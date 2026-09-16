"use client";

import { authService } from "@/services/service.auth";

import { WS_URL } from "@/config/env";
import { getSessionId } from "@/lib/auth/session";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

type ConnectionOptions = {
    chatId: string;
    receiveEvent: (event: MessageEvent) => void;
    refreshHistory: () => void;
    setError: (error: string | null) => void;
};
export function useChatConnection({
    chatId,
    receiveEvent,
    refreshHistory,
    setError,
}: ConnectionOptions) {
    const router = useRouter();
    const [wsConnected, setWsConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    // The connection observes a durable run. Reconnect reloads its authoritative snapshot.
    useEffect(() => {
        let disposed = false;
        let retry: ReturnType<typeof setTimeout>;
        let attempt = 0;
        setWsConnected(false);
        const connect = () => {
            if (disposed) return;
            const token = localStorage.getItem("auth_token");
            const sessionId = getSessionId();
            if (!token) {
                router.push("/signin");
                return;
            }
            const ws = new WebSocket(`${WS_URL}/ws/${chatId}`);
            wsRef.current = ws;
            ws.onopen = () => {
                if (disposed) {
                    ws.close();
                    return;
                }
                ws.send(JSON.stringify({ type: "auth", token, mode: "events" }));
                attempt = 0;
                setError(null);
            };
            ws.onmessage = (event) => {
                if (disposed || wsRef.current !== ws) return;
                let incoming;
                try {
                    incoming = JSON.parse(event.data);
                } catch {
                    return;
                }
                if (incoming.e === "ready" || incoming.e === "resync") {
                    if (incoming.e === "ready") setWsConnected(true);
                    // Catch up after subscription: history remains visible during reconnect.
                    refreshHistory();
                    return;
                }
                receiveEvent(event);
                if (incoming.e === "run_started") refreshHistory();
            };
            ws.onclose = async (event) => {
                if (disposed || wsRef.current !== ws) return;
                setWsConnected(false);
                if (event.code === 1008) {
                    // HTTP can renew an expired token; a socket policy close alone cannot
                    // distinguish expiry from a missing project or denied permission.
                    try {
                        await authService.getCurrentUser();
                        if (disposed || wsRef.current !== ws) return;
                        if (
                            getSessionId() === sessionId &&
                            localStorage.getItem("auth_token") !== token
                        ) {
                            connect();
                            return;
                        }
                    } catch {
                        if (disposed || wsRef.current !== ws) return;
                    }
                    setError(
                        "Could not reconnect. Check your connection and project access, then reload.",
                    );
                    return;
                }
                setError(
                    "Connection lost. Reconnecting to check your run; it may still be working.",
                );
                retry = setTimeout(connect, Math.min(1000 * 2 ** attempt++, 10000));
            };
            ws.onerror = () => ws.close();
        };
        connect();
        return () => {
            disposed = true;
            clearTimeout(retry);
            wsRef.current?.close();
            wsRef.current = null;
        };
    }, [chatId, router, receiveEvent, refreshHistory, setError]);

    return { wsConnected };
}
