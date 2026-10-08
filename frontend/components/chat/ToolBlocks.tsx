"use client";

import { CheckIcon, CopyIcon, Cross2Icon } from "@radix-ui/react-icons";
import { ChevronRight } from "lucide-react";
import { useContext, useState } from "react";

import { IconSwap } from "@/components/ui/IconSwap";
import { basename, type FileDiff } from "@/lib/chat/tool-lines";
import { OpenFileContext } from "./OpenFileContext";

/** A file name that opens the file in the Files panel; the dotted underline marks it as a link. */
export function FileLink({ path }: { path: string }) {
    const openFile = useContext(OpenFileContext);
    return (
        <button
            type="button"
            title={path}
            onClick={() => openFile(path)}
            className="relative z-[1] min-w-0 cursor-pointer truncate text-left text-muted-foreground underline decoration-dotted decoration-1 underline-offset-[3px] [transition:color_130ms_ease] focus-visible:rounded-[3px] focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:text-foreground"
        >
            {basename(path)}
        </button>
    );
}

export function Counts({ added, removed }: { added: number; removed: number }) {
    // Positioned, so it paints above a timeline row's hover layer; clicks pass through to the row.
    return (
        <span className="pointer-events-none relative shrink-0 font-mono text-[12px] tabular-nums">
            <span className="text-emerald-500">+{added}</span>{" "}
            <span className="text-red-400">-{removed}</span>
        </span>
    );
}

function CopyButton({ text, label }: { text: string; label: string }) {
    const [copied, setCopied] = useState(false);
    return (
        <button
            type="button"
            aria-label={label}
            onClick={async () => {
                try {
                    await navigator.clipboard.writeText(text);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 1400);
                } catch {
                    /* The text stays selectable in the block. */
                }
            }}
            className="ml-auto grid size-7 shrink-0 pointer-coarse:size-11 cursor-pointer place-items-center rounded-[6px] text-muted-foreground [transition:color_130ms_ease,background-color_130ms_ease] focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:bg-surface-3 pointer-fine:hover:text-foreground"
        >
            <IconSwap swapped={copied} from={<CopyIcon />} to={<CheckIcon />} />
        </button>
    );
}

// Fixed height with its own scroll, so opening one does not push the conversation around.
const FRAME =
    "mt-1 mb-2 min-w-0 overflow-hidden rounded-[10px] border border-border bg-surface-2 animate-in fade-in duration-150 ease-out motion-reduce:animate-none";

export function DiffCard({ diff }: { diff: FileDiff }) {
    const unified = diff.hunks
        .map((hunk) => hunk.map(([sign, , text]) => `${sign}${text}`).join("\n"))
        .join("\n...\n");
    return (
        <div className={FRAME}>
            <div className="flex min-h-10 items-center gap-2 border-b border-hairline px-3 text-[12.5px]">
                <FileLink path={diff.path} />
                <Counts added={diff.added} removed={diff.removed} />
                <CopyButton text={unified} label="Copy diff" />
            </div>
            <div
                tabIndex={0}
                aria-label={`Changes to ${diff.path}`}
                className="relative max-h-68 overflow-auto font-mono text-[12px] leading-[1.7] focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring"
            >
                {diff.hunks.map((hunk, index) => (
                    <div key={index} className="min-w-max [&+&]:border-t-4 [&+&]:border-surface-3">
                        {hunk.map(([sign, number, text], row) => (
                            <div
                                key={row}
                                data-diff={
                                    sign === "+" ? "add" : sign === "-" ? "remove" : undefined
                                }
                                className="grid grid-cols-[3px_3.5rem_1fr] data-[diff=add]:bg-emerald-500/12 data-[diff=remove]:bg-red-500/12 [&[data-diff=add]>i]:bg-emerald-500 [&[data-diff=remove]>i]:bg-red-400"
                            >
                                <i aria-hidden="true" />
                                <span className="pr-3 text-right text-muted-foreground tabular-nums select-none">
                                    {number}
                                </span>
                                <span className="pr-6 whitespace-pre">
                                    <span className="sr-only">
                                        {sign === "+" ? "added " : sign === "-" ? "removed " : ""}
                                    </span>
                                    {text}
                                </span>
                            </div>
                        ))}
                    </div>
                ))}
            </div>
            {diff.truncated && (
                <p className="border-t border-hairline px-3 py-1.5 text-[11.5px] text-muted-foreground">
                    Diff shortened. Open the file to see all of it.
                </p>
            )}
        </div>
    );
}

