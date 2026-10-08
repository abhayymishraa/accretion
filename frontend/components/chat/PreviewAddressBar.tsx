"use client";

import { Button, buttonVariants } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import type { PreviewPhase } from "@/types/preview.type";
import {
    ArrowLeft,
    ArrowRight,
    ChevronDown,
    ExternalLink,
    Power,
    RotateCcw,
    Smartphone,
} from "lucide-react";
import { useState } from "react";

const STATUS: Record<PreviewPhase, string> = {
    active: "Running",
    building: "Building",
    opening: "Starting",
    checking: "Starting",
    sleeping: "Sleeping",
    error: "Stopped",
};

/** The preview's address bar. History comes from the bridge the preview proxy adds (usePreviewHistory). */
export function PreviewAddressBar({
    src,
    current,
    canBack,
    canForward,
    onBack,
    onForward,
    phase,
    mobile,
    onToggleMobile,
    onNavigate,
    onRefresh,
}: {
    src: string | null;
    // The page the app is on now, as its bridge reports it; null for a preview without one.
    current: string | null;
    canBack: boolean;
    canForward: boolean;
    onBack: () => void;
    onForward: () => void;
    phase: PreviewPhase;
    mobile: boolean;
    onToggleMobile: () => void;
    onNavigate: (path: string) => void;
    onRefresh: () => void;
}) {
    const [path, setPath] = useState("/");
    // While typing, the field holds the draft; otherwise it follows the app's own navigation.
    const [typing, setTyping] = useState(false);
    const ready = Boolean(src) && phase === "active";
    return (
        <div className="flex h-10 pointer-coarse:h-11 shrink-0 items-center gap-0.5 border-b border-b-border bg-background px-2 max-md:px-1.5">
            <Button variant="icon" disabled={!canBack} aria-label="Back" onClick={onBack}>
                <ArrowLeft size={15} />
            </Button>
            <Button variant="icon" disabled={!canForward} aria-label="Forward" onClick={onForward}>
                <ArrowRight size={15} />
            </Button>
            {/* A phone-width panel is already narrower than the mobile frame. */}
            <Button
                variant="icon"
                className="max-md:hidden"
                aria-label={mobile ? "Responsive preview" : "Mobile preview"}
                aria-pressed={mobile}
                onClick={onToggleMobile}
            >
                <Smartphone size={15} />
            </Button>
            <form
                className="min-w-0 flex-1"
                onSubmit={(event) => {
                    event.preventDefault();
                    // One leading slash: "//host" would leave the preview's origin.
                    const next = `/${path.trim().replace(/^\/+/, "")}`;
                    setPath(next);
                    event.currentTarget.querySelector("input")?.blur();
                    onNavigate(next);
                }}
            >
                <input
                    aria-label="Preview path"
                    value={typing ? path : (current ?? path)}
                    disabled={!ready}
                    spellCheck={false}
                    onFocus={() => {
                        setPath(current ?? path);
                        setTyping(true);
                    }}
                    onBlur={() => setTyping(false)}
                    onChange={(event) => setPath(event.target.value)}
                    className="h-7 w-full rounded-[7px] border border-border bg-surface-2 px-2.5 font-mono text-[12px] pointer-coarse:h-11 pointer-coarse:text-[16px] text-foreground outline-none [transition:border-color_130ms_ease] focus-visible:border-ring disabled:opacity-50"
                />
            </form>
            {ready && src && (
                <a
                    href={current ? new URL(current, src).href : src}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={buttonVariants({ variant: "icon" })}
                    aria-label="Open preview in new tab"
                >
                    <ExternalLink size={15} />
                </a>
            )}
            <Button
                variant="icon"
                disabled={!ready}
                aria-label="Reload preview"
                onClick={onRefresh}
            >
                <RotateCcw size={14} />
            </Button>
            <Popover>
                <PopoverTrigger asChild>
                    <Button variant="icon" aria-label="Preview status">
                        <ChevronDown size={15} />
                    </Button>
                </PopoverTrigger>
                <PopoverContent align="end" className="w-60 text-[13px]">
                    <div className="flex items-center justify-between gap-3">
                        <span className="flex items-center gap-2">
                            <span
                                aria-hidden="true"
                                className={`size-2 rounded-full ${ready ? "bg-emerald-500" : "bg-muted-foreground/50"}`}
                            />
                            {STATUS[phase]}
                        </span>
                        {/* ponytail: shown, not wired; restart needs a backend action first. */}
                        <Button
                            variant="icon"
                            disabled
                            aria-label="Hard restart (coming soon)"
                            title="Hard restart is coming soon"
                        >
                            <Power size={14} />
                        </Button>
                    </div>
                </PopoverContent>
            </Popover>
        </div>
    );
}
