"use client";

import { subscribeSession } from "@/lib/auth/session";
import { projectService } from "@/services/service.projects";
import type { Project } from "@/types/project.type";
import { useEffect, useSyncExternalStore } from "react";

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

function load() {
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

/** The user's projects, newest first; null until the first load. Reloads on every mount. */
export function useProjectList() {
    const list = useSyncExternalStore(
        subscribe,
        () => projects,
        () => null,
    );
    useEffect(load, []);
    return list;
}

/** Saves a project's new name, showing it everywhere before the server answers. */
export async function renameProject(id: string, title: string) {
    const previous = projects;
    projects =
        projects?.map((project) => (project.id === id ? { ...project, title } : project)) ?? null;
    notify();
    try {
        await projectService.renameProject(id, title);
    } catch (error) {
        projects = previous;
        notify();
        throw error;
    }
}
