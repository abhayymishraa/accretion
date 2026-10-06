"use client";

import { useRequireSession } from "@/hooks/auth/useHasSession";
import { message } from "@/hooks/skills/useSkillLibrary";
import { connectionService } from "@/services/service.connections";
import type { Connection } from "@/types/connection.type";
import { toast } from "sonner";
import useSWR from "swr";

/** The Connections page: the catalog, the user's servers, and every change to them. */
export function useConnections() {
    const hasSession = useRequireSession();
    const servers = useSWR(hasSession ? ["/mcp-servers"] : null, () => connectionService.list());
    const catalog = useSWR(hasSession ? ["/mcp-catalog"] : null, () => connectionService.catalog());

    /** Runs a change that returns the server, puts it in the list, and returns the error to show, or "". */
    async function attempt(work: () => Promise<Connection | void>, fallback: string) {
        try {
            const saved = await work();
            if (saved)
                await servers.mutate(
                    (list = []) =>
                        list.some((item) => item.id === saved.id)
                            ? list.map((item) => (item.id === saved.id ? saved : item))
                            : [...list, saved],
                    { revalidate: false },
                );
            else await servers.mutate();
            return "";
        } catch (reason) {
            return message(reason, fallback);
        }
    }

    const show = (error: string) => {
        if (error) toast.error(error);
        return error;
    };

    return {
        servers: servers.data ?? null,
        catalog: catalog.data ?? null,
        error:
            servers.error || catalog.error
                ? message(servers.error ?? catalog.error, "Could not load your connections.")
                : "",
        retry: () => Promise.all([servers.mutate(), catalog.mutate()]),
        add: (source: { catalog_id: string } | { url: string; title?: string }) =>
            attempt(() => connectionService.add(source), "Could not add this server."),
        saveKey: (id: string, value: string, headerName?: string) =>
            attempt(
                () => connectionService.saveKey(id, value, headerName),
                "Could not save the key.",
            ),
        clearKey: async (id: string) =>
            show(await attempt(() => connectionService.clearKey(id), "Could not save.")),
        saveIcon: async (id: string, dataUri: string) =>
            show(
                await attempt(
                    () => connectionService.saveIcon(id, dataUri),
                    "Could not save the logo.",
                ),
            ),
        approve: async (id: string, approved: string[]) =>
            show(
                await attempt(
                    () => connectionService.approveTools(id, approved),
                    "Could not save.",
                ),
            ),
        refresh: async (id: string) =>
            show(
                await attempt(
                    () => connectionService.refreshTools(id),
                    "Could not check the tools.",
                ),
            ),
        setEnabled: async (id: string, enabled: boolean) =>
            show(await attempt(() => connectionService.setEnabled(id, enabled), "Could not save.")),
        remove: async (id: string) =>
            show(await attempt(() => connectionService.remove(id), "Could not remove it.")),
        /** Sends the browser to the server's sign-in page, in this tab: in-app browsers block new windows. */
        signIn: async (id: string) => {
            try {
                window.location.assign(await connectionService.beginSignIn(id));
            } catch (reason) {
                toast.error(message(reason, "Could not start the sign-in."));
            }
        },
    };
}

export type Connections = ReturnType<typeof useConnections>;
