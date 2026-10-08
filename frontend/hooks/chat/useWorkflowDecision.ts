"use client";

import { useRef, useState } from "react";
import { runService } from "@/services/service.runs";
import { getSessionId } from "@/lib/auth/session";
import type { DecisionAction } from "@/types/chat.type";

export function useWorkflowDecision(onChanged: (action: DecisionAction) => void) {
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const sending = useRef(false);
    async function respond(runId: string, action: DecisionAction, text = "") {
        if (sending.current) return;
        sending.current = true;
        setBusy(true);
        setError(null);
        const session = getSessionId();
        try {
            await runService.respond(runId, action, text);
            if (getSessionId() === session) onChanged(action);
        } catch (cause) {
            if (getSessionId() === session)
                setError(cause instanceof Error ? cause.message : "Could not save your response.");
        } finally {
            sending.current = false;
            setBusy(false);
        }
    }
    return { busy, error, respond };
}
