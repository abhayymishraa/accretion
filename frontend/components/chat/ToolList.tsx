"use client";

// Interaction patterns adapted from Beautiful UI, MIT © 2026 Shane Levine.
// See ../ember/BEAUTIFUL-UI-LICENSE. All progress comes from recorded run events.
import { presentTool, toolLabel, type TouchedFile } from "@/lib/tool-presentation";
import type { ToolCall } from "@/types/chat.type";
import {
    ChevronRightIcon,
    ClockIcon,
    CodeIcon,
    Cross2Icon,
    CubeIcon,
    FileTextIcon,
    MagnifyingGlassIcon,
    Pencil1Icon,
} from "@radix-ui/react-icons";
import { memo, useId, useState } from "react";
import { createPortal } from "react-dom";
import styles from "./transcript.module.css";

import { PixelLoader } from "./RunStatus";
import { ToolResult } from "./ToolResult";

const icons: Record<string, typeof CubeIcon> = {
    write_files: Pencil1Icon,
    read_files: FileTextIcon,
    list_files: FileTextIcon,
    run_command: CodeIcon,
    read_skill: MagnifyingGlassIcon,
};
export const ToolRow = memo(function ToolRow({ tool }: { tool: ToolCall }) {
    const result = presentTool(tool);
    // Errors open by default. A user's explicit expand/collapse choice takes precedence.
    const [choice, setChoice] = useState<boolean | null>(null);
    const expanded = choice ?? tool.status === "error";
    const Glyph = icons[tool.name] || CubeIcon;
    // One chip per row: the command, else the first path, else the plain summary.
    const chip = result.command || result.files[0] || result.summary;
    const mono = Boolean(result.command || result.files[0]);
    return (
        <details
            className={
                styles.tool +
                " transcript-tool min-w-0 [&>summary]:list-none [&>summary]:flex [&>summary]:min-h-9 [&>summary]:cursor-pointer [&>summary]:items-center [&>summary]:gap-2 [&>summary]:rounded-md [&>summary]:px-1 [&>summary]:text-[12.5px] [&>summary::-webkit-details-marker]:hidden [&[open]>summary>.transcript-chevron]:rotate-90 [&>summary:hover]:bg-secondary [&[data-state=error]>summary]:text-destructive [&[data-state=error]_.transcript-toolSummary]:text-destructive"
            }
            data-state={tool.status}
            open={expanded}
            onToggle={(event) => {
                if (event.currentTarget.open !== expanded) setChoice(event.currentTarget.open);
            }}
        >
            <summary>
                <span className="group/glyph relative flex size-4 shrink-0 items-center justify-center text-muted-foreground">
                    {tool.status === "running" ? (
                        <PixelLoader />
                    ) : tool.status === "error" ? (
                        <Cross2Icon aria-hidden="true" />
                    ) : result.interrupted ? (
                        <ClockIcon aria-hidden="true" />
                    ) : (
                        <Glyph aria-hidden="true" />
                    )}
                </span>
                <span
                    className={`${styles.toolName} transcript-toolName shrink-0 font-medium text-foreground`}
                >
                    {result.title}
                </span>
                <span
                    className={`transcript-toolSummary mr-auto min-w-0 truncate rounded-md bg-secondary px-1.5 py-0.5 text-[11.5px] text-muted-foreground ${mono ? "font-mono" : ""}`}
                    title={chip}
                >
                    {chip}
                </span>
                {result.fileCount > 1 && (
                    <span className="shrink-0 font-mono text-[11px] text-muted-foreground tabular-nums">
                        +{result.fileCount - 1}
                    </span>
                )}
                {typeof tool.duration_ms === "number" && (
                    <span className="shrink-0 font-mono text-[11px] text-muted-foreground tabular-nums">
                        {(tool.duration_ms / 1000).toFixed(1)}s
                    </span>
                )}
                <ChevronRightIcon
                    className="transcript-chevron w-[13px] shrink-0 text-muted-foreground [transition:transform_.18s_var(--ease-out)] motion-reduce:[transition:none]"
                    aria-hidden="true"
                />
                <span className="sr-only">
                    {tool.status === "success"
                        ? "Completed"
                        : result.interrupted
                          ? "Stopped"
                          : tool.status === "error"
                            ? "Failed"
                            : "Running"}
                </span>
            </summary>
            {expanded && (
                <div className="transcript-result min-w-0 px-1 pt-0.5 pb-2">
                    <div className="border-l border-border pl-3">
                        <ToolResult tool={tool} result={result} />
                    </div>
                </div>
            )}
        </details>
    );
});

