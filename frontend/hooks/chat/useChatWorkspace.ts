"use client";

import { runService } from "@/services/service.runs";

import { usePreviewLifecycle } from "@/hooks/preview/usePreviewLifecycle";
import { subscribeSession } from "@/lib/auth/session";
import type { UserData } from "@/types/auth.type";
import type { Message } from "@/types/chat.type";
import { useRouter } from "next/navigation";
import {
    useCallback,
    useEffect,
    useLayoutEffect,
    useMemo,
    useRef,
    useState,
    useSyncExternalStore,
} from "react";

import { useProjectFiles } from "@/hooks/files/useProjectFiles";
import { useChatHistory } from "./useChatHistory";
import { useChatConnection } from "./useChatConnection";
import { useModelChoice } from "./useModelChoice";
import { useWorkspaceLayout } from "./useWorkspaceLayout";
export function useChatWorkspace(chatId: string) {
    const router = useRouter();

    const [messages, setMessages] = useState<Message[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [input, setInput] = useState("");
    const [mode, setMode] = useState<"auto" | "plan">("auto");
    const [appUrl, setAppUrl] = useState<string | null>(null);
    const [isBuilding, setIsBuilding] = useState(false);
    const { projectFiles, revisionId } = useProjectFiles(chatId, isBuilding);
    const [runId, setRunId] = useState<string | null>(null);
    const {
        previewWidth,
        setPreviewWidth,
        setIsDragging,
        showPreview,
        setShowPreview,
        mobilePane,
        setMobilePane,
        previewTab,
        setPreviewTab,
        workspaceVisible,
        containerRef,
    } = useWorkspaceLayout();
    // The session client and socket own authentication; this is display data only. It is
    // read as an external store so the server and the first client render agree.
    const storedUser = useSyncExternalStore(
        subscribeSession,
        () => localStorage.getItem("user_data"),
        () => null,
    );
    const [updatedUser, setUserData] = useState<UserData | null>(null);
    const userData = useMemo(() => {
        if (updatedUser) return updatedUser;
        if (!storedUser) return null;
        try {
            return JSON.parse(storedUser) as UserData;
        } catch (err) {
            console.error("Failed to parse user data:", err);
            return null;
        }
    }, [updatedUser, storedUser]);
    const modelChoice = useModelChoice(userData?.default_model_choice);
    const preview = usePreviewLifecycle({
        projectId: chatId,
        revisionId,
        isBuilding,
        enabled: workspaceVisible && previewTab === "preview",
        onPreviewOpen: setAppUrl,
    });

    const followLatest = useRef(true);
    const conversationRef = useRef<HTMLDivElement>(null);
    const trackRef = useRef<HTMLDivElement>(null);
    const prependPosition = useRef<{ height: number; top: number } | null>(null);
    // Our own scrollTop writes also fire onScroll; without this they read as user intent.
    const programmatic = useRef(false);

    const pinToBottom = useCallback(() => {
        const element = conversationRef.current;
        if (!element) return;
        programmatic.current = true;
        element.scrollTop = element.scrollHeight;
    }, []);

    const history = useChatHistory({
        chatId,
        setIsBuilding,
        setRunId,
        setMessages,
        setAppUrl,
        setError,
    });

    const { wsConnected } = useChatConnection({
        chatId,
        receiveEvent: history.receiveEvent,
        refreshHistory: history.refreshHistory,
        setError,
    });

    useLayoutEffect(() => {
        const position = prependPosition.current;
        const element = conversationRef.current;
        if (position && element) {
            if (!history.loadingOlder) {
                element.scrollTop = position.top + element.scrollHeight - position.height;
                prependPosition.current = null;
            }
            programmatic.current = true;
        } else if (followLatest.current) {
            pinToBottom();
        }
    }, [messages, mobilePane, history.loadingOlder, pinToBottom]);

    // Streamed text grows and run traces collapse long after the render commits;
    // the transcript stays pinned only if we follow those later size changes too.
    useEffect(() => {
        const track = trackRef.current;
        if (!track) return;
        const observer = new ResizeObserver(() => {
            if (followLatest.current && !prependPosition.current) pinToBottom();
        });
        observer.observe(track);
        return () => observer.disconnect();
    }, [pinToBottom]);

    function loadOlder() {
        const element = conversationRef.current;
        if (!element || history.loadingOlder) return;
        prependPosition.current = { height: element.scrollHeight, top: element.scrollTop };
        followLatest.current = false;
        history.loadOlder();
    }

    function handleConversationScroll(event: React.UIEvent<HTMLDivElement>) {
        if (programmatic.current) {
            programmatic.current = false;
            return;
        }
        const element = event.currentTarget;
        followLatest.current =
            element.scrollHeight - element.scrollTop - element.clientHeight < 100;
    }

    const handleSendMessage = async (e: React.FormEvent) => {
        e.preventDefault();
        const prompt = input.trim();
        if (!prompt) return;
        if (isBuilding) {
            // A running build takes the message as a steering update (spec 5).
            if (!runId) return;
            try {
                await runService.steer(runId, prompt);
                setInput("");
                history.refreshHistory();
            } catch (err) {
                setError(err instanceof Error ? err.message : "Update was not accepted");
            }
            return;
        }
        setIsBuilding(true);
        setError(null);
        followLatest.current = true;
        try {
            const data = await runService.start(chatId, prompt, mode, modelChoice.choice);
            setRunId(data.run_id);
            setInput("");
            if (userData) {
                const updated = {
                    ...userData,
                    tokens_remaining: data.tokens_remaining,
                    default_model_choice: modelChoice.choice,
                };
                localStorage.setItem("user_data", JSON.stringify(updated));
                setUserData(updated);
            }
            // The run_started event fetches the accepted prompt for connected observers.
            if (!wsConnected) history.refreshHistory();
        } catch (err) {
            setIsBuilding(false);
            modelChoice.rejected(err);
            setError(err instanceof Error ? err.message : "Request was not accepted");
        }
    };

    const handleCancel = async () => {
        if (!runId) return;
        try {
            await runService.cancel(runId);
            setIsBuilding(false);
            setRunId(null);
            history.refreshHistory();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Could not stop the run");
        }
    };

    return {
        router,
        wsConnected,
        messages,
        error,
        input,
        setInput,
        mode,
        setMode,
        pendingDecisionId: history.pendingRunId,
        awaitingInput: Boolean(history.pendingRunId),
        isLoading: history.isLoading,
        hasOlder: history.hasOlder,
        loadingOlder: history.loadingOlder,
        loadOlder,
        refreshHistory: history.refreshHistory,
        appUrl,
        revisionId,
        isBuilding,
        runId,
        previewWidth,
        setPreviewWidth,
        setIsDragging,
        showPreview,
        setShowPreview,
        userData,
        mobilePane,
        setMobilePane,
        projectFiles,
        previewTab,
        setPreviewTab,
        workspaceVisible,
        preview,
        handleConversationScroll,
        trackRef,
        conversationRef,
        containerRef,
        handleSendMessage,
        handleCancel,
        models: modelChoice.models,
        modelChoice: modelChoice.choice,
        setModelChoice: modelChoice.setChoice,
    };
}
