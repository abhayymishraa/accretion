"use client";

import { clearSession } from "@/lib/auth/session";

import {
    LEGACY_PROJECT_DRAFT_KEY,
    LEGACY_STARTER_KEY,
    MAX_PROJECT_DRAFT_LENGTH,
    PROJECT_DRAFT_KEY,
    STARTER_KEY,
} from "@/lib/projects/draft";
import { migrateKey } from "@/lib/storage/migrateKey";
import { starterBriefs } from "@/lib/projects/starterBriefs";
import { authService } from "@/services/service.auth";
import { projectService } from "@/services/service.projects";
import { type UserData } from "@/types/auth.type";
import { sendable } from "./useComposerMenu";
import { useModelChoice } from "./useModelChoice";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

export function useNewProject() {
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState("");
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [userData, setUserData] = useState<UserData | null>(null);
    const modelChoice = useModelChoice(userData?.default_model_choice);
    const router = useRouter();
    const initialDraft = useRef<string | null>(null);

    useEffect(() => {
        // Check if user is authenticated
        const token = localStorage.getItem("auth_token");

        if (initialDraft.current === null) {
            try {
                initialDraft.current = "";
                const explicitStarter = new URLSearchParams(window.location.search).get("starter");
                migrateKey(sessionStorage, PROJECT_DRAFT_KEY, LEGACY_PROJECT_DRAFT_KEY);
                migrateKey(sessionStorage, STARTER_KEY, LEGACY_STARTER_KEY);
                const draft = sessionStorage.getItem(PROJECT_DRAFT_KEY);
                const requested = explicitStarter || sessionStorage.getItem(STARTER_KEY);
                const starter = starterBriefs.find((item) => item.id === requested);
                if (draft?.trim() && !(explicitStarter && starter)) {
                    initialDraft.current = draft.slice(0, MAX_PROJECT_DRAFT_LENGTH);
                } else if (starter) {
                    initialDraft.current = starter.prompt;
                    sessionStorage.removeItem(PROJECT_DRAFT_KEY);
                    if (token) sessionStorage.removeItem(STARTER_KEY);
                    else sessionStorage.setItem(STARTER_KEY, starter.id);
                }
            } catch {
                /* A starter is optional when session storage is unavailable. */
            }
        }

        if (!token) {
            router.push("/signin");
            return;
        }

        let disposed = false;
        authService
            .getCurrentUser()
            .then((user) => {
                if (disposed) return;
                localStorage.setItem("user_data", JSON.stringify(user));
                setInput((current) => current || initialDraft.current || "");
                setUserData(user);
                setIsAuthenticated(true);
            })
            .catch(() => {
                if (!disposed) setError("Could not load your account. Refresh to try again.");
            });
        return () => {
            disposed = true;
        };
    }, [router]);

    const handleSignOut = () => {
        clearSession();
        setIsAuthenticated(false);
        setUserData(null);
        router.push("/");
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading || !isAuthenticated) return;

        setIsLoading(true);
        setError("");

        try {
            const response = await projectService.createChat(sendable(input), modelChoice.choice);
            try {
                sessionStorage.removeItem(PROJECT_DRAFT_KEY);
            } catch {
                // A successfully created chat must still open if storage becomes unavailable.
            }
            router.push(`/chat/${response.chat_id}`);
        } catch (err) {
            console.error("Error creating chat:", err);
            modelChoice.rejected(err);
            // The API client puts the server's reason in the message; a spent budget says when it resets.
            setError(
                err instanceof Error ? err.message : "Failed to create chat. Please try again.",
            );
            setIsLoading(false);
        }
    };

    return {
        input,
        setInput,
        isLoading,
        error,
        isAuthenticated,
        userData,
        handleSignOut,
        handleSubmit,
        models: modelChoice.models,
        modelChoice: modelChoice.choice,
        setModelChoice: modelChoice.setChoice,
    };
}
