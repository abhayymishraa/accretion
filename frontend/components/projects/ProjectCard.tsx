"use client";

import { ProjectCover } from "@/components/projects/ProjectCover";
import styles from "@/components/projects/project-shelf.module.css";
import { Button } from "@/components/ui/button";
import { projectName } from "@/lib/projects/filters";
import type { Project } from "@/types/project.type";
import { Trash2 } from "lucide-react";
import Link from "next/link";
import type { MouseEvent } from "react";

function createdLabel(value: string) {
    const date = new Date(value);
    return Number.isFinite(date.getTime())
        ? date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
        : "Date unavailable";
}

export function ProjectCard({
    project,
    compact,
    deleting,
    onOpen,
    onDelete,
}: {
    project: Project;
    compact: boolean;
    deleting: boolean;
    onOpen?: () => void;
    onDelete: (event: MouseEvent<HTMLButtonElement>) => void;
}) {
    return (
        <article
            // Named so a delete can slide the other cards into its place (globals.css, *.project).
            style={{ viewTransitionName: `project-${project.id}`, viewTransitionClass: "project" }}
            className={`${styles.cardEnter} flex min-w-0 flex-col ${compact ? "rounded-xl border border-border bg-card" : ""}`}
        >
            <Link
                href={`/chat/${project.id}`}
                onClick={onOpen}
                className={`flex min-w-0 flex-col text-foreground no-underline focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-4 ${compact ? "gap-3 rounded-xl p-4" : `${styles.card} gap-3 rounded-2xl`}`}
            >
                {!compact && (
                    <div className="relative aspect-[16/10] overflow-hidden rounded-2xl border border-border bg-surface-2">
                        <ProjectCover projectId={project.id} version={project.cover_updated_at} />
                    </div>
                )}
                <h2
                    className={`wrap-anywhere ${compact ? "text-base font-medium" : "line-clamp-2 px-1 text-base font-medium"}`}
                >
                    {projectName(project)}
                </h2>
                {compact && (
                    <span className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span aria-hidden="true" className="text-accent-foreground">
                            &gt;
                        </span>{" "}
                        Open workspace
                    </span>
                )}
            </Link>
            <div
                className={`flex min-h-11 items-center justify-between gap-2 ${compact ? "px-2" : "px-1"}`}
            >
                <p className="text-xs text-muted-foreground">
                    Created {createdLabel(project.created_at)}
                </p>
                <Button
                    variant="utility"
                    aria-label={`Delete ${projectName(project)}`}
                    disabled={deleting}
                    onClick={onDelete}
                    className="shrink-0 px-2"
                >
                    <Trash2 size={14} aria-hidden="true" />
                    <span className={compact ? "" : "sr-only"}>Delete</span>
                </Button>
            </div>
        </article>
    );
}
