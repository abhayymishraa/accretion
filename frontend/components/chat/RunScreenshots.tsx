"use client";

import Image from "next/image";
import { useState } from "react";

import { useScreenshot } from "@/hooks/chat/useScreenshot";

function Screenshot({ runId, screenshotId }: { runId: string; screenshotId: string }) {
    const { url, failed } = useScreenshot(runId, screenshotId);
    const [open, setOpen] = useState(false);
    if (failed)
        return <p className="m-0 text-[12.5px] text-muted-foreground">Screenshot unavailable.</p>;
    return (
        <button
            type="button"
            aria-expanded={open}
            aria-label={open ? "Shrink screenshot" : "Show the whole screenshot"}
            onClick={() => setOpen(!open)}
            className={`block max-w-full cursor-zoom-in overflow-hidden rounded-[10px] border border-border bg-surface-2 text-left focus-visible:outline-2 focus-visible:outline-ring data-[open=true]:cursor-zoom-out ${open ? "" : "max-h-72"}`}
            data-open={open}
        >
            {url ? (
                // A session-authenticated blob URL: served as is, at the image's own size.
                <Image
                    src={url}
                    alt="Screenshot from checking the app"
                    unoptimized
                    width={0}
                    height={0}
                    className="block h-auto w-auto max-w-full animate-in fade-in duration-200 ease-out motion-reduce:animate-none"
                />
            ) : (
                <span className="block h-44 w-[min(36rem,80vw)] bg-surface-3 motion-safe:animate-pulse" />
            )}
        </button>
    );
}

/** The images a browser check saved, shown right after its command. */
export function RunScreenshots({ runId, ids }: { runId: string; ids: string[] }) {
    return (
        <div className="grid max-w-[36rem] justify-items-start gap-2 py-1.5">
            {ids.map((id) => (
                <Screenshot key={id} runId={runId} screenshotId={id} />
            ))}
        </div>
    );
}
