"use client";

import { homePath, saveSession } from "@/lib/auth/session";
import { authService } from "@/services/service.auth";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export function useEmailVerification() {
    const [token, setToken] = useState("");
    const [email, setEmail] = useState("");
    const [ready, setReady] = useState(false);
    const [busy, setBusy] = useState(false);
    const [message, setMessage] = useState("");
    const [error, setError] = useState("");
    const router = useRouter();
    useEffect(() => {
        const value = new URLSearchParams(window.location.hash.slice(1)).get("token");
        if (value) {
            setToken(value);
            window.history.replaceState(null, "", window.location.pathname);
        }
        setReady(true);
    }, []);
    const confirm = async () => {
        setBusy(true);
        setError("");
        try {
            const session = await authService.confirmVerification(token);
            saveSession(session);
            const user = await authService.getCurrentUser();
            localStorage.setItem("user_data", JSON.stringify(user));
            router.replace(homePath(user));
        } catch (err) {
            setError(err instanceof Error ? err.message : "We could not verify this link.");
            setToken("");
            setBusy(false);
        }
    };
    const requestVerification = async (event: React.FormEvent) => {
        event.preventDefault();
        setBusy(true);
        setError("");
        setMessage("");
        try {
            setMessage((await authService.requestVerification(email)).message);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Unable to send verification.");
        } finally {
            setBusy(false);
        }
    };

    return { token, email, setEmail, ready, busy, message, error, confirm, requestVerification };
}
