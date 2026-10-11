"use client";

import { repoBusy, useRepoStatus } from "@/hooks/github/useProjectRepo";
import { CircleCheck, LoaderCircle, TriangleAlert } from "lucide-react";

// A link inside the GitHub tab: its repository, a pull request, the way to reconnect.
export const PANEL_LINK =
    "inline-flex min-h-11 items-center gap-1.5 rounded-[4px] text-[13px] font-medium text-primary no-underline focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:underline";

/** The one plain status line: a check when fine, a turning ring while work runs, a warning when it needs the user.
 * GitHub's line truncates; a database message wraps. */
export function StatusLine({
    busy,
    fine,
    text,
    wrap = false,
    className = "",
}: {
    busy: boolean;
    fine: boolean;
    text: string;
    wrap?: boolean;
    className?: string;
}) {
    const Icon = busy ? LoaderCircle : fine ? CircleCheck : TriangleAlert;
    return (
        <p role="status" className={`flex min-w-0 items-center gap-1.5 ${className}`}>
            <Icon
                size={14}
                aria-hidden="true"
                className={`shrink-0 ${busy ? "text-muted-foreground motion-safe:animate-spin" : fine ? "text-emerald-700 dark:text-[#22c55e]" : "text-amber-700 dark:text-amber-300"}`}
            />
            <span className={wrap ? "" : "truncate"}>{text}</span>
        </p>
    );
}

/** The project's GitHub status beside its name. Nothing shows until the project saves to GitHub. */
export function RepoStatus({ projectId }: { projectId: string }) {
    const { data } = useRepoStatus(projectId);
    if (!data?.linked) return null;
    return (
        <StatusLine
            busy={repoBusy(data)}
            fine={data.status === "synced"}
            text={data.message ?? "Saved to GitHub"}
            className="ml-auto pl-3 text-[12px] text-muted-foreground"
        />
    );
}
