"use client";

import styles from "@/components/chat/menu.module.css";
import { Button } from "@/components/ui/button";
import { DotsHorizontalIcon } from "@radix-ui/react-icons";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { toast } from "sonner";

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
    ["day", 86_400_000],
    ["hour", 3_600_000],
    ["minute", 60_000],
];

const FORMAT = new Intl.RelativeTimeFormat(undefined, { numeric: "auto", style: "narrow" });

function relative(iso: string) {
    const elapsed = Date.now() - new Date(iso).getTime();
    if (!Number.isFinite(elapsed)) return "";
    for (const [unit, ms] of UNITS) {
        if (elapsed >= ms) return FORMAT.format(-Math.floor(elapsed / ms), unit);
    }
    return FORMAT.format(-Math.round(elapsed / 1000), "second");
}

const noSubscribe = () => () => {};

/** Client-only: the server cannot know the reader's clock, so it renders nothing. */
export function RelativeTime({ iso }: { iso: string }) {
    const label = useSyncExternalStore(
        noSubscribe,
        () => relative(iso),
        () => "",
    );
    if (!label) return null;
    return (
        <time dateTime={iso} className="shrink-0 text-[11px] text-muted-foreground">
            {label}
        </time>
    );
}

export function RunMenu({
    runId,
    transcript,
    onOpen,
}: {
    runId: string;
    // null while the run's steps are still loading.
    transcript: string | null;
    onOpen: () => void;
}) {
    const [open, setOpen] = useState(false);
    const box = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!open) return;
        const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
        const onDown = (event: PointerEvent) => {
            if (!box.current?.contains(event.target as Node)) setOpen(false);
        };
        document.addEventListener("keydown", onKey);
        document.addEventListener("pointerdown", onDown);
        return () => {
            document.removeEventListener("keydown", onKey);
            document.removeEventListener("pointerdown", onDown);
        };
    }, [open]);

    const copy = async (value: string, success: string) => {
        setOpen(false);
        try {
            await navigator.clipboard.writeText(value);
            toast.success(success, { id: "run-copy" });
        } catch {
            toast.error("Copy failed. Select the visible text to copy it.", { id: "run-copy" });
        }
    };

    return (
        <div ref={box} className="relative shrink-0">
            <Button
                type="button"
                variant="utility"
                aria-haspopup="menu"
                aria-expanded={open}
                aria-label="Run options"
                onClick={() => {
                    if (!open) onOpen();
                    setOpen(!open);
                }}
            >
                <DotsHorizontalIcon aria-hidden="true" />
            </Button>
            {/* Stays mounted so it can leave as well as arrive. origin-top-right
                added: it was scaling from centre, not from its trigger. */}
            <div
                role="menu"
                data-state={open ? "open" : "closed"}
                aria-hidden={!open}
                inert={!open}
                className={`${styles.menu} absolute top-full right-0 z-50 mt-1 w-48 origin-top-right overflow-hidden rounded-[10px] border border-border bg-surface-2`}
            >
                <button
                    role="menuitem"
                    type="button"
                    onClick={() => void copy(runId, "Run id copied")}
                    className="flex min-h-9 w-full cursor-pointer items-center px-3 text-left text-[12.5px] text-foreground pointer-fine:hover:bg-surface-1"
                >
                    Copy run id
                </button>
                <button
                    role="menuitem"
                    type="button"
                    disabled={transcript === null}
                    onClick={() =>
                        transcript !== null && void copy(transcript, "Build steps copied")
                    }
                    className="flex min-h-9 w-full cursor-pointer items-center px-3 text-left text-[12.5px] text-foreground pointer-fine:hover:bg-surface-1 disabled:cursor-default disabled:text-muted-foreground"
                >
                    {transcript === null ? "Loading build steps…" : "Copy build steps"}
                </button>
            </div>
        </div>
    );
}
