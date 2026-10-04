"use client";

import { projectService } from "@/services/service.projects";
import useSWR from "swr";

/** An object URL for a project's card image, keyed by its version so a new cover refetches. */
export function useProjectCover(projectId: string, version: string | null) {
    const { data, error } = useSWR(
        version ? ["/projects/cover", projectId, version] : null,
        // ponytail: the URL is never revoked; one small image per project for the session.
        async ([, id, v]) => URL.createObjectURL(await projectService.cover(id, v)),
        { revalidateOnFocus: false, shouldRetryOnError: false },
    );
    return { url: data ?? null, loading: Boolean(version) && !data && !error };
}
