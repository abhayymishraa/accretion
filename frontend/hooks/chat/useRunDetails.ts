"use client";

import { useEffect, useMemo, useState } from "react";
import { historyService } from "@/services/service.history";
import { getSessionId } from "@/lib/auth/session";
import { isOpenRun } from "@/lib/chat/messages";
import { applyRunEvent } from "@/socket/handleChatEvent";
import type { Message, RunEvent } from "@/types/chat.type";

// A finished run's steps load when wanted (expanded, or about to be copied). An open run needs no
// fetch: its stream replays every event from the first.
export function useRunDetails(message: Message, wanted: boolean) {
    // Steps as last fetched, with the version they belong to: older steps stay on screen while a
    // newer version loads, but only steps of the current version count as loaded.
    const [loadedSteps, setLoadedSteps] = useState<{ version: string; events: RunEvent[] } | null>(
        null,
    );
    const events = loadedSteps?.events ?? null;
    const [error, setError] = useState<string | null>(null);
    const [attempt, setAttempt] = useState(0);
    const running = isOpenRun(message.run_status);
    const version = `${message.id}:${message.details_version || 0}`;
    const fetching = wanted && !running && Boolean(message.details_pending);
    const current = loadedSteps?.version === version;
    useEffect(() => {
        if (!fetching || current) return;
        const controller = new AbortController();
        const session = getSessionId();
        historyService
            .details(message.id.replace(/^run:/, ""), controller.signal)
            .then((result) => {
                if (!controller.signal.aborted && getSessionId() === session) {
                    setError(null);
                    setLoadedSteps({ version, events: result.events });
                }
            })
            .catch((error) => {
                if (!controller.signal.aborted && getSessionId() === session)
                    setError(
                        error instanceof Error ? error.message : "Could not load build steps.",
                    );
            });
        return () => controller.abort();
    }, [message.id, fetching, current, version, attempt]);
    const details = useMemo(() => {
        // Restore older details first, then replay live items so completed tools stay completed.
        let restored: Message[] = [{ ...message, activity: [], tool_calls: [] }];
        for (const event of events || []) restored = applyRunEvent(restored, event);
        const activity = new Map((restored[0].activity || []).map((item) => [item.id, item]));
        const calls = new Map((restored[0].tool_calls || []).map((call) => [call.id, call]));
        for (const item of message.activity || []) activity.set(item.id, item);
        for (const call of message.tool_calls || []) {
            if (call.status !== "running" || !calls.has(call.id)) calls.set(call.id, call);
        }
        return { activity: [...activity.values()], calls: [...calls.values()] };
    }, [message, events]);
    return {
        ...details,
        loaded: current,
        loading: fetching && !current && !error,
        error,
        retry: () => {
            setError(null);
            setAttempt((value) => value + 1);
        },
    };
}
