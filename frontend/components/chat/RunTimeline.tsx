"use client";

import {
    BookOpen,
    ChevronRight,
    FilePlus2,
    Folder,
    ListCollapse,
    Pencil,
    Puzzle,
    Search,
    ShieldCheck,
    SquareTerminal,
    type LucideIcon,
} from "lucide-react";
import { ThinkingOrb } from "thinking-orbs";
import { memo, useState } from "react";

import {
    sectionTitle,
    type LineKind,
    type TimelineBlock,
    type ToolLine,
} from "@/lib/chat/tool-lines";
import { presentTool } from "@/lib/tool-presentation";
import { RunScreenshots } from "./RunScreenshots";
import { Counts, DiffCard, FileLink, ShellBlock } from "./ToolBlocks";
import { RecordedResult, ToolResult } from "./ToolResult";

const ICONS: Record<LineKind, LucideIcon> = {
    read: BookOpen,
    edit: Pencil,
    create: FilePlus2,
    run: SquareTerminal,
    search: Search,
    list: Folder,
    guide: BookOpen,
    other: Puzzle,
};

const VERBS: Record<LineKind, [string, string]> = {
    // [done, in flight]
    read: ["Read", "Reading"],
    edit: ["Edited", "Editing"],
    create: ["Created", "Creating"],
    run: ["Ran", "Running"],
    search: ["Searched", "Searching"],
    list: ["Listed files", "Listing files"],
    guide: ["Read guidance", "Reading guidance"],
    other: ["Used", "Using"],
};

const ROW =
    "group relative flex min-h-8 min-w-0 items-center gap-2 rounded-[6px] px-1 text-[13.5px] text-foreground/85 data-[failed=true]:text-destructive";

// Rows with a body open on click anywhere; the file link inside stays its own target.
const TOGGLE =
    "absolute inset-0 cursor-pointer rounded-[6px] focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:bg-surface-2";

const TimelineRow = memo(function TimelineRow({ line }: { line: ToolLine }) {
    const { tool } = line;
    const result = presentTool(tool);
    const running = tool.status === "running";
    const failed = tool.status === "error";
    // Opens on its own when it failed or the page reported problems.
    const [open, setOpen] = useState(failed || result.pageProblems.length > 0);
    const Glyph = ICONS[line.kind];
    const expandable =
        line.kind === "run" ||
        (!running && (line.kind === "other" || failed || Boolean(line.diff?.hunks.length)));
    const [done, going] = VERBS[line.kind];
    return (
        <div className="min-w-0">
            <div className={ROW} data-failed={failed}>
                {expandable && (
                    <button
                        type="button"
                        aria-expanded={open}
                        aria-label={`${open ? "Hide" : "Show"} details: ${done} ${line.text}`}
                        onClick={() => setOpen(!open)}
                        className={TOGGLE}
                    />
                )}
                <span className="pointer-events-none relative flex size-4 shrink-0 items-center justify-center text-muted-foreground">
                    {running ? (
                        <ThinkingOrb state="working" size={20} aria-hidden="true" />
                    ) : (
                        <Glyph size={15} strokeWidth={1.6} aria-hidden="true" />
                    )}
                </span>
                <span
                    className={`pointer-events-none relative shrink-0 ${running ? "motion-safe:animate-pulse" : ""}`}
                >
                    {running ? going : done}
                </span>
                {line.path ? (
                    <FileLink path={line.path} />
                ) : (
                    line.text && (
                        <span
                            className="pointer-events-none relative min-w-0 truncate text-muted-foreground"
                            title={line.text}
                        >
                            {line.text}
                        </span>
                    )
                )}
                {line.diff && <Counts added={line.diff.added} removed={line.diff.removed} />}
                {expandable && (
                    <ChevronRight
                        size={14}
                        aria-hidden="true"
                        className={`pointer-events-none relative shrink-0 text-muted-foreground [transition:transform_180ms_var(--ease-out),opacity_130ms_ease] motion-reduce:[transition:none] ${
                            open
                                ? "rotate-90"
                                : "opacity-0 group-focus-within:opacity-100 pointer-fine:group-hover:opacity-100"
                        }`}
                    />
                )}
            </div>
            {open && expandable && (
                <div className="pl-7">
                    {line.diff?.hunks.length ? (
                        <DiffCard diff={line.diff} />
                    ) : line.kind === "run" || (result.command && failed) ? (
                        <ShellBlock
                            command={result.command || "Command not recorded"}
                            stdout={result.stdout}
                            stderr={result.stderr || (failed ? result.error : "")}
                            exitCode={result.exitCode}
                            ok={!failed && (result.exitCode ?? 0) === 0}
                            running={running}
                            shortened={result.truncatedFields.some((field) =>
                                field.startsWith("std"),
                            )}
                            pageSummary={result.pageSummary}
                            pageProblems={result.pageProblems}
                            note={result.browserRestarted}
                        />
                    ) : (
                        <div className="border-l border-hairline pb-2 pl-3">
                            <ToolResult tool={tool} result={result} />
                        </div>
                    )}
                </div>
            )}
        </div>
    );
});

