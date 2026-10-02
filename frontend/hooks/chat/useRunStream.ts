"use client";

import { authService } from "@/services/service.auth";

import { getSessionId } from "@/lib/auth/session";
import { followEvents, retryDelay, StreamRefusedError } from "@/lib/http/eventStream";
import { useEffect } from "react";

type RunStreamOptions = {
    runId: string | null;
    receiveEvent: (event: MessageEvent) => void;
    refreshHistory: () => void;
};

// Follows one open run's events until its run_finished. The cursor starts empty, so a fresh
// mount replays the run from its first event; event_id and call_id dedupe what history holds.
export function useRunStream({ runId, receiveEvent, refreshHistory }: RunStreamOptions) {
    useEffect(() => {
        if (!runId) return;
        const controller = new AbortController();
        const { signal } = controller;
        let retry: ReturnType<typeof setTimeout>;
        let attempt = 0;
        let lastEventId: string | undefined;
        let finished = false;
        const onEvent = (data: string, id: string | undefined) => {
            lastEventId = id;
            attempt = 0;
            receiveEvent(new MessageEvent("message", { data }));
            try {
                if (JSON.parse(data).e === "run_finished") finished = true;
            } catch {
                // receiveEvent already reported the unreadable update.
            }
        };
        const follow = async () => {
            const token = localStorage.getItem("auth_token");
            const sessionId = getSessionId();
            try {
                await followEvents(`/runs/${runId}/stream`, { lastEventId, onEvent, signal });
                if (signal.aborted || finished) return;
                // Closed without a terminal event: the row may have ended unseen, so reload it.
                refreshHistory();
            } catch (error) {
                if (signal.aborted) return;
                if (error instanceof StreamRefusedError) {
                    // Only a renewed token can change the answer; a failed renewal ends the
                    // session itself. Otherwise the run is gone or not ours: reload, then stop.
                    const renewed = await authService.tokenRenewed(token, sessionId);
                    if (signal.aborted) return;
                    if (renewed) void follow();
                    else refreshHistory();
                    return;
                }
            }
            retry = setTimeout(() => void follow(), retryDelay(attempt++));
        };
        void follow();
        return () => {
            controller.abort();
            clearTimeout(retry);
        };
    }, [runId, receiveEvent, refreshHistory]);
}
