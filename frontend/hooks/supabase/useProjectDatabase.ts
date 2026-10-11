"use client";

import { message } from "@/hooks/skills/useSkillLibrary";
import { supabaseService } from "@/services/service.supabase";
import type { LinkDatabase, ProjectDatabase } from "@/types/supabase.type";
import useSWR from "swr";

// Creating a project and moving data run in the background; the status is read again this often. Our API
// answers it from its own row, so it costs no call to Supabase.
const BUSY_POLL_MS = 5000;
export const databaseBusy = (database?: ProjectDatabase) =>
    database?.status === "creating" || database?.status === "moving";

/** The Database tab: the project's Supabase link, and linking or unlinking one. */
export function useProjectDatabase(projectId: string) {
    const database = useSWR(
        ["/projects", projectId, "database"] as const,
        ([, id]) => supabaseService.database(id),
        { refreshInterval: (latest) => (databaseBusy(latest) ? BUSY_POLL_MS : 0) },
    );
    const account = useSWR(["/supabase/account"], () => supabaseService.account());
    return {
        database: database.data ?? null,
        account: account.data ?? null,
        failed: Boolean(database.error || account.error),
        retry: () => Promise.all([database.mutate(), account.mutate()]),
        /** Each returns the error to show, or "". */
        link: async (body: LinkDatabase) => {
            try {
                await database.mutate(await supabaseService.link(projectId, body), {
                    revalidate: false,
                });
                return "";
            } catch (reason) {
                return message(reason, "Could not connect the database.");
            }
        },
        unlink: async () => {
            try {
                await supabaseService.unlink(projectId);
                await database.mutate();
                return "";
            } catch (reason) {
                return message(reason, "Could not disconnect the database.");
            }
        },
    };
}

/** The choices the link form offers: regions, and the projects in the chosen organization. */
export function useDatabaseChoices(organizationId: string) {
    const regions = useSWR(["/supabase/regions"], () => supabaseService.regions());
    const projects = useSWR(
        organizationId ? (["/supabase/projects", organizationId] as const) : null,
        ([, id]) => supabaseService.projects(id),
        { keepPreviousData: true },
    );
    return {
        regions: regions.data ?? null,
        projects: projects.data ?? null,
        failed: Boolean(regions.error || projects.error),
    };
}
