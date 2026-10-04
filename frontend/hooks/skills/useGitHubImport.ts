"use client";

import { skillService } from "@/services/service.skills";
import type { GitHubSkills, ImportResult } from "@/types/skill.type";
import { useState } from "react";
import { useSWRConfig } from "swr";
import { message } from "./useSkillLibrary";

/** From GitHub: find the skills in a repository, choose some, import them into the library. */
export function useGitHubImport() {
    const { mutate: refresh } = useSWRConfig();
    const [found, setFound] = useState<GitHubSkills | null>(null);
    const [chosen, setChosen] = useState<Set<string>>(new Set());
    const [result, setResult] = useState<ImportResult | null>(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");

    async function discover(url: string) {
        setBusy(true);
        setError("");
        setResult(null);
        try {
            const next = await skillService.discoverGitHub(url);
            setFound(next);
            setChosen(new Set(next.skills.map((skill) => skill.path)));
        } catch (reason) {
            setFound(null);
            setError(message(reason, "Could not read that repository. Try again."));
        } finally {
            setBusy(false);
        }
    }

    function toggle(path: string) {
        setChosen((current) => {
            const next = new Set(current);
            if (!next.delete(path)) next.add(path);
            return next;
        });
    }

    async function importChosen(url: string) {
        setBusy(true);
        setError("");
        try {
            setResult(await skillService.importGitHub(url, [...chosen]));
            await refresh(["/skills"]);
        } catch (reason) {
            setError(message(reason, "Could not import these skills. Try again."));
        } finally {
            setBusy(false);
        }
    }

    function reset() {
        setFound(null);
        setChosen(new Set());
        setResult(null);
        setError("");
    }

    return { found, chosen, result, busy, error, discover, toggle, importChosen, reset };
}
