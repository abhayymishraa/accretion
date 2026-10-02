"use client";

// Timeline shape follows Codex: a finished run folds to "Worked for 8m", and opens to the
// sections of tool rows it ran. All progress comes from recorded run events.
import type { Message } from "@/types/chat.type";
import { ChevronRight } from "lucide-react";
import { ThinkingOrb } from "thinking-orbs";
import { useMemo, useState, type ReactNode } from "react";

import { Elapsed } from "./RunStatus";
import { RelativeTime, RunMenu } from "./RunMenu";
import { EditedFiles } from "./ToolList";
import { RunTimeline } from "./RunTimeline";
import { useRunDetails } from "@/hooks/chat/useRunDetails";
import { isOpenRun } from "@/lib/chat/messages";
import { timelineEntries } from "@/lib/chat/run-timeline";
import { editedFiles, timelineBlocks, workedFor } from "@/lib/chat/tool-lines";
import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";

const QUIET = [
    "queued",
    "running",
    "succeeded",
    "cancelled",
    "stopped",
    "awaiting_input",
    "answered",
];

/** `children` is the reply: it sits between the trace and the edited-files card, as Codex lays out a turn. */
export function RunActivity({
    message,
    connected,
    children,
}: {
    message: Message;
    connected: boolean;
    children?: ReactNode;
}) {
    const running = isOpenRun(message.run_status);
    const [expanded, setExpanded] = useState(false);
    // Opening the menu loads the steps too, so "Copy build steps" copies all of them.
    const [menuOpened, setMenuOpened] = useState(false);
    const open = running || expanded;
    const details = useRunDetails(message, expanded || menuOpened);
    const failed = Boolean(message.run_status && !QUIET.includes(message.run_status));
    const steps = details.activity;
    const calls = details.calls;
    const blocks = useMemo(() => timelineBlocks(timelineEntries(steps, calls)), [steps, calls]);
    // Folded, the card comes from history's edit summary instead of the full steps.
    const edits = details.loaded ? null : message.edits;
    const files = useMemo(() => editedFiles(edits ?? calls), [edits, calls]);
    const transcript = blocks
        .flatMap((block) =>
            block.kind === "note"
                ? [block.item.message || "Verification"]
                : block.kind === "section"
                  ? block.lines.map((line) => `${line.kind} ${line.text}`)
                  : [`${block.ids.length} screenshot${block.ids.length === 1 ? "" : "s"}`],
        )
        .join("\n");
    const latest = steps.filter((item) => item.kind === "stage").at(-1)?.message;
    const took = workedFor(message.created_at, message.finished_at);
    const finished: Partial<Record<string, string>> = {
        succeeded: `Worked for ${took}`,
        cancelled: `Stopped after ${took}`,
        stopped: `Paused at its limit after ${took}`,
        awaiting_input: "Waiting for your response",
        answered: message.workflow?.kind === "answer" ? "Answered" : "Response saved",
    };
    const label = running
        ? connected
            ? latest || "Working on your app"
            : "Reconnecting to run"
        : (finished[message.run_status ?? ""] ??
          (failed ? `Needs attention after ${took}` : "Recorded steps"));
    return (
        <div className="transcript-run min-w-0" data-failed={failed}>
            <div className="flex min-h-9 items-center gap-2 border-b border-hairline pb-1.5">
                {running ? (
                    <span
                        role="status"
                        className="flex min-w-0 flex-1 items-center gap-2 text-[13.5px] text-muted-foreground"
                    >
                        {connected && <ThinkingOrb state="working" size={20} aria-hidden="true" />}
                        <span className="min-w-0 truncate">{label}</span>
                        <Elapsed start={message.created_at} running />
                    </span>
                ) : (
                    <button
                        type="button"
                        aria-expanded={expanded}
                        onClick={() => setExpanded(!expanded)}
                        className={`group flex min-w-0 cursor-pointer items-center gap-1.5 rounded-[6px] text-left text-[13.5px] [transition:color_130ms_ease] focus-visible:outline-2 focus-visible:outline-ring ${
                            failed
                                ? "text-destructive"
                                : "text-muted-foreground pointer-fine:hover:text-foreground"
                        }`}
                    >
                        <span role="status" className="min-w-0 truncate">
                            {label}
                        </span>
                        <ChevronRight
                            size={14}
                            aria-hidden="true"
                            className={`shrink-0 [transition:transform_180ms_var(--ease-out)] motion-reduce:[transition:none] ${expanded ? "rotate-90" : ""}`}
                        />
                    </button>
                )}
                <span className="ml-auto flex shrink-0 items-center gap-2">
                    {!running && <RelativeTime iso={message.finished_at || message.created_at} />}
                    <RunMenu
                        runId={message.id.replace(/^run:/, "")}
                        transcript={
                            running || details.loaded || !message.details_pending
                                ? transcript
                                : null
                        }
                        loadFailed={Boolean(details.error)}
                        onOpen={() => setMenuOpened(true)}
                    />
                </span>
            </div>
            {open && (
                <div className="animate-in fade-in pt-2 duration-150 ease-out motion-reduce:animate-none">
                    {details.loading && (
                        <p className="m-0 pb-2 text-[13px] text-muted-foreground" role="status">
                            Loading build steps…
                        </p>
                    )}
                    <div className="[&>[data-error-box]]:mb-2">
                        <ErrorBox message={details.error ?? ""}>
                            <Button variant="utility" onClick={details.retry}>
                                Retry
                            </Button>
                        </ErrorBox>
                    </div>
                    <RunTimeline blocks={blocks} running={running} />
                </div>
            )}
            {children}
            {!running && files.length > 0 && <EditedFiles files={files} />}
        </div>
    );
}