export function ShellBlock({
    command,
    stdout,
    stderr,
    exitCode,
    ok,
    running,
    shortened,
    pageSummary = "",
    pageProblems = [],
    note = "",
}: {
    command: string;
    stdout: string;
    stderr: string;
    exitCode?: number;
    ok: boolean;
    running: boolean;
    shortened: boolean;
    pageSummary?: string;
    pageProblems?: string[];
    note?: string;
}) {
    // agent-browser fences page text with nonce markers for the model; the user needs only the text.
    const shown = stdout
        .replace(/^--- (?:END_)?AGENT_BROWSER_PAGE_CONTENT .*---\n?/gm, "")
        .replace(/^\n+/, "");
    return (
        <div className={FRAME}>
            <div className="flex min-h-9 items-center px-3 text-[12px] text-muted-foreground">
                Shell
                {command && <CopyButton text={command} label="Copy command" />}
            </div>
            <div
                tabIndex={0}
                aria-label="Command and output"
                className="max-h-72 overflow-auto px-3 pb-2 font-mono text-[12px] leading-[1.65] focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring"
            >
                {command && (
                    <p className="m-0 whitespace-pre-wrap break-all text-foreground">
                        <span className="text-muted-foreground select-none">$ </span>
                        {command}
                    </p>
                )}
                {shown && <pre className="m-0 mt-2 text-muted-foreground">{shown}</pre>}
                {stderr && <pre className="m-0 mt-2 text-destructive">{stderr}</pre>}
                {shortened && (
                    <p className="m-0 mt-2 text-[11px] text-muted-foreground">Output shortened.</p>
                )}
            </div>
            {(pageSummary || note) && (
                <div
                    className="border-t border-hairline px-3 py-1.5 font-mono text-[11.5px] leading-[1.6] data-[problems=true]:text-destructive"
                    data-problems={pageProblems.length > 0}
                >
                    {note && <p className="m-0 text-muted-foreground">{note}</p>}
                    {pageSummary && <p className="m-0">Page: {pageSummary}</p>}
                    {pageProblems.map((problem, index) => (
                        <p key={index} className="m-0 whitespace-pre-wrap break-all">
                            {problem}
                        </p>
                    ))}
                </div>
            )}
            {!running && (
                <div className="flex items-center justify-end gap-1.5 border-t border-hairline px-3 py-1.5 text-[12px] text-muted-foreground">
                    {ok ? <CheckIcon aria-hidden="true" /> : <Cross2Icon aria-hidden="true" />}
                    {ok ? "Success" : exitCode !== undefined ? `Exit code ${exitCode}` : "Failed"}
                </div>
            )}
        </div>
    );
}

// Shared by the timeline's rows (RunTimeline, TimelineNotes). Every icon, card and image lines
// up on one left edge: a row's content starts there and its hover background reaches 4px past it.
export const ROW =
    "group relative -mx-1 flex min-h-8 pointer-coarse:min-h-11 min-w-0 items-center gap-2 rounded-[6px] px-1 text-[13.5px] text-foreground/85 data-[failed=true]:text-destructive";

// Rows with a body open on click anywhere; the file link inside stays its own target.
export const TOGGLE =
    "absolute inset-0 cursor-pointer rounded-[6px] focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:bg-surface-2 pointer-coarse:active:bg-surface-2";

/** Turns down when the row is open; otherwise shown on hover or focus, and always on touch, which has no hover. */
export function RowChevron({ open }: { open: boolean }) {
    return (
        <ChevronRight
            size={14}
            aria-hidden="true"
            className={`pointer-events-none relative shrink-0 text-muted-foreground [transition:transform_180ms_var(--ease-out),opacity_130ms_ease] motion-reduce:[transition:none] ${
                open
                    ? "rotate-90"
                    : "opacity-0 group-focus-within:opacity-100 pointer-fine:group-hover:opacity-100 pointer-coarse:opacity-100"
            }`}
        />
    );
}
