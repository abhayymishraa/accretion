"use client";

// Interaction patterns adapted from Beautiful UI, MIT © 2026 Shane Levine.
// See ../ember/BEAUTIFUL-UI-LICENSE. All progress comes from recorded run events.
import type { Message } from "@/types/chat.type";
import { CheckIcon, ChevronRightIcon, ClockIcon, Cross2Icon } from "@radix-ui/react-icons";
import { useEffect, useMemo, useRef, useState } from "react";
import styles from "./transcript.module.css";

import { Elapsed, PixelLoader } from "./RunStatus";
import { RelativeTime, RunMenu } from "./RunMenu";
import { FileChips, ToolGroup, ToolRow } from "./ToolList";
import { RecordedResult } from "./ToolResult";
import { useRunDetails } from "@/hooks/chat/useRunDetails";
import { groupTimeline, timelineEntries } from "@/lib/chat/run-timeline";
import { touchedFiles } from "@/lib/tool-presentation";
import { Button } from "@/components/ui/button";
export function RunActivity({ message, connected }: { message: Message; connected: boolean }) {
    const completionIcon = useRef<SVGSVGElement>(null);
    const [pointerReveal, setPointerReveal] = useState(false);
    const [expanded, setExpanded] = useState(false);
    const details = useRunDetails(message, expanded);
    const previousRun = useRef({ id: message.id, status: message.run_status });

    useEffect(() => {
        const previous = previousRun.current;
        previousRun.current = { id: message.id, status: message.run_status };
        // Celebrate only a live transition, never an already-completed history entry.
        if (
            previous.id !== message.id ||
            previous.status !== "running" ||
            message.run_status !== "succeeded"
        )
            return;
        const icon = completionIcon.current;
        if (!icon?.animate) return;
        const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        const easing = getComputedStyle(icon).getPropertyValue("--ease-out").trim();
        const animation = icon.animate(
            reduced
                ? [{ opacity: 0.6 }, { opacity: 1 }]
                : [
                      { opacity: 0, transform: "scale(0.94)" },
                      { opacity: 1, transform: "scale(1)" },
                  ],
            { duration: reduced ? 80 : 180, easing: easing || "cubic-bezier(0.23, 1, 0.32, 1)" },
        );
        return () => animation.cancel();
    }, [message.id, message.run_status]);

    const running = message.run_status === "running";
    const failed =
        message.run_status &&
        !["running", "succeeded", "cancelled", "stopped", "awaiting_input", "answered"].includes(
            message.run_status,
        );
    const steps = details.activity;
    const calls = details.calls;
    // An approved plan is replayed as kind "execute"; it belongs in the trace, not the transcript.
    const approach = message.workflow?.kind === "execute" ? message.workflow : null;
    // Both walk every tool call and presentTool parses each result, so they are
    // recomputed only when the run's steps or calls actually change.
    const timeline = useMemo(() => groupTimeline(timelineEntries(steps, calls)), [steps, calls]);
    const files = useMemo(() => touchedFiles(calls), [calls]);
    const transcript = timeline
        .map((entry) =>
            entry.kind === "stage"
                ? entry.item.message || "Verification"
                : entry.kind === "group"
                  ? `${entry.name} x${entry.items.length}`
                  : entry.item.name,
        )
        .join("\n");
    const latest = steps.filter((item) => item.kind === "stage").at(-1)?.message;
    let label = "Recorded steps";
    if (running) {
        label = connected ? latest || "Working on your app" : "Reconnecting to run";
    } else if (message.run_status === "succeeded") {
        label = "Build complete";
    } else if (message.run_status === "cancelled") {
        label = "Run stopped";
    } else if (message.run_status === "stopped") {
        label = "Paused at its limit";
    } else if (message.run_status === "awaiting_input") {
        label = "Waiting for your response";
    } else if (message.run_status === "answered") {
        label = message.workflow?.kind === "answer" ? "Answered" : "Response saved";
    } else if (failed) {
        label = "Run needs attention";
    }
    return (
        <div
            className="transcript-run min-w-0 mt-2 [&[data-failed=true]_.transcript-status]:text-destructive"
            data-failed={Boolean(failed)}
        >
            <div className="transcript-runHeader flex items-baseline justify-between gap-3 pt-1 px-0 pb-2.5 max-[481px]:gap-2">
                <span
                    role="status"
                    className="transcript-status flex items-center gap-[9px] text-[13px] leading-[1.5] text-foreground wrap-anywhere [&>svg]:shrink-0"
                >
                    {running && connected ? (
                        <PixelLoader />
                    ) : failed ? (
                        <Cross2Icon aria-hidden="true" />
                    ) : running ||
                      message.run_status === "cancelled" ||
                      message.run_status === "stopped" ||
                      message.run_status === "awaiting_input" ? (
                        <ClockIcon aria-hidden="true" />
                    ) : (
                        <CheckIcon
                            ref={completionIcon}
                            className="origin-center [transform-box:fill-box]"
                            aria-hidden="true"
                        />
                    )}
                    {label}
                </span>
                <span className="flex shrink-0 items-center gap-2.5">
                    <Elapsed
                        start={message.created_at}
                        end={message.finished_at}
                        running={running}
                    />
                    {!running && <RelativeTime iso={message.finished_at || message.created_at} />}
                    <RunMenu runId={message.id.replace(/^run:/, "")} transcript={transcript} />
                </span>
            </div>
            {(message.details_pending || steps.length > 0 || calls.length > 0) && (
                <details
                    onToggle={(event) => setExpanded(event.currentTarget.open)}
                    data-pointer-reveal={pointerReveal}
                    className={`${styles.buildTrace} transcript-trace [&>summary]:list-none [&>summary]:flex [&>summary]:items-center [&>summary]:gap-2 [&>summary]:cursor-pointer [&>summary]:min-h-11 [&>summary]:text-[12px] [&>summary::-webkit-details-marker]:hidden [&[open]>summary>.transcript-chevron]:rotate-90 [&>summary]:text-muted-foreground`}
                >
                    <summary
                        onClick={(event) => setPointerReveal(event.detail > 0)}
                        onKeyDown={() => setPointerReveal(false)}
                    >
                        <ChevronRightIcon
                            className="transcript-chevron w-[13px] shrink-0 [transition:transform_.18s_ease-out] motion-reduce:[transition:none]"
                            aria-hidden="true"
                        />
                        Build steps{" "}
                        <span className="transcript-caption font-mono text-[11px] text-muted-foreground">
                            {timeline.length || ""}
                        </span>
                    </summary>
                    <div className={styles.buildDetails}>
                        {approach && (
                            <div className="pb-2 pl-[7px] text-[12px] text-muted-foreground">
                                <p className="m-0 pb-1 wrap-anywhere">{approach.summary}</p>
                                {approach.steps.map((step, index) => (
                                    <p className="m-0 flex gap-3 py-1 wrap-anywhere" key={index}>
                                        <span aria-hidden="true" className="tabular-nums">
                                            {index + 1}
                                        </span>
                                        <span className="min-w-0">{step}</span>
                                    </p>
                                ))}
                            </div>
                        )}
                        {details.loading && <p role="status">Loading build steps…</p>}
                        {details.error && (
                            <p role="alert">
                                {details.error}{" "}
                                <Button variant="utility" onClick={details.retry}>
                                    Retry
                                </Button>
                            </p>
                        )}
                        <div className="grid gap-1 pt-0 pr-0 pb-2 pl-[7px]">
                            {timeline.map((entry) =>
                                entry.kind === "group" ? (
                                    <ToolGroup
                                        key={`${entry.name}:${entry.order}`}
                                        name={entry.name}
                                        calls={entry.items}
                                    />
                                ) : entry.kind === "tool" ? (
                                    <ToolRow
                                        key={entry.item.event_id || entry.item.id}
                                        tool={entry.item}
                                    />
                                ) : (
                                    <div
                                        key={entry.item.id}
                                        data-failed={entry.item.ok === false}
                                        className="flex min-h-9 min-w-0 items-center gap-2 px-1 text-[12.5px] text-muted-foreground data-[failed=true]:text-destructive"
                                    >
                                        <span
                                            aria-hidden="true"
                                            className="flex size-4 shrink-0 items-center justify-center"
                                        >
                                            <span className="size-1 rounded-full bg-current" />
                                        </span>
                                        <div className="min-w-0 flex-1 wrap-anywhere">
                                            <p className="m-0">
                                                {entry.item.message || "Verification"}
                                            </p>
                                            {entry.item.checks !== undefined && (
                                                <RecordedResult
                                                    label="Check results"
                                                    output={JSON.stringify(
                                                        entry.item.checks,
                                                        null,
                                                        2,
                                                    )}
                                                />
                                            )}
                                        </div>
                                    </div>
                                ),
                            )}
                        </div>
                        {files.length > 0 && <FileChips files={files} />}
                    </div>
                </details>
            )}
        </div>
    );
}
