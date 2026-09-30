"use client";

import type { TouchedFile } from "@/lib/tool-presentation";
import { useContext } from "react";

import { OpenFileContext } from "./OpenFileContext";

/** Every file the run touched; each one opens in the Files panel. */
export function FileChips({ files }: { files: TouchedFile[] }) {
    const openFile = useContext(OpenFileContext);
    const edited = files.filter((file) => file.changed).length;
    return (
        <div className="mt-3 min-w-0 rounded-[10px] border border-border bg-surface-2 px-3 py-2.5">
            <p className="m-0 pb-2 text-[12.5px] text-muted-foreground">
                {edited
                    ? `Edited ${edited} ${edited === 1 ? "file" : "files"}`
                    : `Read ${files.length} ${files.length === 1 ? "file" : "files"}`}
            </p>
            <div className="flex max-w-full flex-wrap gap-1.5">
                {files.map((file) => (
                    <button
                        type="button"
                        key={file.path}
                        title={`Open ${file.path}`}
                        onClick={() => openFile(file.path)}
                        className="inline-flex h-7 max-w-full cursor-pointer items-center gap-2 rounded-[6px] bg-surface-3 px-2 font-mono text-[11.5px] text-foreground [transition:background-color_130ms_ease] focus-visible:outline-2 focus-visible:outline-ring active:scale-[0.98] pointer-fine:hover:bg-surface-1"
                    >
                        <span className="min-w-0 truncate">{file.path}</span>
                        <span
                            className={`shrink-0 ${file.changed ? "text-accent-foreground" : "text-muted-foreground"}`}
                        >
                            {file.changed ? "edited" : "read"}
                        </span>
                    </button>
                ))}
            </div>
        </div>
    );
}
