"use client";

import { ListCollapse, ShieldCheck } from "lucide-react";
import { useState } from "react";

import type { TimelineBlock } from "@/lib/chat/tool-lines";
import { ROW, RowChevron, ShellBlock, TOGGLE } from "./ToolBlocks";

type Step = { ok?: boolean; stdout?: string; stderr?: string; exit_code?: number };
type BuildChecks = {
    ok: boolean;
    build: Step;
    migration?: Step & { migrations?: string; files?: string[]; output?: string };
};

/** The host's final check as one row, like a command: its output opens in a Shell block. */
function BuildCheck({ checks }: { checks: BuildChecks }) {
    // A failure opens on its own, showing the errors the model was asked to fix.
    const [open, setOpen] = useState(!checks.ok);
    const { build, migration } = checks;
    const migrations =
        migration?.migrations === "unchanged"
            ? "no new migrations"
            : migration?.ok
              ? `${migration.files?.length ?? 0} migrations applied`
              : migration
                ? `migration ${migration.migrations?.replaceAll("_", " ")}`
                : "";
    const summary = ["typecheck", "build", migrations].filter(Boolean).join(" · ");
    return (
        <div className="min-w-0">
            <div className={ROW} data-failed={!checks.ok}>
                <button
                    type="button"
                    aria-expanded={open}
                    aria-label={`${open ? "Hide" : "Show"} build output`}
                    onClick={() => setOpen(!open)}
                    className={TOGGLE}
                />
                <ShieldCheck
                    size={15}
                    strokeWidth={1.6}
                    aria-hidden="true"
                    className="pointer-events-none relative shrink-0 text-muted-foreground"
                />
                <span className="pointer-events-none relative shrink-0">
                    {checks.ok ? "Checked the build" : "The build check failed"}
                </span>
                <span className="pointer-events-none relative min-w-0 truncate text-muted-foreground">
                    {summary}
                </span>
                <RowChevron open={open} />
            </div>
            {open && (
                <ShellBlock
                    command=""
                    stdout={build.stdout ?? ""}
                    stderr={
                        (build.stderr ?? "") +
                        (migration?.ok === false ? (migration.output ?? "") : "")
                    }
                    exitCode={build.exit_code}
                    ok={checks.ok}
                    running={false}
                    shortened={false}
                    note={migrations && `Database: ${migrations}`}
                />
            )}
        </div>
    );
}

export function TimelineNote({ block }: { block: Extract<TimelineBlock, { kind: "note" }> }) {
    const { item } = block;
    if (item.compacted)
        return (
            <p className="m-0 flex min-h-8 items-center gap-2 text-[13.5px] text-muted-foreground">
                <ListCollapse size={15} strokeWidth={1.6} aria-hidden="true" />
                Context automatically compacted
            </p>
        );
    if (item.kind === "approach")
        return (
            <div className="py-1.5 text-[13.5px] text-muted-foreground">
                <p className="m-0 pb-1 wrap-anywhere">{item.message}</p>
                {item.steps?.map((step, index) => (
                    <p className="m-0 flex gap-3 py-0.5 wrap-anywhere" key={index}>
                        <span aria-hidden="true" className="tabular-nums">
                            {index + 1}
                        </span>
                        <span className="min-w-0">{step}</span>
                    </p>
                ))}
            </div>
        );
    const checks = item.checks as BuildChecks | undefined;
    if (item.kind === "verification" && checks?.build) return <BuildCheck checks={checks} />;
    if (item.kind === "verification")
        return (
            <p
                className={`m-0 flex min-h-8 min-w-0 items-center gap-2 text-[13.5px] ${item.ok === false ? "text-destructive" : "text-foreground/85"}`}
            >
                <ShieldCheck
                    size={15}
                    strokeWidth={1.6}
                    aria-hidden="true"
                    className="shrink-0 text-muted-foreground"
                />
                <span className="min-w-0 wrap-anywhere">{item.message || "Verification"}</span>
            </p>
        );
    return (
        <p className="m-0 py-1.5 text-[13.5px] text-muted-foreground wrap-anywhere">
            {item.message}
        </p>
    );
}
