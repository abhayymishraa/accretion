"use client";

import { Button, buttonVariants } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import type { PreviewPhase } from "@/types/preview.type";
import { ChevronDown, ExternalLink, Power, RotateCcw, Smartphone } from "lucide-react";
import { useState } from "react";

const STATUS: Record<PreviewPhase, string> = {
    active: "Running",
    building: "Building",
    opening: "Starting",
    checking: "Starting",
    sleeping: "Sleeping",
    error: "Stopped",
};

/** v0's address bar minus history buttons: a cross-origin frame cannot be stepped back. */
export function PreviewAddressBar({
    src,
    phase,
    mobile,
    onToggleMobile,
    onNavigate,
    onRefresh,
}: {
    src: string | null;
    phase: PreviewPhase;
    mobile: boolean;
    onToggleMobile: () => void;
    onNavigate: (path: string) => void;
    onRefresh: () => void;
}) {
    const [path, setPath] = useState("/");
    const ready = Boolean(src) && phase === "active";
    return (
        <div className="flex h-10 shrink-0 items-center gap-0.5 border-b border-b-border bg-background px-2 max-md:px-1.5">
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
                    onNavigate(next);
                }}
            >
                <input
                    aria-label="Preview path"
                    value={path}
                    disabled={!ready}
                    spellCheck={false}
                    onChange={(event) => setPath(event.target.value)}
                    className="h-7 w-full rounded-[7px] border border-border bg-surface-2 px-2.5 font-mono text-[12px] text-foreground outline-none [transition:border-color_130ms_ease] focus-visible:border-ring disabled:opacity-50"
                />
            </form>
            {ready && src && (
                <a
                    href={src}
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
