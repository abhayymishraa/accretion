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
import { projectName } from "@/lib/projects/filters";
import { ChevronDown, CircleDashed, FolderArchive, Pencil } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import { toast } from "sonner";

// The heading, the rename field and its sizer share one box, so editing never moves the text.
const TITLE_TEXT = "rounded-[7px] px-2 py-1 text-[13.5px] leading-5 font-medium text-foreground";
// The AI's name fades in and settles 2px once, when it replaces "New project" (plans/001).
export const NAME_ARRIVES =
    "starting:translate-y-0.5 starting:opacity-0 motion-reduce:starting:translate-y-0";
const STATUS = { idle: "", saving: "Saving…", saved: "Saved", error: "Couldn't save the name" };

/** The project name atop the conversation: double-click to rename, ⌄ to switch projects. */
export function ProjectTitle({
    projectId,
    revisionId,
}: {
    projectId: string;
    revisionId?: string | null;
}) {
    const { title, arriving, settleArrival, projects, status, save, saveSoon } =
        useProjectTitle(projectId);
    // The words stay while the status fades out, so nothing blinks and aria-live hears no change.
    const [message, setMessage] = useState("");
    if (STATUS[status] && STATUS[status] !== message) setMessage(STATUS[status]);
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
                // Sized by a hidden copy of the text in the same grid cell, so the field is exactly
                // as wide as the name (field-sizing lacks Firefox).
                <div className="inline-grid min-w-0 max-w-full [&>*]:[grid-area:1/1]">
                    <span
                        aria-hidden="true"
                        className={`${TITLE_TEXT} invisible overflow-hidden whitespace-pre pointer-coarse:text-[16px]`}
                    >
                        {draft || " "}
                    </span>
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
                        // The title's own type, no box or ring of its own;
                        // the tinted field and the selection show it is being edited.
                        className={`${TITLE_TEXT} w-full min-w-0 border-0 bg-surface-2 outline-none focus-visible:outline-none pointer-coarse:text-[16px]`}
                    />
                </div>
            ) : title === null ? (
                <span
                    aria-hidden="true"
                    className="h-3 w-32 animate-pulse rounded-full bg-surface-2 motion-reduce:animate-none"
                />
            ) : (
                <h1
                    key={arriving ? "arrived" : "steady"}
                    onTransitionEnd={settleArrival}
                    onDoubleClick={startEditing}
                    title="Double-click to rename"
                    className={`${TITLE_TEXT} m-0 min-w-0 cursor-text truncate ${arriving ? NAME_ARRIVES : ""} [transition:background-color_130ms_ease,opacity_200ms_var(--ease-out),translate_200ms_var(--ease-out)] pointer-fine:hover:bg-surface-2`}
                >
                    {title}
                </h1>
            )}
            <DropdownMenu>
                <DropdownMenuTrigger
                    aria-label="Project menu"
                    className="grid size-7 shrink-0 cursor-pointer place-items-center rounded-[7px] pointer-coarse:size-11 text-muted-foreground [transition:background-color_130ms_ease,color_130ms_ease] focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:bg-surface-2 pointer-fine:hover:text-foreground"
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
                                            {projectName(project)}
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
                className={`shrink-0 text-[11.5px] [transition:opacity_200ms_var(--ease-out)] ${status === "idle" ? "opacity-0" : "opacity-100 [transition-duration:0ms]"} ${status === "error" ? "text-destructive" : "text-muted-foreground"}`}
            >
                {message}
            </span>
        </div>
    );
}
