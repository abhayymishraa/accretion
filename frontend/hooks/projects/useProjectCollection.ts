"use client";

import { reloadProjects } from "@/hooks/projects/useProjectList";
import { filterProjects, type ProjectPeriod, type ProjectSort } from "@/lib/projects/filters";
import { projectService } from "@/services/service.projects";
import type { Project } from "@/types/project.type";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState, type PointerEvent } from "react";
import { toast } from "sonner";

export function useProjectCollection(compact: boolean, onOpen?: () => void) {
    const pathname = usePathname();
    const router = useRouter();
    const id = useId();
    const searchRef = useRef<HTMLInputElement>(null);
    const deleteTrigger = useRef<HTMLButtonElement | null>(null);
    const spotlightEnabled = useRef(false);
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [query, setQuery] = useState("");
    const [sort, setSort] = useState<ProjectSort>("recent");
    const [period, setPeriod] = useState<ProjectPeriod>("all");
    const [attempt, setAttempt] = useState(0);
    const [pendingDelete, setPendingDelete] = useState<Project | null>(null);
    // Keep the description intact while Radix finishes the closing animation.
    const [deleteTitle, setDeleteTitle] = useState("");
    const [dialogMotion, setDialogMotion] = useState<"open" | "closed" | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [deleteError, setDeleteError] = useState("");

    useEffect(() => {
        if (compact) return;
        const media = window.matchMedia(
            "(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)",
        );
        const sync = () => {
            spotlightEnabled.current = media.matches;
        };
        sync();
        media.addEventListener("change", sync);
        return () => {
            spotlightEnabled.current = false;
            media.removeEventListener("change", sync);
        };
    }, [compact]);

    // Adapted from React Bits SpotlightCard; see REACT-BITS-LICENSE.
    // https://github.com/DavidHDev/react-bits/blob/3a1c7f2f9f94ed833934ab5c2635760b9e644583/src/ts-default/Components/SpotlightCard/SpotlightCard.tsx
    function moveSpotlight(event: PointerEvent<HTMLAnchorElement>) {
        if (!spotlightEnabled.current || event.pointerType !== "mouse") return;
        const card = event.currentTarget;
        const bounds = card.getBoundingClientRect();
        card.style.setProperty("--spotlight-x", `${event.clientX - bounds.left}px`);
        card.style.setProperty("--spotlight-y", `${event.clientY - bounds.top}px`);
    }

    async function deleteProject() {
        if (!pendingDelete || deletingId) return;
        const project = pendingDelete;
        setDeletingId(project.id);
        setDeleteError("");
        try {
            const result = await projectService.deleteProject(project.id);
            setProjects((current) => current.filter((item) => item.id !== project.id));
            reloadProjects();
            setPendingDelete(null);
            const cleanupPending =
                result.storage_cleanup !== "completed" || result.sandbox_cleanup !== "completed";
            toast.success(cleanupPending ? "Project removed; cleanup pending" : "Project deleted", {
                description: cleanupPending
                    ? "Some files or the preview are still being removed. Cleanup will retry automatically."
                    : "Saved files were removed and the preview was stopped.",
            });
            if (pathname === `/chat/${project.id}`) {
                onOpen?.();
                router.replace("/projects");
            }
        } catch (error) {
            setDeleteError(
                error instanceof Error
                    ? error.message
                    : "Could not delete the project. Please try again.",
            );
        } finally {
            setDeletingId(null);
        }
    }

    useEffect(() => {
        let disposed = false;
        projectService
            .listProjects()
            .then((response) => {
                if (!disposed) setProjects(response.projects);
            })
            .catch(() => {
                if (!disposed) setError("Could not load your projects. Please try again.");
            })
            .finally(() => {
                if (!disposed) setLoading(false);
            });
        return () => {
            disposed = true;
        };
    }, [attempt]);

    const visible = filterProjects(projects, query, sort, period);
    const narrowed = Boolean(query.trim()) || period !== "all";
    const changed = narrowed || sort !== "recent";
    function resetFilters() {
        setQuery("");
        setPeriod("all");
        setSort("recent");
        searchRef.current?.focus();
    }

    return {
        id,
        searchRef,
        deleteTrigger,
        projects,
        loading,
        error,
        query,
        setQuery,
        sort,
        setSort,
        period,
        setPeriod,
        setAttempt,
        setLoading,
        setError,
        pendingDelete,
        setPendingDelete,
        deleteTitle,
        setDeleteTitle,
        dialogMotion,
        setDialogMotion,
        deletingId,
        deleteError,
        setDeleteError,
        moveSpotlight,
        deleteProject,
        visible,
        narrowed,
        changed,
        resetFilters,
    };
}
