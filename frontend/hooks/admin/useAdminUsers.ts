"use client";

import { useRequireSession } from "@/hooks/auth/useHasSession";
import { useSignOut } from "@/hooks/auth/useSignOut";
import { usersService } from "@/services/service.users";
import type { AccountStatus } from "@/types/auth.type";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import useSWR from "swr";

const ADMIN_ONLY = "Only an admin can do this.";

export function useAdminUsers() {
    const router = useRouter();
    const signOut = useSignOut();
    const hasSession = useRequireSession();
    const [status, setStatus] = useState<AccountStatus>("waiting");
    const [query, setQuery] = useState("");
    const [search, setSearch] = useState("");
    const [page, setPage] = useState(1);
    // The signup notice links here with ?approve=<id> to open one account.
    const [selectedId, setSelectedId] = useState<number | null>(() =>
        typeof window === "undefined"
            ? null
            : Number(new URLSearchParams(window.location.search).get("approve")) || null,
    );
    const [pending, setPending] = useState<number | null>(null);
    const [actionError, setActionError] = useState("");

    // Search once typing pauses, from the first page.
    useEffect(() => {
        const next = query.trim();
        if (next === search) return;
        const timer = setTimeout(() => {
            setSearch(next);
            setPage(1);
        }, 250);
        return () => clearTimeout(timer);
    }, [query, search]);

    const { data, error, mutate } = useSWR(
        hasSession ? (["/users", status, search, page] as const) : null,
        ([, s, q, p]) => usersService.list(s, q, p),
        { keepPreviousData: true },
    );

    useEffect(() => {
        // Signed in but not the admin: this page is not theirs, so leave quietly.
        if (error instanceof Error && error.message === ADMIN_ONLY) router.replace("/chat");
    }, [error, router]);

    const items = data?.items ?? [];
    const selected = items.find((user) => user.id === selectedId) ?? items[0] ?? null;

    function changeStatus(next: AccountStatus) {
        setStatus(next);
        setPage(1);
    }

    async function approve(userId: number) {
        setPending(userId);
        setActionError("");
        try {
            await usersService.approve(userId);
            // Move on to the next person on this page.
            const index = items.findIndex((user) => user.id === userId);
            setSelectedId(items[index + 1]?.id ?? items[index - 1]?.id ?? null);
            await mutate();
        } catch (err) {
            setActionError(err instanceof Error ? err.message : "Could not approve this account.");
        } finally {
            setPending(null);
        }
    }

    // Keyboard: A approves the open account, J and K move through this page.
    const keys = useRef({ items, selected, pending, approve });
    useEffect(() => {
        keys.current = { items, selected, pending, approve };
    });
    useEffect(() => {
        function onKey(event: KeyboardEvent) {
            if (event.metaKey || event.ctrlKey || event.altKey) return;
            if ((event.target as HTMLElement).closest("input, textarea, [contenteditable]")) return;
            const { items, selected, pending, approve } = keys.current;
            if (!selected) return;
            const index = items.indexOf(selected);
            if (event.key === "a" && pending === null && !selected.approved_at)
                void approve(selected.id);
            else if (event.key === "j")
                setSelectedId(items[Math.min(index + 1, items.length - 1)].id);
            else if (event.key === "k") setSelectedId(items[Math.max(index - 1, 0)].id);
        }
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, []);

    const loadError = error instanceof Error && error.message !== ADMIN_ONLY ? error.message : "";

    return {
        data,
        items,
        selected,
        status,
        changeStatus,
        query,
        setQuery,
        setPage,
        pending,
        approve,
        select: setSelectedId,
        error: actionError || loadError,
        signOut,
    };
}
