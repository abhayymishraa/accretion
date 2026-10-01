"use client";

import { renameProject, useProjectList } from "@/hooks/projects/useProjectList";
import { useEffect, useRef, useState } from "react";

// Typing pauses this long before the name is saved; Enter and blur save at once.
const SAVE_DELAY_MS = 500;

/** The open project's name, and a debounced rename that shows everywhere before it saves. */
export function useProjectTitle(projectId: string) {
    const projects = useProjectList();
    const title = projects?.find((project) => project.id === projectId)?.title ?? null;
    const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
    const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

    // ponytail: saves are not serialized; a slow debounced save can land after a later Enter.
    const save = async (value: string) => {
        clearTimeout(timer.current);
        const next = value.trim();
        if (!next || next === title) return;
        setStatus("saving");
        try {
            await renameProject(projectId, next);
            setStatus("saved");
        } catch {
            setStatus("error");
        }
    };
    const saveSoon = (value: string) => {
        clearTimeout(timer.current);
        timer.current = setTimeout(() => void save(value), SAVE_DELAY_MS);
    };

    useEffect(() => () => clearTimeout(timer.current), []);
    useEffect(() => {
        if (status !== "saved") return;
        const fade = setTimeout(() => setStatus("idle"), 1500);
        return () => clearTimeout(fade);
    }, [status]);

    return { title, projects, status, save, saveSoon };
}
