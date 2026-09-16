"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { historyService } from "@/services/service.history";
import { getSessionId } from "@/lib/auth/session";
import { cacheHistory, getHistoryCache } from "@/lib/chat/historyCache";
import { consolidateMessages } from "@/lib/chat/messages";
import { handleWebSocketMessage } from "@/socket/handleChatEvent";
import type { Message, WebSocketHandlers } from "@/types/chat.type";

function mergeMessages(previous: Message[], incoming: Message[], older = false) {
    const items = new Map(previous.map((message) => [message.id, message]));
    for (const message of incoming) {
        const existing = items.get(message.id);
        if (older && existing) continue;
        items.set(
            message.id,
            existing && message.details_pending
                ? {
                      ...message,
                      activity: existing.activity,
                      tool_calls: existing.tool_calls,
                      details_version: (existing.details_version || 0) + 1,
                  }
                : message,
        );
    }
    return [...items.values()].sort(
        (a, b) => a.created_at.localeCompare(b.created_at) || a.id.localeCompare(b.id),
    );
}

type Options = Omit<WebSocketHandlers, "terminalRuns" | "consolidateMessages"> & { chatId: string };
export function useChatHistory(options: Options) {
    const { chatId, setMessages, setIsBuilding, setRunId, setAppUrl, setError } = options;
    const [isLoading, setIsLoading] = useState(true);
    const [loadingOlder, setLoadingOlder] = useState(false);
    const [nextCursor, setNextCursor] = useState<string | null>(null);
    const control = useRef<{
        refresh: () => void;
        receive: (event: MessageEvent) => void;
        older: (cursor: string) => void;
    } | null>(null);

    useEffect(() => {
        const session = getSessionId();
        const key = JSON.stringify([session, chatId]);
        const cached = session ? getHistoryCache(key) : undefined;
        let disposed = false;
        let loading = false;
        let queued = false;
        let olderLoading = false;
        let olderLoaded = false;
        let latestIds = new Set(cached?.messages.map((message) => message.id));
        let buffered: MessageEvent[] = [];
        const abort = new AbortController();
        const terminalRuns = new Set<string>();
        const handlers = {
            setMessages,
            setIsBuilding,
            setRunId,
            setAppUrl,
            setError,
            terminalRuns,
            consolidateMessages,
        };
        const valid = () => !disposed && getSessionId() === session;
        const applyEvent = (event: MessageEvent) => handleWebSocketMessage(event, handlers);
        setMessages(cached?.messages || []);
        setNextCursor(cached?.next_cursor || null);
        setIsLoading(!cached);
        setLoadingOlder(false);
        setIsBuilding(Boolean(cached?.active_run_id));
        setRunId(cached?.active_run_id || null);
        setAppUrl(null);
        setError(null);

        const refresh = async () => {
            if (!valid()) return;
            if (loading) {
                queued = true;
                return;
            }
            loading = true;
            try {
                do {
                    queued = false;
                    const page = await historyService.page(chatId, abort.signal);
                    if (!valid()) return;
                    cacheHistory(key, page);
                    // A long disconnect can leave a gap between the new page and loaded history.
                    if (
                        latestIds.size &&
                        !page.messages.some((message) => latestIds.has(message.id))
                    )
                        olderLoaded = false;
                    latestIds = new Set(page.messages.map((message) => message.id));
                    for (const message of page.messages) {
                        if (message.run_status && message.run_status !== "running")
                            terminalRuns.add(message.id.replace(/^run:/, ""));
                    }
                    setMessages((previous) => mergeMessages(previous, page.messages));
                    if (!olderLoaded) setNextCursor(page.next_cursor);
                    setRunId(page.active_run_id);
                    setIsBuilding(Boolean(page.active_run_id));
                    setError(null);
                    setIsLoading(false);
                    // Messages committed during the GET win over its snapshot.
                    for (const event of buffered) applyEvent(event);
                    buffered = [];
                } while (queued && valid());
            } catch (error) {
                if (valid()) {
                    setError(
                        error instanceof Error ? error.message : "Could not load conversation.",
                    );
                    for (const event of buffered) applyEvent(event);
                    buffered = [];
                }
            } finally {
                loading = false;
                if (valid()) setIsLoading(false);
            }
        };
        const older = async (cursor: string) => {
            if (olderLoading || !valid()) return;
            olderLoading = true;
            setLoadingOlder(true);
            try {
                const page = await historyService.page(chatId, abort.signal, cursor);
                if (!valid()) return;
                olderLoaded = true;
                setMessages((previous) => mergeMessages(previous, page.messages, true));
                setNextCursor(page.next_cursor);
            } catch (error) {
                if (valid())
                    setError(
                        error instanceof Error ? error.message : "Could not load older messages.",
                    );
            } finally {
                olderLoading = false;
                if (valid()) setLoadingOlder(false);
            }
        };
        control.current = {
            refresh: () => {
                void refresh();
            },
            older: (cursor) => {
                void older(cursor);
            },
            receive: (event) => {
                if (!valid()) return;
                if (loading) {
                    buffered.push(event);
                    if (buffered.length > 512) {
                        buffered = buffered.slice(-512);
                        queued = true;
                    }
                } else applyEvent(event);
            },
        };
        void refresh();
        return () => {
            disposed = true;
            abort.abort();
            control.current = null;
        };
    }, [chatId, setAppUrl, setError, setIsBuilding, setMessages, setRunId]);

    const refreshHistory = useCallback(() => control.current?.refresh(), []);
    const receiveEvent = useCallback((event: MessageEvent) => control.current?.receive(event), []);
    const loadOlder = useCallback(() => {
        if (nextCursor) control.current?.older(nextCursor);
    }, [nextCursor]);
    return {
        isLoading,
        loadingOlder,
        hasOlder: Boolean(nextCursor),
        loadOlder,
        refreshHistory,
        receiveEvent,
    };
}
