"use client";

import { useDemoRuns } from "@/hooks/admin/useDemoAccounts";

/** A demo account's builds, newest first: what was asked and how it ended. */
export function DemoRuns({ userId }: { userId: number }) {
    const { runs, error } = useDemoRuns(userId);
    if (error) return <p className="text-[13px] text-destructive">{error}</p>;
    if (!runs)
        return (
            <p role="status" className="text-[13px] text-muted-foreground">
                Loading builds…
            </p>
        );
    if (!runs.length) return <p className="text-[13px] text-muted-foreground">No builds yet.</p>;
    return (
        <ol data-loaded-in="" aria-label="Builds" className="grid gap-2">
            {runs.map((run) => (
                <li key={run.id} className="rounded-lg border border-border bg-surface-2 p-3">
                    <p className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-[12px] text-muted-foreground">
                        <span className="min-w-0 truncate">
                            {run.project_title ?? "Untitled project"}
                        </span>
                        <span className="font-mono">
                            {run.status} ·{" "}
                            {new Date(run.created_at).toLocaleString(undefined, {
                                dateStyle: "medium",
                                timeStyle: "short",
                            })}
                        </span>
                    </p>
                    <p className="mt-1.5 line-clamp-4 text-[13.5px] whitespace-pre-wrap wrap-anywhere">
                        {run.prompt}
                    </p>
                </li>
            ))}
        </ol>
    );
}
