"use client";

import { saveSession } from "@/lib/auth/session";

import { authService } from "@/services/service.auth";
import type { LoginResponse } from "@/types/auth.type";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

/**
 * A demo link, /demo#token=…&q=…: signs in to its demo account and opens a new project with the
 * prompt in the composer, not sent. The token stays in the hash, so it never reaches a server log;
 * a ?q= typed onto the end works too, for a prompt added to the link by hand.
 */
export function useDemoLink() {
    const router = useRouter();
    const [error, setError] = useState("");
    // Reuse the one redemption across Strict Mode effect setup/cleanup.
    const redemption = useRef<Promise<LoginResponse> | null>(null);
    const prompt = useRef("");
    useEffect(() => {
        let disposed = false;
        if (!redemption.current) {
            // A "?q=" typed onto the end of the link lands in the hash: read its "?" as "&". The token
            // is URL-safe base64, so it never holds a "?".
            const hash = new URLSearchParams(window.location.hash.slice(1).replace("?", "&"));
            const token = hash.get("token");
            prompt.current = hash.get("q") ?? "";
            window.history.replaceState(null, "", window.location.pathname);
            redemption.current = token
                ? authService.redeemDemoLink(token)
                : Promise.reject(new Error("Demo link has no token"));
        }
        redemption.current
            .then(
                async (session) => {
                    if (disposed) return;
                    saveSession(session);
                    const user = await authService.getCurrentUser();
                    if (disposed) return;
                    localStorage.setItem("user_data", JSON.stringify(user));
                    const q = prompt.current.trim();
                    router.replace(q ? `/chat?${new URLSearchParams({ q })}` : "/chat");
                },
                () => {
                    if (!disposed)
                        setError(
                            "This demo link is not valid. Ask the person who sent it for a new one.",
                        );
                },
            )
            .catch(() => {
                // The link worked; loading the account did not. A link is never used up, so it can be
                // opened again.
                if (!disposed) setError("Could not open your workspace. Open the link again.");
            });
        return () => {
            disposed = true;
        };
    }, [router]);

    return { error };
}
