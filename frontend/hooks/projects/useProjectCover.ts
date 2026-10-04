"use client";

import { projectService } from "@/services/service.projects";
import useSWR from "swr";

/** An object URL for a project's card image, keyed by its id so a new cover refetches. */
export function useProjectCover(projectId: string, coverId: string | null) {
    const { data, error } = useSWR(
        coverId ? ["/projects/cover", projectId, coverId] : null,
        // ponytail: the URL is never revoked; one small image per project for the session.
        async ([, id, cover]) => URL.createObjectURL(await projectService.cover(id, cover)),
        { revalidateOnFocus: false, shouldRetryOnError: false },
    );
    return { url: data ?? null, loading: Boolean(coverId) && !data && !error };
}
