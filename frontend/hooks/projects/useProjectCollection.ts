"use client";

import { reloadProjects } from "@/hooks/projects/useProjectList";
import { filterProjects, type ProjectPeriod, type ProjectSort } from "@/lib/projects/filters";
import { projectService } from "@/services/service.projects";
import type { Project } from "@/types/project.type";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { toast } from "sonner";

export function useProjectCollection(onOpen?: () => void) {
    const pathname = usePathname();
    const router = useRouter();
    const id = useId();
    const searchRef = useRef<HTMLInputElement>(null);
    const deleteTrigger = useRef<HTMLButtonElement | null>(null);
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

    async function deleteProject() {
        if (!pendingDelete || deletingId) return;
        const project = pendingDelete;
        setDeletingId(project.id);
        setDeleteError("");
        try {
            await projectService.deleteProject(project.id);
            const remove = () => {
                setProjects((current) => current.filter((item) => item.id !== project.id));
                setPendingDelete(null);
            };
            // The other cards slide into the gap instead of jumping; without the API, or with
            // reduced motion, the card is removed at once.
            if (
                "startViewTransition" in document &&
                !window.matchMedia("(prefers-reduced-motion: reduce)").matches
            ) {
                document.startViewTransition(() => flushSync(remove));
            } else {
                remove();
            }
            reloadProjects();
            toast.success("Project deleted");
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
        deleteProject,
        visible,
        narrowed,
        changed,
        resetFilters,
    };
}
