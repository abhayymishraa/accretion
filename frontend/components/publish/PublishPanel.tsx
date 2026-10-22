"use client";

import { WorkspaceTabPanel } from "@/components/chat/WorkspaceTabPanel";
import { RemoveRow } from "@/components/github/RemoveRow";
import { PANEL_LINK } from "@/components/github/RepoStatus";
import { Button, buttonVariants } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { IconSwap } from "@/components/ui/IconSwap";
import { Skeleton } from "@/components/ui/skeleton";
import { usePublish } from "@/hooks/publish/usePublish";
import type { Publish } from "@/types/vercel.type";
import { Check, Copy, ExternalLink, Globe, Share2 } from "lucide-react";
import { type ReactNode, useState } from "react";
import { flushSync } from "react-dom";
import { toast } from "sonner";
import { describe, PublishCard, PublishRoute, type View } from "./PublishCard";

const NOTE = "text-xs leading-[1.5] text-muted-foreground";
// Full width on a phone, inline from sm up.
const WIDE = "max-sm:w-full";
// Rises into place once, after the route's last leg (420ms) and check; reduced motion keeps the fade only.
const LANDS =
    "transition-[opacity,translate] delay-[480ms] duration-[260ms] ease-[var(--ease-out)] starting:translate-y-1.5 starting:opacity-0 motion-reduce:delay-0 motion-reduce:starting:translate-y-0";

/** The request a failed publish hands the builder: the reason, then the end of the log the backend redacted. */
function askText(publish: Publish) {
    const log = publish.log.length
        ? // Four backticks, so a log line holding three cannot end the block.
          `\n\nThe end of the build log:\n\`\`\`\`\n${publish.log.join("\n")}\n\`\`\`\``
        : "";
    const reason = publish.message ?? "it stopped before it finished.";
    return `Publishing my app failed: ${reason}${log}\n\nPlease fix it so the app publishes.`;
}

/** Nothing on the web yet, laid out like the GitHub and Database tabs before they connect: a figure, a heading,
 * a note and one button on one centre line. The figure is the route the app will take, drawn dashed; the
 * status card fills in the same route once publishing starts, so the first tap continues a path already seen. */
function NotLive({ note, action, error }: { note: string; action: ReactNode; error: string }) {
    return (
        <div className="grid justify-items-center pb-4 text-center">
            <PublishRoute now={-1} className="w-full max-w-[300px] pt-6 pb-7" />
            <h3 className="text-[13px] font-semibold">Not on the web yet</h3>
            <p className={`${NOTE} mt-0.5 max-w-[36ch] text-pretty`}>{note}</p>
            <div className="mt-4">{action}</div>
            <ErrorBox message={error} className="mt-3 text-xs" />
        </div>
    );
}

