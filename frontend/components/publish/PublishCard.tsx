"use client";

import { PANEL_LINK, StatusLine } from "@/components/github/RepoStatus";
import { Button } from "@/components/ui/button";
import { IconSwap } from "@/components/ui/IconSwap";
import { publishBusy } from "@/hooks/publish/usePublish";
import type { Publish } from "@/types/vercel.type";
import { Circle, CircleCheck, ExternalLink, LoaderCircle } from "lucide-react";
import { useId, useState } from "react";

// The status card's lower part sits under a dashed rule, as the GitHub tab's file list does.
const RULE = "mt-2 border-t border-dashed border-border pt-2";
const STEPS = ["Send your app", "Build it", "Put it online"];

// The card renders on the client once the row has loaded, so the viewer's own locale is safe here.
const WHEN = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

type CardState = "reconnect" | "updating" | "first" | "live" | "changed" | "database" | "failed";
/** Every view the Publish panel shows: before there is a copy, then the card's own states. */
export type View = "loading" | "error" | "unavailable" | "connect" | "ready" | CardState;
type Card = {
    state: CardState;
    busy?: boolean;
    fine?: boolean;
    text: string;
    lines: string[];
};

/** What the status card says about a copy that exists or is on its way, in the user's words. */
export function describe(publish: Publish, reconnect: boolean): Card {
    const kept = publish.url !== null;
    const published = publish.published_at
        ? `Published ${WHEN.format(new Date(publish.published_at))}`
        : "";
    if (reconnect)
        return { state: "reconnect", text: "Connect Vercel again to keep publishing.", lines: [] };
    if (publishBusy(publish) && kept)
        return {
            state: "updating",
            busy: true,
            text: "Updating your app…",
            lines: ["The current version stays live until the new one is ready."],
        };
    if (publishBusy(publish))
        return {
            state: "first",
            busy: true,
            text: publish.status === "uploading" ? "Sending your app…" : "Building your app…",
            lines: [],
        };
    if (publish.status === "live" && publish.current)
        return {
            state: "live",
            fine: true,
            text: published ? `Live. ${published}` : "Live",
            // A changed key makes no new revision, so the copy reads as current; publishing again is the only
            // way the key reaches the live app.
            lines: ["Changed a key? Publish again to send it to the live app."],
        };
    if (publish.status === "live")
        return {
            state: "changed",
            text: "Your latest changes aren't live yet.",
            lines: [published],
        };
    if (publish.status === "database")
        return {
            state: "database",
            text: "Your app needs a database before it can go online.",
            lines: kept ? ["The current version stays live."] : [],
        };
    return {
        state: "failed",
        text: "Publishing didn't finish.",
        // Written for people by the backend, e.g. "Publishing took too long. Try again."
        lines: [publish.message ?? "", kept ? "The last version is still live." : ""],
    };
}

/** The way an app travels to the web: three stops in a row, joined by one line, so the path fills whatever
 * width it is given. Before the first publish it is the path ahead, dashed; while a publish runs, each leg
 * fills in behind the app. `now` is the stop at work: -1 before any publish, STEPS.length once the app has
 * arrived. The last stop never shows working: the live view replaces the card. */
export function PublishRoute({ now, className }: { now: number; className: string }) {
    const last = STEPS.length - 1;
    return (
        // One name for both places it shows, so the first publish can move it from the empty state into the card.
        <ol className={`grid grid-cols-3 [view-transition-name:publish-route] ${className}`}>
            {STEPS.map((step, index) => (
                <li
                    key={step}
                    aria-current={index === now ? "step" : undefined}
                    className={`relative grid justify-items-center gap-1.5 text-center text-xs leading-[1.4] ${index > now ? "text-muted-foreground" : ""}`}
                >
                    {index < last && (
                        // The leg to the next stop, icon edge to icon edge: dashed while ahead, drawn solid from the
                        // left once passed. The leg into the last stop draws itself as the live view arrives.
                        <span
                            aria-hidden="true"
                            className="absolute top-[7px] right-[calc(-50%+14px)] left-[calc(50%+14px)] h-0 border-t border-dashed border-muted-foreground/50"
                        >
                            <span
                                className={`absolute inset-x-0 -top-px h-px origin-left bg-emerald-700 transition-[scale] duration-[420ms] ease-[var(--ease-in-out)] motion-reduce:transition-none dark:bg-[#22c55e] ${index < now ? "scale-x-100" : "scale-x-0"} ${index === last - 1 ? "starting:scale-x-0" : ""}`}
                            />
                        </span>
                    )}
                    <span
                        // On arrival the last check lands once its leg has drawn in.
                        className={
                            index === last && now > last
                                ? "transition-[opacity,scale] delay-[360ms] duration-200 ease-[var(--ease-out)] starting:scale-75 starting:opacity-0 motion-reduce:delay-0 motion-reduce:starting:scale-100"
                                : ""
                        }
                    >
                        {/* Three looks from two swaps: waiting turns to working, working turns to done. */}
                        <IconSwap
                            swapped={index < now}
                            from={
                                <IconSwap
                                    swapped={index === now}
                                    from={
                                        <Circle
                                            size={14}
                                            aria-hidden="true"
                                            className="text-muted-foreground"
                                        />
                                    }
                                    to={
                                        <LoaderCircle
                                            size={14}
                                            aria-hidden="true"
                                            className={`text-muted-foreground ${index === now ? "motion-safe:animate-spin" : ""}`}
                                        />
                                    }
                                />
                            }
                            to={
                                <CircleCheck
                                    size={14}
                                    aria-hidden="true"
                                    className="text-emerald-700 dark:text-[#22c55e]"
                                />
                            }
                        />
                    </span>
                    {step}
                </li>
            ))}
        </ol>
    );
}

