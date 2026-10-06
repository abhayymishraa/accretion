"use client";

import { SkillSwitch } from "@/components/skills/SkillSwitch";
import type { ProjectConnection } from "@/types/connection.type";
import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import type { CSSProperties } from "react";
import styles from "./mcp.module.css";
import { ServiceLogo } from "./ServiceLogo";

export type ConnectorState = "live" | "off" | "attention";

/** Where a connector stands in this project: used here, turned off here, or waiting on the user. */
export function stateOf(item: ProjectConnection): ConnectorState {
    if (!item.connected || !item.account_enabled) return "attention";
    return item.enabled ? "live" : "off";
}

// A status in the switch's place that leads to the service's page.
const GO =
    "inline-flex min-h-8 shrink-0 items-center gap-1 rounded-[6px] border border-border bg-surface-2 px-2.5 text-[11.5px] text-foreground [transition:background-color_130ms_ease,scale_100ms_var(--ease-out)] active:scale-[0.97] motion-reduce:active:scale-100 focus-visible:outline-2 focus-visible:outline-ring pointer-coarse:min-h-11 pointer-fine:hover:bg-surface-3";

function Control({
    item,
    state,
    onChange,
}: {
    item: ProjectConnection;
    state: ConnectorState;
    onChange: (on: boolean) => void;
}) {
    if (state === "attention")
        return (
            <Link href={`/connectors/${item.name}`} className={GO}>
                {item.connected ? "Turn on" : "Sign in"}
                <ArrowUpRight size={12} aria-hidden="true" className="text-muted-foreground" />
            </Link>
        );
    return (
        <SkillSwitch
            checked={item.enabled}
            label={`Use ${item.title} in this project`}
            onChange={onChange}
        />
    );
}

/** One connector: its logo, name and tools, and the control that fits its state. */
export function ConnectorRow({
    item,
    index,
    onChange,
}: {
    item: ProjectConnection;
    index: number;
    onChange: (on: boolean) => void;
}) {
    const state = stateOf(item);
    return (
        <li
            className={`${styles.cascade} flex items-center gap-3 bg-surface-1 px-3 py-3 [transition:background-color_130ms_ease] pointer-fine:hover:bg-surface-2`}
            style={{ "--i": Math.min(index, 8) } as CSSProperties}
        >
            <div
                className={`flex min-w-0 flex-1 items-start gap-3 [transition:opacity_150ms_ease] ${state === "off" ? "opacity-55" : ""}`}
            >
                <ServiceLogo id={item.name} icon={item.icon} />
                <div className="min-w-0 flex-1">
                    <div className="flex min-w-0 items-center gap-2">
                        <p className="truncate text-[13px] font-medium text-foreground">
                            {item.title}
                        </p>
                        <span
                            data-numeric=""
                            className="shrink-0 font-mono text-[10px] tracking-[0.08em] text-muted-foreground uppercase tabular-nums"
                        >
                            [{String(item.tool_count).padStart(2, "0")}]{" "}
                            {item.tool_count === 1 ? "tool" : "tools"}
                        </span>
                    </div>
                    {/* Only a row that waits on the user says so; the switch shows on and off. */}
                    {state === "attention" && (
                        <p className="mt-1 flex items-center gap-1.5 font-mono text-[10px] tracking-[0.08em] text-muted-foreground uppercase">
                            <span
                                aria-hidden="true"
                                className="size-1.5 rounded-full bg-amber-500"
                            />
                            Needs you
                            <span className="normal-case tracking-normal">
                                ·{" "}
                                {item.connected ? "Off in your account" : "Sign in to use it here"}
                            </span>
                        </p>
                    )}
                    {item.description && (
                        <p className="mt-1.5 line-clamp-2 text-[12px] leading-[1.5] text-muted-foreground">
                            {item.description}
                        </p>
                    )}
                </div>
            </div>
            <Control item={item} state={state} onChange={onChange} />
        </li>
    );
}
