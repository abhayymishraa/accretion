"use client";

import { homePath, saveSession } from "@/lib/auth/session";

import { authService } from "@/services/service.auth";
import type { LoginResponse } from "@/types/auth.type";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

const errors: Record<string, string> = {
    link_required:
        "An account already uses this email. Sign in with email, then connect this provider from your profile.",
    verified_email_required:
        "Your provider must have a verified email address before you can continue.",
    account_conflict:
        "This provider is already connected to another account, or your account already has a different connection.",
    oauth_failed: "Sign-in was cancelled or could not be completed. Please try again.",
};

export function useOAuthCallback() {
    const router = useRouter();
    const [error, setError] = useState("");
    // Reuse the one-time exchange across Strict Mode effect setup/cleanup.
    const exchange = useRef<Promise<LoginResponse> | null>(null);
    const callbackError = useRef("");
    useEffect(() => {
        let disposed = false;
        if (!exchange.current && !callbackError.current) {
            const params = new URLSearchParams(window.location.hash.slice(1));
            const ticket = params.get("ticket");
            callbackError.current = params.get("error") || (!ticket ? "oauth_failed" : "");
            window.history.replaceState(null, "", window.location.pathname);
            exchange.current =
                ticket && !callbackError.current
                    ? authService.exchangeOAuth(ticket)
                    : Promise.reject(new Error("OAuth callback rejected"));
        }
        exchange.current
            ?.then(async (session) => {
                if (disposed) return;
                saveSession(session);
                const user = await authService.getCurrentUser();
                if (disposed) return;
                localStorage.setItem("user_data", JSON.stringify(user));
                router.replace(homePath(user));
            })
            .catch(() => {
                if (!disposed) setError(errors[callbackError.current] || errors.oauth_failed);
            });
        return () => {
            disposed = true;
        };
    }, [router]);

    return { error };
}
