"use client";

import { useRequireSession } from "@/hooks/auth/useHasSession";
import { usersService } from "@/services/service.users";
import type { DemoLink } from "@/types/auth.type";
import { useState } from "react";
import { toast } from "sonner";
import useSWR from "swr";

/** The link a demo account is opened with; the prompt, when given, waits in its composer. */
function demoUrl(link: DemoLink, prompt: string) {
    const hash = new URLSearchParams({ token: link.token });
    if (prompt.trim()) hash.set("q", prompt.trim());
    return `${window.location.origin}/demo#${hash}`;
}

/** The admin's demo accounts: each one's link, made, replaced and revoked here, and its builds. */
export function useDemoAccounts() {
    const hasSession = useRequireSession();
    const { data, error, mutate } = useSWR(hasSession ? ["/users/demo"] : null, () =>
        usersService.listDemo(),
    );
    const [pending, setPending] = useState<number | "new" | null>(null);
    // The newest link and its account, shown once: the server keeps only its digest.
    const [link, setLink] = useState<{ userId: number; url: string } | null>(null);

    async function run(key: number | "new", work: () => Promise<DemoLink | void>, prompt = "") {
        setPending(key);
        try {
            const made = await work();
            // A revoke clears the link only when it is that account's: another one's may not be copied yet.
            if (made) setLink({ userId: made.user_id, url: demoUrl(made, prompt) });
            else setLink((shown) => (shown?.userId === key ? null : shown));
            await mutate();
            return true;
        } catch (err) {
            toast.error(err instanceof Error ? err.message : "Could not save.");
            return false;
        } finally {
            setPending(null);
        }
    }

    return {
        accounts: data ?? null,
        error: error instanceof Error ? error.message : "",
        pending,
        link: link?.url ?? null,
        create: (name: string, prompt: string) =>
            run("new", () => usersService.createDemo(name), prompt),
        replace: (userId: number, prompt: string) =>
            run(userId, () => usersService.replaceDemoLink(userId), prompt),
        revoke: (userId: number) => run(userId, () => usersService.revokeDemoLink(userId)),
    };
}

/** One demo account's builds, fetched when the admin opens them. */
export function useDemoRuns(userId: number) {
    const { data, error } = useSWR(["/users", userId, "runs"], () => usersService.runs(userId));
    return { runs: data ?? null, error: error instanceof Error ? error.message : "" };
}