/**
 * A run of tool rows under one header. The header sticks to the top of the conversation while its
 * rows scroll beneath it, as Codex does, so a long section never loses its label.
 */
function TimelineSection({ lines, live }: { lines: ToolLine[]; live: boolean }) {
    const [choice, setChoice] = useState<boolean | null>(null);
    const open = choice ?? live;
    if (lines.length === 1) return <TimelineRow line={lines[0]} />;
    const Glyph = ICONS[lines[0].kind];
    // Sticky insets are measured inside the conversation's padding (py-8, py-5 on phones), so the
    // header climbs back over it; otherwise rows would show through above it.
    return (
        <section className="min-w-0">
            <button
                type="button"
                aria-expanded={open}
                onClick={() => setChoice(!open)}
                className="group sticky -top-8 z-[2] max-md:-top-5 flex min-h-8 w-full cursor-pointer items-center gap-2 bg-surface-1 px-1 text-left text-[13.5px] text-muted-foreground [transition:color_130ms_ease] focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:text-foreground"
            >
                <Glyph size={15} strokeWidth={1.6} aria-hidden="true" className="shrink-0" />
                <span className="min-w-0 truncate">{sectionTitle(lines)}</span>
                <ChevronRight
                    size={14}
                    aria-hidden="true"
                    className={`shrink-0 [transition:transform_180ms_var(--ease-out)] motion-reduce:[transition:none] ${open ? "rotate-90" : ""}`}
                />
            </button>
            {open && (
                <div className="grid min-w-0 animate-in fade-in duration-150 ease-out motion-reduce:animate-none">
                    {lines.map((line) => (
                        <TimelineRow key={line.key} line={line} />
                    ))}
                </div>
            )}
        </section>
    );
}

function TimelineNote({ block }: { block: Extract<TimelineBlock, { kind: "note" }> }) {
    const { item } = block;
    if (item.compacted)
        return (
            <p className="m-0 flex min-h-8 items-center gap-2 px-1 text-[13.5px] text-muted-foreground">
                <ListCollapse size={15} strokeWidth={1.6} aria-hidden="true" />
                Context automatically compacted
            </p>
        );
    if (item.kind === "verification")
        return (
            <div className="min-w-0 px-1">
                <p
                    className={`m-0 flex min-h-8 items-center gap-2 text-[13.5px] ${item.ok === false ? "text-destructive" : "text-foreground/85"}`}
                >
                    <ShieldCheck
                        size={15}
                        strokeWidth={1.6}
                        aria-hidden="true"
                        className="shrink-0 text-muted-foreground"
                    />
                    <span className="min-w-0 wrap-anywhere">{item.message || "Verification"}</span>
                </p>
                {item.checks !== undefined && (
                    <div className="pl-6">
                        <RecordedResult
                            label="Check results"
                            output={JSON.stringify(item.checks, null, 2)}
                        />
                    </div>
                )}
            </div>
        );
    return (
        <p className="m-0 px-1 py-1.5 text-[13.5px] text-muted-foreground wrap-anywhere">
            {item.message}
        </p>
    );
}

export function RunTimeline({ blocks, running }: { blocks: TimelineBlock[]; running: boolean }) {
    return (
        <div className="grid min-w-0 gap-0.5">
            {blocks.map((block, index) =>
                block.kind === "section" ? (
                    <TimelineSection
                        key={block.key}
                        lines={block.lines}
                        // The section being written stays open while the run is live.
                        live={running && index === blocks.length - 1}
                    />
                ) : block.kind === "screenshots" ? (
                    <RunScreenshots key={block.key} runId={block.runId} ids={block.ids} />
                ) : (
                    <TimelineNote key={block.key} block={block} />
                ),
            )}
        </div>
    );
}
