"use client";

import { secretService } from "@/services/service.secrets";
import useSWR from "swr";

// The backend's rule (agent/sandbox/secrets.py NAME), checked here so a typo is caught before a request.
export const SECRET_NAME = /^[A-Z_][A-Z0-9_]{0,127}$/;
// A name starting with one of these is built into the web page, where every visitor can read it.
export const PUBLIC = /^(VITE_|NEXT_PUBLIC_)/;

/** What a person types as a name, in the form keys take: "stripe key" becomes STRIPE_KEY. */
export function secretName(typed: string): string {
    return typed
        .trim()
        .toUpperCase()
        .replace(/[^A-Z0-9_]+/g, "_");
}

/**
 * A project's keys by name. A save or delete answers with the new list, which replaces the cached one;
 * each returns an error message, or "" when it worked.
 */
export function useProjectSecrets(projectId: string) {
    const { data, error, mutate } = useSWR(["/projects", projectId, "secrets"] as const, ([, id]) =>
        secretService.list(id),
    );
    const run = async (write: () => ReturnType<typeof secretService.list>) => {
        try {
            await mutate(await write(), { revalidate: false });
            return "";
        } catch (cause) {
            return cause instanceof Error ? cause.message : "Could not save the key.";
        }
    };
    return {
        secrets: data ?? null,
        failed: Boolean(error),
        retry: () => mutate(),
        save: (name: string, value: string) =>
            run(() => secretService.save(projectId, name, value)),
        remove: (name: string) => run(() => secretService.remove(projectId, name)),
    };
}
