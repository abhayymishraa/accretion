"use client";

import { authService } from "@/services/service.auth";

import { reloadProjects, showProjectTitle } from "@/hooks/projects/useProjectList";
import { getSessionId } from "@/lib/auth/session";
import { followEvents, retryDelay, StreamRefusedError } from "@/lib/http/eventStream";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type ConnectionOptions = {
    chatId: string;
    refreshHistory: () => void;
    setError: (error: string | null) => void;
};
export function useChatConnection({ chatId, refreshHistory, setError }: ConnectionOptions) {
    const router = useRouter();
    const [connected, setConnected] = useState(false);
    // The project stream announces runs; each run's events arrive on its own stream (useRunStream).
    useEffect(() => {
        const controller = new AbortController();
        const { signal } = controller;
        let retry: ReturnType<typeof setTimeout>;
        let attempt = 0;
        setConnected(false);
        const onEvent = (data: string) => {
            let incoming;
            try {
                incoming = JSON.parse(data);
            } catch {
                return;
            }
            attempt = 0;
            if (incoming.e === "ready" || incoming.e === "resync") {
                if (incoming.e === "ready") {
                    setConnected(true);
                    setError(null);
                }
                // Catch up after subscription: history remains visible during reconnect.
                refreshHistory();
                reloadProjects();
                return;
            }
            // The AI's name for a new project; not a run event, so the timeline never sees it.
            if (incoming.e === "project_title" && typeof incoming.title === "string") {
                showProjectTitle(chatId, incoming.title);
                return;
            }
            // History then lists the run as open, and useRunStream follows it.
            if (incoming.e === "run_created") refreshHistory();
        };
        const connect = async () => {
            const token = localStorage.getItem("auth_token");
            const sessionId = getSessionId();
            if (!token) {
                router.push("/signin");
                return;
            }
            try {
                await followEvents(`/projects/${chatId}/stream`, { onEvent, signal });
            } catch (error) {
                if (signal.aborted) return;
                if (error instanceof StreamRefusedError) {
                    setConnected(false);
                    // HTTP can renew an expired token; a refusal alone cannot distinguish
                    // expiry from a missing project or denied permission.
                    const renewed = await authService.tokenRenewed(token, sessionId);
                    if (signal.aborted) return;
                    if (renewed) {
                        void connect();
                        return;
                    }
                    setError(
                        "Could not reconnect. Check your connection and project access, then reload.",
                    );
                    return;
                }
            }
            if (signal.aborted) return;
            setConnected(false);
            setError("Connection lost. Reconnecting to check your run; it may still be working.");
            retry = setTimeout(() => void connect(), retryDelay(attempt++));
        };
        void connect();
        return () => {
            controller.abort();
            clearTimeout(retry);
        };
    }, [chatId, router, refreshHistory, setError]);

    return { connected };
}
