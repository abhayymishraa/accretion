"use client";

import { useRequireSession } from "@/hooks/auth/useHasSession";
import { skillService } from "@/services/service.skills";
import type { SkillDraft, SkillSummary } from "@/types/skill.type";
import { toast } from "sonner";
import useSWR, { useSWRConfig, type KeyedMutator } from "swr";

export const message = (reason: unknown, fallback: string) =>
    reason instanceof Error ? reason.message : fallback;

/** Changes one skill in a cached list at once, saves it, and rolls back with a toast if the save
 * fails. Returns whether it saved. */
export async function patchSkill<T extends { name: string }>(
    mutate: KeyedMutator<T[]>,
    name: string,
    patch: Partial<T>,
    save: () => Promise<unknown>,
): Promise<boolean> {
    const apply = (list: T[] = []) =>
        list.map((skill) => (skill.name === name ? { ...skill, ...patch } : skill));
    try {
        await mutate(
            async (current) => {
                await save();
                return apply(current);
            },
            { optimisticData: apply, rollbackOnError: true, revalidate: false },
        );
        return true;
    } catch (reason) {
        toast.error(message(reason, "Could not save. Try again."));
        return false;
    }
}

/** The Skills page: built-in skills and the user's own, with create, edit and delete. */
export function useSkillLibrary() {
    const hasSession = useRequireSession();
    const { mutate: refresh } = useSWRConfig();
    const { data, error, mutate } = useSWR(hasSession ? ["/skills"] : null, () =>
        skillService.list(),
    );

    /** Runs a change, then reloads the list; returns the error to show, or "". */
    async function attempt(work: () => Promise<unknown>, fallback: string): Promise<string> {
        try {
            await work();
            await mutate();
            return "";
        } catch (reason) {
            return message(reason, fallback);
        }
    }

    /** Saves a new skill, or edits one. */
    const save = (draft: SkillDraft, id?: string) =>
        attempt(async () => {
            if (!id) return skillService.create(draft);
            const { description, instructions } = draft;
            await skillService.update(id, { description, instructions });
            await refresh(["/skills", id]);
        }, "Could not save. Try again.");

    /** Imports a .md, .mdx or .zip skill file. */
    const importFile = (file: File) =>
        attempt(() => skillService.importFile(file), "Could not import this file. Try again.");

    const remove = (id: string) =>
        attempt(() => skillService.remove(id), "Could not delete. Try again.");

    /** Turns a skill on or off for every project; shows at once and rolls back if the save fails. */
    async function setEverywhere(name: string, enabled: boolean) {
        const saved = await patchSkill(mutate, name, { off_everywhere: !enabled }, () =>
            skillService.setEverywhere(name, enabled),
        );
        // Every loaded project list now shows the skill's new state.
        if (saved)
            await refresh(
                (key) => Array.isArray(key) && key[0] === "/projects" && key[2] === "skills",
            );
    }

    return {
        skills: data ?? null,
        error: error instanceof Error ? error.message : "",
        retry: () => mutate(),
        save,
        importFile,
        remove,
        setEverywhere,
    };
}

/** A skill's full instructions for the preview: a library skill by id, a built-in one by name. */
export function useSkillPreview(skill: SkillSummary | null) {
    // A library skill shares the edit form's key, so a saved edit shows here at once.
    const key = !skill ? null : skill.id ? ["/skills", skill.id] : ["/skills/builtin", skill.name];
    const { data, error } = useSWR(key, ([path, value]: string[]) =>
        path === "/skills" ? skillService.get(value) : skillService.builtin(value),
    );
    return {
        instructions: data?.instructions ?? null,
        error: error instanceof Error ? error.message : "",
    };
}

/** One library skill with its instructions, for the edit form; nothing is fetched without an id. */
export function useSkillDetail(id: string | null) {
    const { data, error } = useSWR(id ? (["/skills", id] as const) : null, ([, skillId]) =>
        skillService.get(skillId),
    );
    return { skill: data ?? null, error: error instanceof Error ? error.message : "" };
}
