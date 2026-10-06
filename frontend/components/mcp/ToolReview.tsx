"use client";

import { Button } from "@/components/ui/button";
import type { Connections } from "@/hooks/connections/useConnections";
import type { Connection, ConnectionTool } from "@/types/connection.type";
import { Check, Eye, PenLine, RefreshCw, TriangleAlert } from "lucide-react";
import { useState } from "react";
import styles from "./mcp.module.css";

const UTILITY = "h-11 px-2.5 text-[12.5px] pointer-fine:h-8";

/** "resolve-library-id" and "read_wiki_contents" read as "Resolve library id", "Read wiki contents". */
function humanize(name: string) {
    const words = name.replace(/[-_.]+/g, " ").trim();
    return words.charAt(0).toUpperCase() + words.slice(1);
}

function ToolItem({
    tool,
    service,
    checked,
    onChange,
}: {
    tool: ConnectionTool;
    service: string;
    checked: boolean;
    onChange: (checked: boolean) => void;
}) {
    return (
        <li className="bg-background">
            <label className="flex cursor-pointer gap-3 px-4 py-3 [transition:background-color_140ms_ease] pointer-fine:hover:bg-surface-1">
                {/* The whole row is the 44px target; the box itself stays a calm 18px. */}
                <input
                    type="checkbox"
                    checked={checked}
                    onChange={(event) => onChange(event.target.checked)}
                    className="mt-0.5 size-[18px] shrink-0 cursor-pointer accent-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                />
                <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                        <span className="text-[13.5px] font-medium wrap-anywhere">
                            {humanize(tool.name)}
                        </span>
                        {tool.read_only ? (
                            <span className="inline-flex items-center gap-1 text-[11.5px] text-muted-foreground">
                                <Eye size={12} aria-hidden="true" />
                                Only reads
                            </span>
                        ) : (
                            <span className="inline-flex items-center gap-1 text-[11.5px] text-amber-700 dark:text-amber-400">
                                <PenLine size={12} aria-hidden="true" />
                                Can make changes
                            </span>
                        )}
                    </span>
                    {tool.description && (
                        <span className="mt-1 line-clamp-2 text-[12.5px] leading-[1.5] text-muted-foreground wrap-anywhere">
                            {tool.description}
                        </span>
                    )}
                    {tool.changed && (
                        <span className="mt-2 flex items-start gap-1.5 border border-amber-500/40 bg-amber-500/8 px-2.5 py-2 text-[12px] leading-[1.45] text-amber-800 dark:text-amber-300">
                            <TriangleAlert
                                size={13}
                                className="mt-px shrink-0"
                                aria-hidden="true"
                            />
                            {service} changed this tool after you allowed it. It stays off until you
                            tick it and save again.
                        </span>
                    )}
                </span>
            </label>
        </li>
    );
}

/** Tick the tools builds may use, then save. Builds use nothing else. */
export function ToolReview({
    server,
    connections,
}: {
    server: Connection;
    connections: Connections;
}) {
    const approved = server.tools.filter((tool) => tool.approved).map((tool) => tool.name);
    // A refresh or a save brings a new list: start again from what is now allowed.
    const basis = approved.join("\n") + "|" + server.tools.map((tool) => tool.name).join("\n");
    const [held, setHeld] = useState(basis);
    const [picked, setPicked] = useState(() => new Set(approved));
    if (held !== basis) {
        setHeld(basis);
        setPicked(new Set(approved));
    }
    const [saving, setSaving] = useState(false);
    const [checking, setChecking] = useState(false);
    const dirty = picked.size !== approved.length || approved.some((name) => !picked.has(name));
    const all = server.tools.length > 0 && picked.size === server.tools.length;

    function toggle(name: string, on: boolean) {
        const next = new Set(picked);
        if (on) next.add(name);
        else next.delete(name);
        setPicked(next);
    }

    return (
        <div className="overflow-hidden rounded-[12px] border border-border bg-surface-1">
            <div className="flex flex-wrap items-center gap-x-1 gap-y-1 px-4 py-2">
                <p className="mr-auto py-2 text-[12.5px] text-muted-foreground">
                    <span data-numeric="" className="font-mono text-foreground">
                        {picked.size}/{server.tools.length}
                    </span>{" "}
                    ticked
                </p>
                <Button
                    variant="utility"
                    className={UTILITY}
                    disabled={all}
                    onClick={() => setPicked(new Set(server.tools.map((tool) => tool.name)))}
                >
                    Select all
                </Button>
                <Button
                    variant="utility"
                    className={UTILITY}
                    disabled={picked.size === 0}
                    onClick={() => setPicked(new Set())}
                >
                    Clear
                </Button>
                <Button
                    variant="utility"
                    className={UTILITY}
                    disabled={checking}
                    onClick={async () => {
                        setChecking(true);
                        await connections.refresh(server.id);
                        setChecking(false);
                    }}
                >
                    <RefreshCw
                        size={13}
                        aria-hidden="true"
                        className={checking ? "motion-safe:animate-spin" : ""}
                    />
                    {checking ? "Checking" : "Check for new tools"}
                </Button>
            </div>
            {server.tools.length === 0 ? (
                <p className="border-t border-border px-4 py-5 text-[13px] text-muted-foreground">
                    {server.title} has not offered any tools yet. Check again in a moment.
                </p>
            ) : (
                <ul
                    aria-label={`${server.title} tools`}
                    className="grid gap-px border-t border-border bg-border"
                >
                    {server.tools.map((tool) => (
                        <ToolItem
                            key={tool.name}
                            tool={tool}
                            service={server.title}
                            checked={picked.has(tool.name)}
                            onChange={(on) => toggle(tool.name, on)}
                        />
                    ))}
                </ul>
            )}
            <div className="flex min-h-14 flex-wrap items-center justify-end gap-x-3 gap-y-2 border-t border-border bg-background px-4 py-2">
                {dirty ? (
                    <div
                        key="dirty"
                        className={`${styles.ask} flex flex-wrap items-center gap-x-3 gap-y-2`}
                    >
                        <Button
                            variant="secondary"
                            disabled={saving}
                            onClick={() => setPicked(new Set(approved))}
                        >
                            Undo
                        </Button>
                        <Button
                            disabled={saving}
                            onClick={async () => {
                                setSaving(true);
                                await connections.approve(server.id, [...picked]);
                                setSaving(false);
                            }}
                        >
                            <Check size={14} aria-hidden="true" />
                            {saving
                                ? "Saving"
                                : picked.size === 0
                                  ? "Turn off every tool"
                                  : `Allow ${picked.size} ${picked.size === 1 ? "tool" : "tools"}`}
                        </Button>
                    </div>
                ) : (
                    <p
                        key="saved"
                        className={`${styles.ask} flex h-11 items-center gap-1.5 text-[12.5px] text-muted-foreground`}
                    >
                        <Check size={13} aria-hidden="true" />
                        Saved. Builds use only the ticked tools.
                    </p>
                )}
            </div>
        </div>
    );
}
