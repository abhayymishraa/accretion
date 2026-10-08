"use client";

import { NAME_ARRIVES } from "@/components/chat/ProjectTitle";
import { useNameArrivals, useProjectList } from "@/hooks/projects/useProjectList";
import { projectName } from "@/lib/projects/filters";
import type { Project } from "@/types/project.type";
import { AppWindow, CircleDashed } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const SHOWN_DRAFTS = 3;
export const SIDEBAR_ROW =
    "flex min-h-8 pointer-coarse:min-h-11 w-full min-w-0 cursor-pointer items-center gap-2.5 rounded-[8px] px-2.5 text-left text-[12.5px] text-muted-foreground no-underline [transition:background-color_130ms_ease,color_130ms_ease] focus-visible:outline-2 focus-visible:outline-ring aria-[current=page]:bg-surface-2 aria-[current=page]:text-foreground pointer-fine:hover:bg-surface-2 pointer-fine:hover:text-foreground [&>svg]:shrink-0";

function Group({
    label,
    projects,
    current,
    draft,
    arriving,
    onSettle,
}: {
    label: string;
    projects: Project[];
    current: string | undefined;
    draft: boolean;
    arriving: string[];
    onSettle: (id: string) => void;
}) {
    if (!projects.length) return null;
    const Icon = draft ? CircleDashed : AppWindow;
    return (
        <div className="grid gap-px">
            <p className="m-0 px-2.5 pb-1 text-[11px] text-muted-foreground">{label}</p>
            {projects.map((project) => (
                <Link
                    key={project.id}
                    href={`/chat/${project.id}`}
                    title={projectName(project)}
                    aria-current={project.id === current ? "page" : undefined}
                    className={SIDEBAR_ROW}
                >
                    <Icon size={14} strokeWidth={1.6} aria-hidden="true" />
                    <span
                        key={arriving.includes(project.id) ? "arrived" : "steady"}
                        onTransitionEnd={() => onSettle(project.id)}
                        className={`min-w-0 truncate ${arriving.includes(project.id) ? NAME_ARRIVES : ""} [transition:opacity_200ms_var(--ease-out),translate_200ms_var(--ease-out)]`}
                    >
                        {projectName(project)}
                    </span>
                </Link>
            ))}
        </div>
    );
}

/** Drafts (no build saved yet) and recent projects, filtered by the sidebar search. */
export function SidebarProjects({ query }: { query: string }) {
    const projects = useProjectList();
    const pathname = usePathname();
    const [allDrafts, setAllDrafts] = useState(false);
    const { arriving, settle } = useNameArrivals(projects);
    const current = pathname.startsWith("/chat/") ? pathname.slice("/chat/".length) : undefined;
    if (!projects)
        return (
            <div className="grid gap-2 px-2.5 pt-2" aria-hidden="true">
                {[70, 55, 62].map((width) => (
                    <span
                        key={width}
                        className="h-2.5 animate-pulse rounded-full bg-surface-2 motion-reduce:animate-none"
                        style={{ width: `${width}%` }}
                    />
                ))}
            </div>
        );
    const needle = query.trim().toLowerCase();
    const matches = needle
        ? projects.filter((project) => projectName(project).toLowerCase().includes(needle))
        : projects;
    const drafts = matches.filter((project) => !project.latest_saved_revision_id);
    const built = matches.filter((project) => project.latest_saved_revision_id);
    if (!matches.length)
        return (
            <p className="m-0 px-2.5 pt-2 text-[12px] text-muted-foreground">
                {needle ? "No projects match." : "Your projects will show up here."}
            </p>
        );
    const hiddenDrafts = needle || allDrafts ? 0 : drafts.length - SHOWN_DRAFTS;
    return (
        <div className="grid gap-4">
            <div className="grid gap-px">
                <Group
                    label="Drafts"
                    projects={hiddenDrafts > 0 ? drafts.slice(0, SHOWN_DRAFTS) : drafts}
                    current={current}
                    draft
                    arriving={arriving}
                    onSettle={settle}
                />
                {hiddenDrafts > 0 && (
                    <button
                        type="button"
                        onClick={() => setAllDrafts(true)}
                        className={`${SIDEBAR_ROW} pl-[34px] text-[12px]`}
                    >
                        Show {hiddenDrafts} more
                    </button>
                )}
            </div>
            <Group
                label="Recent"
                projects={built}
                current={current}
                draft={false}
                arriving={arriving}
                onSettle={settle}
            />
        </div>
    );
}