/** A burst of the same successful tool, collapsed to one row with its calls inside. */
export function ToolGroup({ name, calls }: { name: string; calls: ToolCall[] }) {
    const Glyph = icons[name] || CubeIcon;
    return (
        <details className="min-w-0 [&>summary]:flex [&>summary]:min-h-9 [&>summary]:cursor-pointer [&>summary]:items-center [&>summary]:gap-2 [&>summary]:rounded-md [&>summary]:px-1 [&>summary]:text-[12.5px] [&>summary]:list-none [&>summary::-webkit-details-marker]:hidden [&[open]>summary>.transcript-chevron]:rotate-90 [&>summary:hover]:bg-secondary">
            <summary>
                <span className="flex size-4 shrink-0 items-center justify-center text-muted-foreground">
                    <Glyph aria-hidden="true" />
                </span>
                <span className="shrink-0 font-medium text-foreground">{toolLabel(name)}</span>
                <span className="mr-auto rounded-md bg-secondary px-1.5 py-0.5 font-mono text-[11.5px] text-muted-foreground tabular-nums">
                    {calls.length} calls
                </span>
                <ChevronRightIcon
                    className="transcript-chevron w-[13px] shrink-0 text-muted-foreground [transition:transform_.18s_var(--ease-out)] motion-reduce:[transition:none]"
                    aria-hidden="true"
                />
            </summary>
            <div className="ml-2 grid gap-1 border-l border-border pl-3">
                {calls.map((tool, index) => (
                    <ToolRow key={tool.id || index} tool={tool} />
                ))}
            </div>
        </details>
    );
}

// Header row plus three body lines; enough to decide whether the preview fits below.
const PREVIEW_HEIGHT = 102;

type Anchor = { file: TouchedFile; x: number; top?: number; bottom?: number };

export function FileChips({ files }: { files: TouchedFile[] }) {
    const previewId = useId();
    // Portalled: the run trace animates its height, and an absolute child would be clipped.
    const [anchor, setAnchor] = useState<Anchor | null>(null);
    const openAt = (file: TouchedFile) => (event: React.SyntheticEvent) => {
        const rect = (event.currentTarget as Element).getBoundingClientRect();
        const fitsBelow = rect.bottom + PREVIEW_HEIGHT <= window.innerHeight - 12;
        setAnchor({
            file,
            x: Math.max(12, Math.min(rect.left, window.innerWidth - 300)),
            ...(fitsBelow
                ? { top: rect.bottom + 6 }
                : { bottom: window.innerHeight - rect.top + 6 }),
        });
    };
    // touchedFiles rebuilds its objects each render, so identity is not stable: match on path.
    const close = (file: TouchedFile) => () =>
        setAnchor((current) => (current?.file.path === file.path ? null : current));
    return (
        <div className="mt-2.5 flex max-w-full flex-wrap gap-1.5 border-t border-border pt-2.5">
            {files.map((file) => (
                <button
                    type="button"
                    key={file.path}
                    aria-describedby={anchor?.file.path === file.path ? previewId : undefined}
                    onMouseEnter={openAt(file)}
                    onMouseLeave={close(file)}
                    onFocus={openAt(file)}
                    onBlur={close(file)}
                    className="inline-flex h-7 max-w-full cursor-pointer items-center gap-2 rounded-md bg-card px-2 font-mono text-[11.5px] text-foreground focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:bg-secondary"
                >
                    <span className="min-w-0 truncate">{file.path}</span>
                    <span
                        className={`shrink-0 ${file.changed ? "text-accent-foreground" : "text-muted-foreground"}`}
                    >
                        {file.changed ? "edited" : "read"}
                    </span>
                </button>
            ))}
            {anchor &&
                createPortal(
                    <div
                        id={previewId}
                        role="tooltip"
                        className="fixed z-50 w-72 animate-in overflow-hidden rounded-lg border border-border bg-card zoom-in-95 fade-in duration-150 ease-out motion-reduce:animate-none"
                        style={{ left: anchor.x, top: anchor.top, bottom: anchor.bottom }}
                    >
                        <div className="flex items-center justify-between border-b border-border px-2.5 py-1.5 font-mono text-[11px] text-muted-foreground">
                            <span className="min-w-0 truncate">{anchor.file.path}</span>
                            <span className="shrink-0 tabular-nums">
                                {((anchor.file.durationMs ?? 0) / 1000).toFixed(1)}s
                            </span>
                        </div>
                        <div className="flex flex-col gap-0.5 px-2.5 py-1.5 font-mono text-[11px] leading-[1.7] text-muted-foreground">
                            <span className="text-foreground">{anchor.file.title}</span>
                            <span>{anchor.file.summary}</span>
                            <span className="text-[10.5px]">
                                Run history records no file contents.
                            </span>
                        </div>
                    </div>,
                    document.body,
                )}
        </div>
    );
}