/** The workspace's Publish tab: put the app on the web at its own address, keep it current, or take it off. */
export function PublishPanel({
    projectId,
    revisionId,
    onAskBuilder,
}: {
    projectId: string;
    revisionId?: string | null;
    onAskBuilder: (text: string) => void;
}) {
    const project = usePublish(projectId, revisionId);
    const { publish, account } = project;
    const [error, setError] = useState("");
    const [acting, setActing] = useState(false);
    // The last state shown, so one that changes while the tab is open can fade in.
    const [shown, setShown] = useState<View | null>(null);
    const [moved, setMoved] = useState(false);
    // The first publish finished while the tab watched: the route finishes and the address lands at its end.
    const [arrived, setArrived] = useState(false);
    const [copied, setCopied] = useState(false);
    const act = async (work: () => Promise<string>) => {
        setActing(true);
        setError(await work());
        setActing(false);
    };
    const connect = async () => {
        setActing(true);
        const failure = await project.connect();
        // Success leaves the page for Vercel, so the button stays on "Opening Vercel…" until it goes.
        if (!failure) return;
        setError(failure);
        setActing(false);
    };
    const url = publish?.url ?? null;
    // The first publish moves the dashed route into the status card. The request has already answered, so only
    // the screen update runs inside the transition; a browser without view transitions just shows the fade.
    const land = (update: () => void) => {
        const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
        if (state !== "ready" || still || !("startViewTransition" in document)) return update();
        document.startViewTransition(() => flushSync(update)).ready.catch(() => {});
    };

    const connectButton = (
        <Button disabled={acting} onClick={connect} className={WIDE}>
            {acting ? "Opening Vercel…" : "Connect Vercel"}
        </Button>
    );
    const publishButton = (label: string, variant: "default" | "secondary" = "default") => (
        <Button
            variant={variant}
            disabled={acting || !revisionId}
            onClick={() => act(() => project.start(land))}
            className={WIDE}
        >
            {acting ? "Starting…" : label}
        </Button>
    );
    const openApp = (variant: "default" | "secondary") => (
        <a
            href={url ?? undefined}
            target="_blank"
            rel="noreferrer"
            className={`${buttonVariants({ variant })} ${WIDE}`}
        >
            <ExternalLink size={14} aria-hidden="true" />
            Open app
        </a>
    );
    const copyAddress = (
        <Button
            variant="secondary"
            className={WIDE}
            onClick={() =>
                navigator.clipboard.writeText(url ?? "").then(
                    // Confirmed at the button, as the code blocks' copy does.
                    () => {
                        setCopied(true);
                        setTimeout(() => setCopied(false), 1500);
                    },
                    () => toast.error("Could not copy the address"),
                )
            }
        >
            <IconSwap
                swapped={copied}
                from={<Copy size={14} aria-hidden="true" />}
                to={<Check size={14} aria-hidden="true" />}
            />
            {/* The words change too, so a screen reader hears the copy worked. */}
            {copied ? "Copied" : "Copy address"}
        </Button>
    );
    // The phone's own share sheet, where there is one: the usual way a link leaves a phone.
    const shareApp = typeof navigator !== "undefined" && typeof navigator.share === "function" && (
        <Button
            variant="secondary"
            className={WIDE}
            onClick={() => navigator.share({ url: url ?? "" }).catch(() => {})}
        >
            <Share2 size={14} aria-hidden="true" />
            Share
        </Button>
    );

    let state: View = "loading";
    let body: ReactNode;
    // A copy on the web shows without the account; only a first publish needs it.
    if (!publish || (!url && !account)) {
        if (project.failed) state = "error";
        body = project.failed ? (
            <ErrorBox
                message="Couldn't load this app's publish status."
                onRetry={() => void project.retry()}
            />
        ) : (
            <Skeleton className="h-24 rounded-[10px]" aria-label="Loading" />
        );
    } else if (account && !account.configured) {
        state = "unavailable";
        body = <p className={NOTE}>Publishing isn&apos;t available here yet.</p>;
    } else if (account && !account.connected && !url) {
        state = "connect";
        body = (
            <NotLive
                note="Connect a free Vercel account once. Your app is published there, under your name."
                action={connectButton}
                error={error}
            />
        );
    } else if (publish.status === "none") {
        state = "ready";
        body = (
            <NotLive
                note={
                    revisionId
                        ? "Publishing gives your app its own address that anyone can open. It usually takes a minute or two."
                        : "Build your app first, then publish it."
                }
                action={publishButton("Publish")}
                error={error}
            />
        );
    } else {
        const card = describe(publish, account?.connected === false);
        state = card.state;
        const actions: Partial<Record<View, ReactNode>> = {
            reconnect: (
                <>
                    {connectButton}
                    {url && openApp("secondary")}
                </>
            ),
            updating: openApp("secondary"),
            live: (
                <>
                    {openApp("default")}
                    {shareApp}
                    {copyAddress}
                    {publishButton("Publish again", "secondary")}
                </>
            ),
            changed: (
                <>
                    {publishButton("Publish changes")}
                    {openApp("secondary")}
                    {shareApp}
                    {copyAddress}
                </>
            ),
            database: (
                <>
                    {publish.dashboard_url && (
                        <a
                            href={publish.dashboard_url}
                            target="_blank"
                            rel="noreferrer"
                            className={`${buttonVariants({ variant: "default" })} ${WIDE}`}
                        >
                            <ExternalLink size={14} aria-hidden="true" />
                            Add a database on Vercel
                        </a>
                    )}
                    {publishButton("Publish again", "secondary")}
                </>
            ),
            failed: (
                <>
                    <Button onClick={() => onAskBuilder(askText(publish))} className={WIDE}>
                        Ask the builder to fix it
                    </Button>
                    {publishButton("Try again", "secondary")}
                </>
            ),
        };
        const removable = ["live", "changed", "database", "failed"].includes(state) && url !== null;
        body = (
            <div className="grid gap-3">
                {url && (
                    // The host alone, after a globe as the GitHub tab puts its mark before the repository: the part
                    // people read aloud and share. On arrival it lands after the route's last leg has drawn in.
                    <a
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className={`${PANEL_LINK} min-w-0 ${arrived ? LANDS : ""}`}
                    >
                        <Globe size={14} aria-hidden="true" className="shrink-0 text-foreground" />
                        <span className="truncate">{url.replace(/^https?:\/\//, "")}</span>
                        <ExternalLink size={13} aria-hidden="true" className="shrink-0" />
                    </a>
                )}
                <PublishCard publish={publish} card={card} arrived={arrived} />
                {state === "first" && (
                    <p className={NOTE}>You can leave this tab. Publishing keeps going.</p>
                )}
                <div className="flex flex-wrap gap-2 empty:hidden">{actions[state]}</div>
                <ErrorBox message={error} className="text-xs" />
                {removable && (
                    <RemoveRow
                        note="Take the app off the web. Its address stops working."
                        label="Unpublish"
                        question="Unpublish? The address stops working. Your project here stays, and any database you added stays on Vercel."
                        onConfirm={project.unpublish}
                    />
                )}
            </div>
        );
    }

    // Opening the tab, or loading, never fades.
    if (state !== "loading" && state !== shown) {
        setMoved(shown !== null);
        setArrived(shown === "first" && state === "live");
        setShown(state);
    }

    return (
        <WorkspaceTabPanel
            title="Publish"
            note="Put your app on the web at its own address, so anyone can open it."
        >
            <div key={state} data-loaded-in={moved ? "" : undefined}>
                {body}
            </div>
        </WorkspaceTabPanel>
    );
}
