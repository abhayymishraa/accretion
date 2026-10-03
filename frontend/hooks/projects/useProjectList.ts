"use client";

import { subscribeSession } from "@/lib/auth/session";
import { projectService } from "@/services/service.projects";
import type { Project } from "@/types/project.type";
import { useEffect, useState, useSyncExternalStore } from "react";

// One list shared by the sidebar and the builder's title, so a rename shows in both at once.
let projects: Project[] | null = null;
let loading: Promise<void> | null = null;
const listeners = new Set<() => void>();

const notify = () => listeners.forEach((listener) => listener());

function subscribe(listener: () => void) {
    listeners.add(listener);
    // Another account must never see the previous one's projects.
    const unsubscribeSession = subscribeSession(() => {
        projects = null;
        notify();
    });
    return () => {
        listeners.delete(listener);
        unsubscribeSession();
    };
}

/** Loads the list; also catches up on names given while the page was not listening. */
export function reloadProjects() {
    loading ??= projectService
        .listProjects()
        .then((response) => {
            projects = response.projects;
        })
        // Navigation only: on failure the sidebar shows what it last had, or nothing.
        .catch(() => {})
        .finally(() => {
            loading = null;
            notify();
        });
}

/**
 * The user's projects, newest first; null until the first load. Loaded once per page, then kept
 * current by events (a new prompt, a delete, a project not yet listed), not on every mount.
 */
export function useProjectList() {
    const list = useSyncExternalStore(
        subscribe,
        () => projects,
        () => null,
    );
    useEffect(() => {
        if (projects === null) reloadProjects();
    }, []);
    return list;
}

/** Reloads when a project opened here is not listed yet, such as one just created. */
export function listProject(id: string) {
    if (projects && !projects.some((project) => project.id === id)) reloadProjects();
}

/** Shows a name the server already saved: one the AI gave a new project, pushed over its socket. */
export function showProjectTitle(id: string, title: string) {
    projects =
        projects?.map((project) => (project.id === id ? { ...project, title } : project)) ?? null;
    notify();
}

/**
 * Projects seen untitled here that have since been named: their AI name fades in once (plans/001).
 * React state, not a module flag, so React Compiler's memoisation sees the change.
 */
export function useNameArrivals(list: Project[] | null) {
    const [watched, setWatched] = useState<string[]>([]);
    const untitled = (list ?? []).filter((p) => !p.title && !watched.includes(p.id));
    if (untitled.length) setWatched([...watched, ...untitled.map((p) => p.id)]);
    const arriving = watched.filter((id) => list?.some((p) => p.id === id && p.title));
    const settle = (id: string) => setWatched((ids) => ids.filter((watchedId) => watchedId !== id));
    return { arriving, settle };
}

/** Saves a project's new name, showing it everywhere before the server answers. */
export async function renameProject(id: string, title: string) {
    const previous = projects;
    showProjectTitle(id, title);
    try {
        await projectService.renameProject(id, title);
    } catch (error) {
        projects = previous;
        notify();
        throw error;
    }
}