/** What the user does on Vercel when the app needs a database: a real sequence, so a numbered list. */
function DatabaseSteps({ database }: { database: Publish["database"] }) {
    return (
        <ol
            className={`${RULE} grid list-decimal gap-1 pl-5 text-[13px] marker:text-muted-foreground`}
        >
            <li>Open your app&apos;s storage page on Vercel.</li>
            <li>
                {database === "mongo"
                    ? "Add a free MongoDB Atlas database."
                    : "Add a free Neon database."}
            </li>
            <li>Come back here and publish again.</li>
        </ol>
    );
}

/** The end of a failed build's log, folded away: it is for the builder, and the user hands it over. */
function FailureLog({ log, logsUrl }: { log: string[]; logsUrl: string | null }) {
    const id = useId();
    const [open, setOpen] = useState(false);
    return (
        <div className={RULE}>
            <Button
                variant="utility"
                className="-ml-2"
                aria-expanded={open}
                aria-controls={id}
                onClick={() => setOpen(!open)}
            >
                {open ? "Hide what went wrong" : "Show what went wrong"}
            </Button>
            <div id={id} data-disclosure={open ? "open" : ""}>
                {/* Reversed, so it opens scrolled to the end, where the error is. */}
                <div className="flex max-h-48 flex-col-reverse overflow-auto rounded-[8px] bg-background">
                    <pre className="p-2 font-mono text-[11.5px] leading-[1.5] whitespace-pre-wrap wrap-anywhere text-muted-foreground">
                        {log.join("\n")}
                    </pre>
                </div>
                {logsUrl && (
                    <a href={logsUrl} target="_blank" rel="noreferrer" className={PANEL_LINK}>
                        See the full log on Vercel
                        <ExternalLink size={13} aria-hidden="true" />
                    </a>
                )}
            </div>
        </div>
    );
}

/** The status card: one line on where the copy is, plain notes under it, then the route, the database steps or
 * the log under a dashed rule. */
export function PublishCard({
    publish,
    card,
    arrived,
}: {
    publish: Publish;
    card: Card;
    /** The app went live while the tab watched: the route stays, finished, for this view. */
    arrived: boolean;
}) {
    return (
        <div className="rounded-[10px] border border-border bg-surface-2 px-3 py-2.5 text-[13px]">
            <StatusLine busy={!!card.busy} fine={!!card.fine} text={card.text} wrap />
            {card.lines.filter(Boolean).map((line) => (
                <p key={line} className="mt-1 pl-5 text-xs leading-[1.5] text-muted-foreground">
                    {line}
                </p>
            ))}
            {(card.busy || arrived) && (
                <PublishRoute
                    now={arrived ? STEPS.length : publish.status === "uploading" ? 0 : 1}
                    className={RULE}
                />
            )}
            {card.busy && publish.logs_url && (
                <a href={publish.logs_url} target="_blank" rel="noreferrer" className={PANEL_LINK}>
                    Watch the build on Vercel
                    <ExternalLink size={13} aria-hidden="true" />
                </a>
            )}
            {card.state === "database" && <DatabaseSteps database={publish.database} />}
            {card.state === "failed" && publish.log.length > 0 && (
                <FailureLog log={publish.log} logsUrl={publish.logs_url} />
            )}
        </div>
    );
}
