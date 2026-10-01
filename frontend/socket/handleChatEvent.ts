import type { Message, RunEvent, RunSnapshot, WebSocketHandlers } from "@/types/chat.type";

export function applyRunEvent(messages: Message[], event: RunEvent): Message[] {
    if (!event.run_id) return messages;
    const id = `run:${event.run_id}`;
    const existing = messages.find((m) => m.id === id);
    // An approved plan is replayed as kind "execute"; it joins the trace where it happened. Other
    // proposals are decision cards outside the trace.
    const plan = event.e === "approach" && event.workflow?.kind === "execute";
    const activityId =
        event.e === "stage" || event.e === "verification" || plan
            ? event.event_id || `${event.e}:${event.created_at}:${event.message}`
            : undefined;
    if (activityId !== undefined && existing?.activity?.some((item) => item.id === activityId)) {
        return messages;
    }
    let toolIndex = -1;
    if (event.e === "tool_started" || event.e === "tool_completed") {
        if (!event.call_id) return messages;
        toolIndex = existing?.tool_calls?.findIndex((call) => call.id === event.call_id) ?? -1;
        // A replayed start must not replace a tool that has already returned a result.
        if (event.e === "tool_started" && toolIndex >= 0) {
            return messages;
        }
    }
    const message: Message = existing
        ? {
              ...existing,
              activity: [...(existing.activity || [])],
              tool_calls: [...(existing.tool_calls || [])],
          }
        : {
              id,
              role: "assistant",
              content: "",
              created_at: event.created_at,
              event_type: "run",
              tool_calls: [],
              activity: [],
              run_status: "running",
          };
    const activity = message.activity!;
    if (event.workflow) message.workflow = event.workflow;
    if (event.e === "tool_started" || event.e === "tool_completed") {
        const calls = message.tool_calls!;
        const call = {
            id: event.call_id,
            name: event.name || "Tool",
            status:
                event.e === "tool_started"
                    ? ("running" as const)
                    : event.ok
                      ? ("success" as const)
                      : ("error" as const),
            output: event.output,
            details: event.details,
            duration_ms: event.duration_ms,
            run_id: event.run_id,
            event_id: event.event_id,
        };
        if (toolIndex < 0) calls.push(call);
        else calls[toolIndex] = call;
    } else if (event.e === "stage" || event.e === "verification") {
        activity.push({
            id: activityId!,
            kind: event.e,
            created_at: event.created_at,
            message: event.message,
            ok: event.ok,
            checks: event.checks,
            compacted: event.compacted,
        });
    } else if (plan) {
        activity.push({
            id: activityId!,
            kind: "approach",
            created_at: event.created_at,
            message: event.workflow?.summary,
            steps: event.workflow?.steps,
        });
    } else if (event.message && event.e !== "approach") {
        message.content = event.message;
    }
    if (event.e === "run_finished") {
        message.run_status = event.status || "interrupted";
        message.finished_at = event.created_at;
        message.tool_calls = message.tool_calls?.map((call) =>
            call.status === "running"
                ? { ...call, status: "error", output: "Run ended before this operation completed." }
                : call,
        );
    }
    return existing ? messages.map((m) => (m.id === id ? message : m)) : [...messages, message];
}

export function restoreRuns(messages: Message[], runs: RunSnapshot[]): Message[] {
    let result = messages;
    for (const run of runs) {
        for (const event of run.events) result = applyRunEvent(result, event);
        const missingTerminalEvent =
            run.status !== "running" && !run.events.some((event) => event.e === "run_finished");
        if (missingTerminalEvent) {
            result = applyRunEvent(result, {
                e: "run_finished",
                run_id: run.id,
                event_id: `${run.id}:terminal`,
                created_at:
                    run.events.at(-1)?.created_at || run.created_at || new Date(0).toISOString(),
                status: run.status,
                message: run.reason || `Run ${run.status}`,
            });
        }
        // A resolved proposal keeps its original terminal event; the row is authoritative.
        result = result.map((message) =>
            message.id === `run:${run.id}`
                ? {
                      ...message,
                      run_status: run.status,
                      workflow: run.workflow,
                      // A terminal snapshot without its event has no trustworthy completion time.
                      ...(missingTerminalEvent ? { finished_at: undefined } : {}),
                  }
                : message,
        );
    }
    return result.sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at));
}

export function handleWebSocketMessage(event: MessageEvent, handlers: WebSocketHandlers) {
    try {
        const data = JSON.parse(event.data);
        if (data.type === "history") {
            const runs: RunSnapshot[] = data.runs || [];
            for (const run of runs) if (run.status !== "running") handlers.terminalRuns.add(run.id);
            // New runs render their own terminal summary; preserve legacy chat history.
            const history = handlers.consolidateMessages(
                (data.messages || []).filter(
                    (m: Message) =>
                        m.event_type !== "run_summary" || !runs.some((run) => run.id === m.id),
                ),
            );
            handlers.setMessages(restoreRuns(history, runs));
            const active = runs.find((run) => run.status === "running");
            handlers.setRunId(active?.id || null);
            handlers.setIsBuilding(Boolean(active));
            handlers.setAppUrl(data.app_url || null);
            // Run failures belong to their inline run card; this banner is for transport errors.
            handlers.setError(null);
            return;
        }
        if (!data.run_id) return;
        if (handlers.terminalRuns.has(data.run_id)) return;
        if (data.e === "run_started") handlers.setPendingRunId(null);
        if (data.e === "run_finished" && data.status === "awaiting_input")
            handlers.setPendingRunId(data.run_id);
        handlers.setMessages((previous) => applyRunEvent(previous, data));
        if (data.e === "run_started" || data.e === "stage" || data.e === "tool_started") {
            handlers.setRunId(data.run_id);
            handlers.setIsBuilding(true);
        }
        if (data.e === "run_finished") {
            handlers.terminalRuns.add(data.run_id);
            handlers.setRunId(null);
            handlers.setIsBuilding(false);
            handlers.setError(null);
            if (data.status === "succeeded" && data.url) handlers.setAppUrl(data.url);
            else if (data.status !== "awaiting_input" && data.status !== "answered")
                handlers.setAppUrl(null);
        }
    } catch {
        handlers.setError("Could not read a progress update. Reconnect to reload run status.");
    }
}
