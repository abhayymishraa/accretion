"use client";

import { RelativeTime } from "@/components/chat/RunMenu";
import { RemoveRow } from "@/components/github/RemoveRow";
import { Button, buttonVariants } from "@/components/ui/button";
import type { Publish } from "@/types/vercel.type";
import { Copy, ExternalLink, Share2 } from "lucide-react";
import { toast } from "sonner";

/** The live address with Copy, Share and Open, whether it shows the latest changes, and Unpublish. */
export function PublishLive({
    publish,
    landed,
    busy,
    onUpdate,
    onUnpublish,
}: {
    publish: Publish & { url: string };
    // It just went live while the sheet was open: the card rises in, once.
    landed: boolean;
    busy: boolean;
    onUpdate: () => void;
    onUnpublish: () => Promise<string>;
}) {
    const address = publish.url.replace(/^https:\/\//, "");
    const copy = () =>
        navigator.clipboard.writeText(publish.url).then(
            () => toast.success("Link copied"),
            () => toast.error("Could not copy the link"),
        );
    // The phone's own share sheet where there is one; copying is the fallback everywhere else.
    const canShare = typeof navigator !== "undefined" && typeof navigator.share === "function";
    const share = () =>
        navigator.share({ url: publish.url }).catch((reason: unknown) => {
            if (!(reason instanceof DOMException && reason.name === "AbortError")) void copy();
        });
    const rise = landed
        ? "[transition:opacity_260ms_var(--ease-out),translate_260ms_var(--ease-out)] starting:opacity-0 motion-safe:starting:translate-y-2 motion-reduce:[transition-duration:150ms]"
        : "";
    // The actions follow the card by 60ms.
    const riseAfter = landed
        ? "[transition:opacity_260ms_var(--ease-out)_60ms,translate_260ms_var(--ease-out)_60ms] starting:opacity-0 motion-safe:starting:translate-y-2 motion-reduce:[transition-duration:150ms]"
        : "";
    return (
        <div className="grid gap-4">
            <div
                className={`grid gap-3 rounded-[12px] border border-border bg-surface-2 p-3 ${rise}`}
            >
                <div className="grid gap-0.5">
                    <p className="flex items-center gap-2 text-xs text-muted-foreground">
                        Live
                        {publish.published_at && <RelativeTime iso={publish.published_at} />}
                    </p>
                    <a
                        href={publish.url}
                        target="_blank"
                        rel="noreferrer"
                        className="truncate text-[15px] font-medium text-foreground no-underline pointer-fine:hover:underline"
                    >
                        {address}
                    </a>
                </div>
                <div className={`grid grid-cols-3 gap-2 ${riseAfter}`}>
                    <Button variant="secondary" className="px-2" onClick={() => void copy()}>
                        <Copy size={14} aria-hidden="true" />
                        Copy
                    </Button>
                    <Button
                        variant="secondary"
                        className="px-2"
                        onClick={() => void (canShare ? share() : copy())}
                    >
                        <Share2 size={14} aria-hidden="true" />
                        Share
                    </Button>
                    <a
                        href={publish.url}
                        target="_blank"
                        rel="noreferrer"
                        className={`${buttonVariants({ variant: "secondary" })} px-2`}
                    >
                        <ExternalLink size={14} aria-hidden="true" />
                        Open
                    </a>
                </div>
            </div>
            {publish.current ? (
                <p className="text-xs leading-[1.5] text-muted-foreground">
                    The live app has your latest changes.
                </p>
            ) : (
                <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                    <p className="mr-auto text-[13px]">Your latest changes aren&apos;t live yet.</p>
                    <Button disabled={busy} onClick={onUpdate}>
                        {busy ? "Starting…" : "Publish changes"}
                    </Button>
                </div>
            )}
            <RemoveRow
                note="Take the app offline. Its data stays in your Vercel account."
                label="Unpublish"
                question="Take this app offline?"
                onConfirm={onUnpublish}
            />
        </div>
    );
}
