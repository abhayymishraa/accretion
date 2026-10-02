"use client";

import { useRequireSession } from "@/hooks/auth/useHasSession";
import { useSignOut } from "@/hooks/auth/useSignOut";
import { authService } from "@/services/service.auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import useSWR from "swr";

export function useWaitlist() {
    const router = useRouter();
    const signOut = useSignOut();
    const hasSession = useRequireSession();
    const { data: user } = useSWR(hasSession ? "/auth/me" : null, authService.getCurrentUser);
    useEffect(() => {
        // Approved while this tab sat open: go straight in.
        if (user && !user.waitlisted) router.replace("/chat");
    }, [user, router]);

    return { user: user?.waitlisted ? user : null, signOut };
}
