"use client";

import type { EditedFile } from "@/lib/chat/tool-lines";
import { ChevronDown, FileDiff } from "lucide-react";
import { useContext, useState } from "react";

import { OpenFileContext } from "./OpenFileContext";
import { Counts } from "./ToolBlocks";

// Codex shows the first few changed files and folds the rest.
const SHOWN = 3;

/** The run's changed files in one card, as Codex closes a turn: totals first, then each file. */
export function EditedFiles({ files }: { files: EditedFile[] }) {
    const openFile = useContext(OpenFileContext);
    const [all, setAll] = useState(false);
    const counted = files.some((file) => file.counted);
    const added = files.reduce((sum, file) => sum + file.added, 0);
    const removed = files.reduce((sum, file) => sum + file.removed, 0);
    const hidden = files.length - SHOWN;
    const row = (file: EditedFile) => {
        const cut = file.path.lastIndexOf("/") + 1;
        return (
            <li key={file.path}>
                <button
                    type="button"
                    title={`Open ${file.path}`}
                    onClick={() => openFile(file.path)}
                    className="flex min-h-9 w-full cursor-pointer items-center gap-3 px-3 text-left text-[13px] [transition:background-color_130ms_ease] focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring pointer-fine:hover:bg-surface-3"
                >
                    <span className="min-w-0 flex-1 truncate">
                        <span className="text-muted-foreground">{file.path.slice(0, cut)}</span>
                        <span className="text-foreground">{file.path.slice(cut)}</span>
                    </span>
                    {file.counted && <Counts added={file.added} removed={file.removed} />}
                </button>
            </li>
        );
    };
    return (
        // Arrives when the build ends, the moment the user is waiting for, instead of popping in.
        <div className="mt-3 min-w-0 overflow-hidden rounded-[12px] border border-border bg-surface-2 [transition:opacity_200ms_var(--ease-out),translate_200ms_var(--ease-out)] starting:translate-y-1 starting:opacity-0 motion-reduce:starting:translate-y-0">
            <div className="flex items-center gap-3 border-b border-hairline px-3 py-2.5">
                <span className="grid size-9 shrink-0 place-items-center rounded-[8px] bg-surface-3 text-muted-foreground">
                    <FileDiff size={16} strokeWidth={1.6} aria-hidden="true" />
                </span>
                <div className="min-w-0 leading-tight">
                    <p className="m-0 text-[13.5px] text-foreground">
                        Edited {files.length} {files.length === 1 ? "file" : "files"}
                    </p>
                    {counted && <Counts added={added} removed={removed} />}
                </div>
            </div>
            <ul className="m-0 list-none p-0">{files.slice(0, SHOWN).map(row)}</ul>
            {hidden > 0 && (
                <>
                    {/* The repo's expand pattern (globals.css [data-disclosure]): height and fade. */}
                    <div data-disclosure={all ? "open" : ""}>
                        <ul className="m-0 list-none p-0">{files.slice(SHOWN).map(row)}</ul>
                    </div>
                    <button
                        type="button"
                        aria-expanded={all}
                        onClick={() => setAll(!all)}
                        className="flex min-h-9 w-full cursor-pointer items-center gap-1.5 border-t border-hairline px-3 text-left text-[13px] text-muted-foreground [transition:color_130ms_ease] focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring pointer-fine:hover:text-foreground"
                    >
                        {all
                            ? "Show fewer files"
                            : `Show ${hidden} more ${hidden === 1 ? "file" : "files"}`}
                        <ChevronDown
                            size={14}
                            aria-hidden="true"
                            className={`[transition:transform_180ms_var(--ease-out)] motion-reduce:[transition:none] ${all ? "rotate-180" : ""}`}
                        />
                    </button>
                </>
            )}
        </div>
    );
}
