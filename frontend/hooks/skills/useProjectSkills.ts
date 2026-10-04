"use client";

import { skillService } from "@/services/service.skills";
import { useState } from "react";
import { toast } from "sonner";
import { patchSkill } from "./useSkillLibrary";
import useSWR, { useSWRConfig } from "swr";

/**
 * The skills a project can use. Nothing is fetched until the "/" menu first opens (a null key until
 * then); SWR keeps the list per project after that. Turning a skill on or off shows at once and
 * rolls back if the save fails.
 */
export function useProjectSkills(projectId: string) {
    const [wanted, setWanted] = useState(false);
    const { mutate: refresh } = useSWRConfig();
    const { data, error, mutate } = useSWR(
        wanted ? (["/projects", projectId, "skills"] as const) : null,
        ([, id]) => skillService.forProject(id),
    );

    const setEnabled = (name: string, enabled: boolean) =>
        patchSkill(mutate, name, { enabled }, () =>
            skillService.setEnabled(projectId, name, enabled),
        );

    /** Copies one of the project's own skills into the library, so every project gets it. */
    async function saveToLibrary(name: string) {
        try {
            await skillService.saveToLibrary(projectId, name);
            // Marked at once: the saved copy is hidden behind the project's own, so no refetch shows it.
            await mutate(
                (list = []) =>
                    list.map((skill) =>
                        skill.source === "project" && skill.name === name
                            ? { ...skill, in_library: true }
                            : skill,
                    ),
                { revalidate: false },
            );
            await refresh(["/skills"]);
            toast.success(`/${name} is in your library`);
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Could not save. Try again.");
        }
    }

    return {
        skills: data ?? null,
        error: error instanceof Error ? error.message : "",
        retry: () => mutate(),
        ensureLoaded: () => setWanted(true),
        setEnabled,
        saveToLibrary,
    };
}

export type ProjectSkills = ReturnType<typeof useProjectSkills>;
