"use client";

import { authService } from "@/services/service.auth";
import { runService } from "@/services/service.runs";

import { usePreviewLifecycle } from "@/hooks/preview/usePreviewLifecycle";
import { clearSession, getSessionId, subscribeSession } from "@/lib/auth/session";
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

// The session whose balance this page has loaded: another sign-in loads its own.
let balanceSession: string | null = null;

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
        resizeHandlers,
        showPreview,
        setShowPreview,
        mobilePane,
        setMobilePane,
        previewTab,
        setPreviewTab,
        workspaceVisible,
        containerRef,
        openedFile,
        openFile,
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
    // The budget balance changes only as a build spends: load it once per page, then after each
    // build, not on every chat opened.
    const buildSeen = useRef(false);
    useEffect(() => {
        if (isBuilding) {
            buildSeen.current = true;
            return;
        }
        const session = getSessionId();
        if (balanceSession === session && !buildSeen.current) return;
        let disposed = false;
        authService
            .getCurrentUser()
            .then((user) => {
                if (disposed) return;
                // Only a load that landed counts: a failed or abandoned one is retried next time.
                balanceSession = session;
                buildSeen.current = false;
                localStorage.setItem("user_data", JSON.stringify(user));
                setUserData(user);
            })
            // Display only: on failure the last known balance stays up.
            .catch(() => {});
        return () => {
            disposed = true;
        };
    }, [isBuilding]);
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

    const { connected } = useChatConnection({
        chatId,
        refreshHistory: history.refreshHistory,
        syncHistory: history.syncHistory,
        receiveEvent: history.receiveEvent,
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
                    default_model_choice: modelChoice.choice,
                };
                localStorage.setItem("user_data", JSON.stringify(updated));
                setUserData(updated);
            }
            // The run_created notice fetches the accepted prompt for connected observers.
            if (!connected) history.refreshHistory();
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

    const signOut = () => {
        clearSession();
        router.push("/");
    };

    return {
        router,
        signOut,
        connected,
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
        resizeHandlers,
        showPreview,
        setShowPreview,
        userData,
        mobilePane,
        setMobilePane,
        projectFiles,
        previewTab,
        setPreviewTab,
        openedFile,
        openFile,
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
