"use client";

import { PANEL_LINK } from "@/components/github/RepoStatus";
import { Button } from "@/components/ui/button";
import type { Publish } from "@/types/vercel.type";
import { Check, ExternalLink, LoaderCircle, TriangleAlert } from "lucide-react";

const STEPS = [
    { key: "uploading", label: "Upload your app" },
    { key: "building", label: "Build it on Vercel" },
    { key: "live", label: "Go live" },
] as const;

/** Where a running publish is: each step done, running, or still to come. */
export function PublishProgress({ publish }: { publish: Publish }) {
    const current = STEPS.findIndex((step) => step.key === publish.status);
    return (
        <div className="grid gap-3">
            <ol className="grid gap-2.5" aria-label="Publishing">
                {STEPS.map((step, index) => {
                    const done = index < current;
                    const running = index === current;
                    return (
                        <li
                            key={step.key}
                            aria-current={running ? "step" : undefined}
                            className={`flex items-center gap-2.5 text-[13px] [transition:color_200ms_var(--ease-out)] ${done || running ? "text-foreground" : "text-muted-foreground"}`}
                        >
                            <span className="grid size-5 shrink-0 place-items-center rounded-full border border-border bg-surface-2">
                                {done ? (
                                    <Check
                                        size={12}
                                        aria-hidden="true"
                                        className="text-emerald-700 [transition:opacity_160ms_var(--ease-out),scale_160ms_var(--ease-out)] starting:opacity-0 motion-safe:starting:scale-80 dark:text-[#22c55e]"
                                    />
                                ) : running ? (
                                    <LoaderCircle
                                        size={12}
                                        aria-hidden="true"
                                        className="text-primary motion-safe:animate-spin"
                                    />
                                ) : null}
                            </span>
                            {step.label}
                        </li>
                    );
                })}
            </ol>
            <p role="status" className="text-xs leading-[1.5] text-muted-foreground">
                {publish.message} You can close this. Publishing goes on without you.
            </p>
            {publish.logs_url && (
                <a href={publish.logs_url} target="_blank" rel="noreferrer" className={PANEL_LINK}>
                    Watch the build on Vercel
                    <ExternalLink size={13} aria-hidden="true" />
                </a>
            )}
        </div>
    );
}

/** A publish that did not finish: why, the end of the build log, and the ways forward. */
export function PublishFailed({
    publish,
    busy,
    onRetry,
    onAskBuilder,
}: {
    publish: Publish;
    busy: boolean;
    onRetry: () => void;
    onAskBuilder?: (text: string) => void;
}) {
    const reason = publish.message ?? "Publishing didn't finish.";
    const ask = () =>
        onAskBuilder?.(
            [
                "Publishing this app to Vercel failed. Fix the code so it builds and runs on Vercel.",
                reason,
                ...(publish.log.length ? ["Build log:", publish.log.join("\n")] : []),
            ].join("\n\n"),
        );
    return (
        <div className="grid gap-3">
            <div
                role="alert"
                className="flex items-start gap-2 rounded-[10px] border border-destructive/40 bg-destructive/8 px-3 py-2.5 text-[13px] leading-[1.5] wrap-anywhere text-destructive"
            >
                <TriangleAlert size={14} aria-hidden="true" className="mt-0.5 shrink-0" />
                {reason}
            </div>
            {publish.log.length > 0 && (
                <details
                    data-faq=""
                    className="group rounded-[10px] border border-border bg-surface-2"
                >
                    <summary className="flex min-h-11 cursor-pointer items-center px-3 text-[13px] font-medium">
                        Build log
                    </summary>
                    {/* Reversed column: the box opens scrolled to the end, where the error is. */}
                    <div className="flex max-h-60 flex-col-reverse overflow-auto border-t border-border">
                        <pre className="px-3 py-2 font-mono text-[11px] leading-[1.6] whitespace-pre-wrap text-muted-foreground">
                            {publish.log.join("\n")}
                        </pre>
                    </div>
                </details>
            )}
            <div className="flex flex-wrap gap-2">
                <Button disabled={busy} onClick={onRetry}>
                    {busy ? "Starting…" : "Try again"}
                </Button>
                {onAskBuilder && publish.log.length > 0 && (
                    <Button variant="secondary" disabled={busy} onClick={ask}>
                        Ask the builder to fix it
                    </Button>
                )}
            </div>
            {publish.logs_url && (
                <a href={publish.logs_url} target="_blank" rel="noreferrer" className={PANEL_LINK}>
                    Open the full log on Vercel
                    <ExternalLink size={13} aria-hidden="true" />
                </a>
            )}
        </div>
    );
}
