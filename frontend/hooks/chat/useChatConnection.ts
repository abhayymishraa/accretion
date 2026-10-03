"use client";

import { authService } from "@/services/service.auth";

import { listProject, reloadProjects, showProjectTitle } from "@/hooks/projects/useProjectList";
import { getSessionId } from "@/lib/auth/session";
import {
    followEvents,
    retryDelay,
    StreamCursorRejectedError,
    StreamRefusedError,
} from "@/lib/http/eventStream";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type ConnectionOptions = {
    chatId: string;
    refreshHistory: () => void;
    syncHistory: (latestRunId: string | null) => void;
    receiveEvent: (event: MessageEvent) => void;
    setError: (error: string | null) => void;
};
export function useChatConnection({
    chatId,
    refreshHistory,
    syncHistory,
    receiveEvent,
    setError,
}: ConnectionOptions) {
    const router = useRouter();
    const [connected, setConnected] = useState(false);
    // One stream per project: its notices and the events of the runs it follows. A reconnect sends
    // the last run event's id (`run_id:sequence`), so that run resumes where this tab left it.
    useEffect(() => {
        const controller = new AbortController();
        const { signal } = controller;
        let retry: ReturnType<typeof setTimeout>;
        let attempt = 0;
        let lastEventId: string | undefined;
        setConnected(false);
        const onEvent = (data: string, id: string | undefined) => {
            let incoming;
            try {
                incoming = JSON.parse(data);
            } catch {
                return;
            }
            attempt = 0;
            if (id) lastEventId = id;
            if (incoming.e === "ready" || incoming.e === "resync") {
                if (incoming.e === "ready") {
                    setConnected(true);
                    setError(null);
                }
                // A ready that names the newest run and the title says what this tab may have
                // missed: reload only when that run is not loaded. Without them, or on resync,
                // catch up in full. History stays visible either way.
                if (incoming.e === "ready" && "latest_run_id" in incoming) {
                    syncHistory(incoming.latest_run_id);
                    listProject(chatId);
                    if (typeof incoming.title === "string")
                        showProjectTitle(chatId, incoming.title);
                    return;
                }
                refreshHistory();
                reloadProjects();
                return;
            }
            // The AI's name for a new project; not a run event, so the timeline never sees it.
            if (incoming.e === "project_title" && typeof incoming.title === "string") {
                showProjectTitle(chatId, incoming.title);
                return;
            }
            // History then lists the run as open; its events follow on this stream. A new prompt
            // also moves this project to the top of the list.
            if (incoming.e === "run_created") {
                refreshHistory();
                reloadProjects();
            } else if (typeof incoming.run_id === "string")
                receiveEvent(new MessageEvent("message", { data }));
        };
        const connect = async () => {
            const token = localStorage.getItem("auth_token");
            const sessionId = getSessionId();
            if (!token) {
                router.push("/signin");
                return;
            }
            try {
                await followEvents(`/projects/${chatId}/stream`, { lastEventId, onEvent, signal });
            } catch (error) {
                if (signal.aborted) return;
                // A rejected resume point: start over once without it, as a reload does (history
                // drops what it already shows). Rejected without one, retrying cannot help.
                if (error instanceof StreamCursorRejectedError) {
                    if (lastEventId) {
                        lastEventId = undefined;
                        void connect();
                        return;
                    }
                    setConnected(false);
                    setError("Could not reconnect to this project. Reload the page.");
                    return;
                }
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
    }, [chatId, router, refreshHistory, syncHistory, receiveEvent, setError]);

    return { connected };
}
