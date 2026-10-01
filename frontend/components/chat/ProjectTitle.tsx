"use client";

import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useProjectDownload } from "@/hooks/files/useProjectDownload";
import { useProjectTitle } from "@/hooks/projects/useProjectTitle";
import { ChevronDown, CircleDashed, FolderArchive, Pencil } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import { toast } from "sonner";

const STATUS = { idle: "", saving: "Saving…", saved: "Saved", error: "Couldn't save the name" };

/** The project name atop the conversation: double-click to rename, ⌄ to switch projects. */
export function ProjectTitle({
    projectId,
    revisionId,
}: {
    projectId: string;
    revisionId?: string | null;
}) {
    const { title, projects, status, save, saveSoon } = useProjectTitle(projectId);
    const { isDownloading, handleDownloadAll } = useProjectDownload(projectId, revisionId);
    const [draft, setDraft] = useState<string | null>(null);
    // The name when editing began, so Esc can undo a save the pause already made.
    const original = useRef("");
    // Esc and Enter unmount the field, which can also fire blur; only the first ending counts.
    const editing = useRef(false);
    const startEditing = () => {
        if (title === null) return;
        original.current = title;
        editing.current = true;
        setDraft(title);
    };
    const finish = (keep: boolean) => {
        if (!editing.current || draft === null) return;
        editing.current = false;
        setDraft(null);
        void save(keep ? draft : original.current);
    };
    const others = (projects ?? []).filter((project) => project.id !== projectId).slice(0, 6);

    return (
        <div className="flex min-w-0 items-center gap-1">
            {draft !== null ? (
                <input
                    autoFocus
                    aria-label="Project name"
                    value={draft}
                    maxLength={255}
                    onFocus={(event) => event.currentTarget.select()}
                    onChange={(event) => {
                        setDraft(event.target.value);
                        saveSoon(event.target.value);
                    }}
                    onKeyDown={(event) => {
                        if (event.key === "Enter") finish(true);
                        if (event.key === "Escape") finish(false);
                    }}
                    onBlur={() => finish(true)}
                    className="h-7 w-[min(26ch,100%)] min-w-0 rounded-[7px] border border-ring bg-surface-2 px-2 text-[13.5px] font-medium text-foreground outline-none"
                />
            ) : title === null ? (
                <span
                    aria-hidden="true"
                    className="h-3 w-32 animate-pulse rounded-full bg-surface-2 motion-reduce:animate-none"
                />
            ) : (
                <h1
                    onDoubleClick={startEditing}
                    title="Double-click to rename"
                    className="m-0 min-w-0 cursor-text truncate rounded-[7px] px-2 py-1 text-[13.5px] font-medium text-foreground [transition:background-color_130ms_ease] pointer-fine:hover:bg-surface-2"
                >
                    {title || "Untitled project"}
                </h1>
            )}
            <DropdownMenu>
                <DropdownMenuTrigger
                    aria-label="Project menu"
                    className="grid size-7 shrink-0 cursor-pointer place-items-center rounded-[7px] text-muted-foreground [transition:background-color_130ms_ease,color_130ms_ease] focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:bg-surface-2 pointer-fine:hover:text-foreground"
                >
                    <ChevronDown size={15} />
                </DropdownMenuTrigger>
                {/* Focus stays where the chosen item sends it: the rename field, not this button. */}
                <DropdownMenuContent
                    align="start"
                    className="w-60"
                    onCloseAutoFocus={(event) => event.preventDefault()}
                >
                    {others.length > 0 && (
                        <>
                            <DropdownMenuLabel className="text-[11px] font-normal text-muted-foreground">
                                Switch project
                            </DropdownMenuLabel>
                            {others.map((project) => (
                                <DropdownMenuItem key={project.id} asChild>
                                    <Link href={`/chat/${project.id}`}>
                                        <span className="min-w-0 flex-1 truncate">
                                            {project.title || "Untitled project"}
                                        </span>
                                        {!project.latest_saved_revision_id && (
                                            <CircleDashed aria-label="Draft" />
                                        )}
                                    </Link>
                                </DropdownMenuItem>
                            ))}
                            <DropdownMenuSeparator />
                        </>
                    )}
                    <DropdownMenuItem onSelect={startEditing}>
                        <Pencil />
                        Rename
                    </DropdownMenuItem>
                    <DropdownMenuItem
                        disabled={isDownloading || !revisionId}
                        onSelect={() =>
                            handleDownloadAll().then(
                                (ok) => ok || toast.error("Could not download the project ZIP"),
                            )
                        }
                    >
                        <FolderArchive />
                        Download ZIP
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
            <span
                aria-live="polite"
                className={`shrink-0 text-[11.5px] ${status === "error" ? "text-destructive" : "text-muted-foreground"}`}
            >
                {STATUS[status]}
            </span>
        </div>
    );
}
