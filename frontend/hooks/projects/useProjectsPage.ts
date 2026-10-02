"use client";

import { useHasSession } from "@/hooks/auth/useHasSession";
import { clearSession } from "@/lib/auth/session";

import { authService } from "@/services/service.auth";
import { type UserData } from "@/types/auth.type";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export function useProjectsPage() {
    const router = useRouter();
    const [ready, setReady] = useState(false);
    const hasSession = useHasSession();
    const [user, setUser] = useState<UserData | null>(null);
    useEffect(() => {
        if (!localStorage.getItem("auth_token")) {
            router.replace("/signin");
            return;
        }
        let disposed = false;
        authService
            .getCurrentUser()
            .then((data) => {
                if (!disposed) setUser(data);
            })
            .catch(() => {
                /* The API client handles an expired session. */
            })
            .finally(() => {
                if (!disposed) setReady(true);
            });
        return () => {
            disposed = true;
        };
    }, [router]);
    function signOut() {
        clearSession();
        router.push("/");
    }

    return { ready, hasSession, user, signOut };
}
