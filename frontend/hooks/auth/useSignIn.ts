"use client";

import { clearSession, getSessionId, homePath, saveSession } from "@/lib/auth/session";
import { authService } from "@/services/service.auth";
import { useRouter } from "next/navigation";
import type React from "react";
import { useEffect, useState } from "react";

export function useSignIn() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState("");
    const [checkingSession, setCheckingSession] = useState(true);
    const router = useRouter();

    useEffect(() => {
        let disposed = false;

        const checkSession = async () => {
            try {
                const token = localStorage.getItem("auth_token");
                const sessionId = getSessionId();
                if (token) {
                    const user = await authService.getCurrentUser();
                    if (disposed) return;
                    if (getSessionId() === sessionId) {
                        try {
                            localStorage.setItem("user_data", JSON.stringify(user));
                        } catch {
                            // Caching profile data is optional after validating the session.
                        }
                        router.replace(homePath(user));
                        return;
                    }
                }
            } catch {
                // The API client clears expired credentials. Network failures keep them.
            }
            if (!disposed) setCheckingSession(false);
        };

        void checkSession();
        return () => {
            disposed = true;
        };
    }, [router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setIsLoading(true);

        try {
            // Call the login API
            const data = await authService.login({ email, password });

            saveSession(data);

            // Fetch user data after login since login doesn't return it
            let destination = "/chat";
            try {
                const userData = await authService.getCurrentUser();
                localStorage.setItem("user_data", JSON.stringify(userData));
                destination = homePath(userData);
            } catch (err) {
                console.warn("Failed to fetch user data after login:", err);
                // Continue anyway, user data will be fetched on chat page
            }

            // Verify token was stored before redirect
            const storedToken = localStorage.getItem("auth_token");
            if (!storedToken) {
                throw new Error("Failed to store authentication token");
            }

            setIsLoading(false);
            router.replace(destination);
        } catch (error: unknown) {
            console.error("Error signing in:", error);
            setError(error instanceof Error ? error.message : "Failed to sign in");
            setIsLoading(false);
            // Clear any partial data on error
            clearSession();
        }
    };

    return {
        email,
        setEmail,
        password,
        setPassword,
        isLoading,
        error,
        checkingSession,
        handleSubmit,
    };
}
