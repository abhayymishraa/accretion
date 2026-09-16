"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { historyService } from "@/services/service.history";
import { getSessionId } from "@/lib/auth/session";
import { applyRunEvent } from "@/socket/handleChatEvent";
import type { Message, RunEvent } from "@/types/chat.type";

export function useRunDetails(message: Message, expanded: boolean) {
    const [events, setEvents] = useState<RunEvent[] | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [attempt, setAttempt] = useState(0);
    const running = message.run_status === "running";
    const loadedVersion = useRef<string | null>(null);
    const version = `${message.id}:${message.details_version || 0}:${running}`;
    useEffect(() => {
        if (!expanded || !message.details_pending || loadedVersion.current === version) return;
        const controller = new AbortController();
        const session = getSessionId();
        setError(null);
        historyService
            .details(message.id.replace(/^run:/, ""), controller.signal)
            .then((result) => {
                if (!controller.signal.aborted && getSessionId() === session) {
                    loadedVersion.current = version;
                    setEvents(result.events);
                }
            })
            .catch((error) => {
                if (!controller.signal.aborted && getSessionId() === session)
                    setError(
                        error instanceof Error ? error.message : "Could not load build steps.",
                    );
            });
        return () => controller.abort();
    }, [message.id, message.details_pending, expanded, version, attempt]);
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
        loading: expanded && message.details_pending && !events && !error,
        error,
        retry: () => setAttempt((value) => value + 1),
    };
}
