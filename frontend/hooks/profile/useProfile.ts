"use client";

import { clearSession } from "@/lib/auth/session";

import { authService } from "@/services/service.auth";
import { type AuthOptions, type UserData } from "@/types/auth.type";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

export function useProfile() {
    const router = useRouter();
    const [user, setUser] = useState<UserData | null>(null);
    const [options, setOptions] = useState<AuthOptions | null>(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");
    const [attempt, setAttempt] = useState(0);

    useEffect(() => {
        if (!localStorage.getItem("auth_token")) {
            router.replace("/signin");
            return;
        }
        let disposed = false;
        setError("");
        authService
            .getCurrentUser()
            .then((value) => {
                if (disposed) return;
                setUser(value);
                localStorage.setItem("user_data", JSON.stringify(value));
                const connected = new URLSearchParams(location.hash.slice(1)).get("connected");
                if (connected && value.providers?.includes(connected))
                    setMessage("Sign-in method connected.");
                if (location.hash) history.replaceState(null, "", location.pathname);
            })
            .catch(() => {
                if (!disposed) setError("Could not load your profile. Please try again.");
            });
        authService
            .options()
            .then((value) => {
                if (!disposed) setOptions(value);
            })
            .catch(() => {});
        return () => {
            disposed = true;
        };
    }, [router, attempt]);

    function signOut() {
        clearSession();
        router.replace("/signin");
    }

    async function save(name: string, bio: string): Promise<boolean> {
        if (busy) return false;
        setBusy(true);
        setError("");
        setMessage("");
        try {
            const value = await authService.updateProfile({
                name: name.trim(),
                bio: bio.trim(),
            });
            setUser(value);
            localStorage.setItem("user_data", JSON.stringify(value));
            toast.success("Your changes are saved.", { id: "profile-save" });
            return true;
        } catch (err) {
            setError(err instanceof Error ? err.message : "Could not save your changes.");
            return false;
        } finally {
            setBusy(false);
        }
    }

    async function connect(provider: "google" | "github") {
        setBusy(true);
        setError("");
        setMessage("");
        try {
            const { url } = await authService.linkProvider(provider);
            window.location.assign(url);
        } catch {
            setError("Could not connect this sign-in method. Please try again.");
            setBusy(false);
        }
    }

    return {
        user,
        options,
        busy,
        error,
        message,
        setAttempt,
        signOut,
        save,
        connect,
    };
}
