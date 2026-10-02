"use client";

import { subscribeSession } from "@/lib/auth/session";
import { useRouter } from "next/navigation";
import { useEffect, useSyncExternalStore } from "react";

/** Whether this tab holds a session; false during server render, live across tabs. */
export function useHasSession() {
    return useSyncExternalStore(
        subscribeSession,
        () => Boolean(localStorage.getItem("auth_token")),
        () => false,
    );
}

/** `useHasSession`, sending a signed-out visitor to /signin. */
export function useRequireSession() {
    const router = useRouter();
    useEffect(() => {
        if (!localStorage.getItem("auth_token")) router.replace("/signin");
    }, [router]);
    return useHasSession();
}
