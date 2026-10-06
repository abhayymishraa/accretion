"use client";

import { SkillSearch } from "@/components/skills/SkillFilters";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Skeleton } from "@/components/ui/skeleton";
import { useProjectConnections } from "@/hooks/connections/useProjectConnections";
import type { ProjectConnection } from "@/types/connection.type";
import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ConnectorRow, type ConnectorState, stateOf } from "./ConnectorRow";
import { Board } from "./Board";

// The toolbar's way out, the same control as the Skills tab's "Library".
const MANAGE =
    "inline-flex h-8 shrink-0 items-center gap-1.5 rounded-[6px] border border-border bg-surface-2 px-3 text-[12.5px] text-foreground shadow-xs [transition:background-color_130ms_ease,scale_100ms_var(--ease-out)] active:scale-[0.97] motion-reduce:active:scale-100 focus-visible:outline-2 focus-visible:outline-ring pointer-coarse:h-11 pointer-fine:hover:bg-surface-3";
const LABEL = "font-mono text-[10px] tracking-[0.12em] text-muted-foreground uppercase";

// The read-out's counts. The list groups only by what the user must act on, so a row never jumps away
// when its switch flips between live and off.
const COUNTS: { state: ConnectorState; label: string }[] = [
    { state: "live", label: "Live" },
    { state: "off", label: "Off" },
    { state: "attention", label: "Needs you" },
];
const GROUPS = [
    {
        title: "Connected services",
        test: (state: ConnectorState) => state !== "attention",
    },
    {
        title: "Needs you",
        test: (state: ConnectorState) => state === "attention",
    },
];

/** Three counts in a hairline grid, the board's read-out of the project at a glance. */
function Readout({ connections }: { connections: ProjectConnection[] }) {
    const count = (state: ConnectorState) =>
        connections.filter((item) => stateOf(item) === state).length;
    return (
        <dl className="mt-4 grid grid-cols-3 gap-px overflow-hidden rounded-[8px] border border-border bg-border">
            {COUNTS.map(({ state, label }) => (
                <div key={state} className="bg-surface-1 px-3 py-2.5">
                    <dt className={LABEL}>{label}</dt>
                    <dd
                        data-numeric=""
                        className={`mt-1 text-[22px] leading-none font-semibold tabular-nums ${state === "live" ? "text-foreground" : "text-muted-foreground"}`}
                    >
                        {String(count(state)).padStart(2, "0")}
                    </dd>
                </div>
            ))}
        </dl>
    );
}

/** No connector yet: what one is, and the way to add the first. */
function Empty() {
    return (
        <div className="grid place-items-center px-6 pt-6 pb-10 text-center">
            <Board
                states={["attention"]}
                label="A patch panel with one empty port, waiting for a cable."
                className="w-[160px]"
            />
            <p className="mt-1 text-[13px] font-medium text-foreground">No connectors yet</p>
            <p className="mt-1 max-w-[36ch] text-xs leading-[1.5] text-muted-foreground">
                Connect services like Notion, Linear or GitHub to give your builds extra tools.
            </p>
            <Link href="/connectors" className={`${MANAGE} mt-4`}>
                Add a connector
                <ArrowUpRight size={13} aria-hidden="true" className="text-muted-foreground" />
            </Link>
        </div>
    );
}

/** The workspace's Connectors tab: a read-out of the project, then each service by its state. */
export function ProjectConnections({ projectId }: { projectId: string }) {
    const { connections, ensureLoaded, setEnabled, failed, retry } =
        useProjectConnections(projectId);
    const [query, setQuery] = useState("");
    // Fetched the first time the tab opens, as the "/" menu does.
    useEffect(() => {
        ensureLoaded();
    }, [ensureLoaded]);
    const needle = query.trim().toLowerCase();
    const shown = (connections ?? []).filter((item) =>
        `${item.name} ${item.title} ${item.description}`.toLowerCase().includes(needle),
    );

    return (
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-surface-1">
            <header className="relative overflow-hidden border-b border-border px-4 pt-3 pb-4">
                <div className="flex items-start gap-4">
                    <div className="min-w-0 flex-1">
                        <p className={LABEL}>Workspace / Connectors</p>
                        <h2 className="mt-1.5 text-sm font-semibold text-foreground">
                            Connectors in this project
                        </h2>
                        <p className="mt-1 max-w-[52ch] text-xs leading-[1.5] text-pretty text-muted-foreground">
                            Choose which connected services Accretion can use here. A connector you
                            turn off is never used in this project, even with /name.
                        </p>
                    </div>
                    {/* One port per connector: the board is the project's state, drawn. */}
                    <Board
                        states={connections?.length ? connections.map(stateOf) : ["attention"]}
                        label="A patch panel with one port for each connector in this project."
                        className="w-[132px] shrink-0"
                    />
                </div>
                {connections && connections.length > 0 && <Readout connections={connections} />}
                <div className="mt-3 flex items-center gap-2">
                    <SkillSearch
                        value={query}
                        onChange={setQuery}
                        label="Search connectors"
                        className="h-8 rounded-[6px] text-[12.5px]"
                    />
                    <Link href="/connectors" className={MANAGE}>
                        Manage
                        <ArrowUpRight
                            size={13}
                            aria-hidden="true"
                            className="text-muted-foreground"
                        />
                    </Link>
                </div>
            </header>
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 pb-[calc(16px+env(safe-area-inset-bottom))]">
                {failed && !connections ? (
                    <div className="pt-4">
                        <ErrorBox message="Could not load your connectors.">
                            <button
                                type="button"
                                onClick={() => void retry()}
                                className="cursor-pointer rounded-[4px] underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-ring pointer-coarse:min-h-11"
                            >
                                Try again
                            </button>
                        </ErrorBox>
                    </div>
                ) : !connections ? (
                    <div className="flex flex-col gap-1.5 pt-4" aria-label="Loading connectors">
                        {[0, 1, 2].map((row) => (
                            <Skeleton key={row} className="h-16 rounded-[8px]" />
                        ))}
                    </div>
                ) : !connections.length ? (
                    <Empty />
                ) : !shown.length ? (
                    <p className="py-6 text-xs text-muted-foreground">
                        No connectors match &ldquo;{query.trim()}&rdquo;.
                    </p>
                ) : (
                    GROUPS.map(({ title, test }) => {
                        const items = shown.filter((item) => test(stateOf(item)));
                        if (!items.length) return null;
                        return (
                            <section key={title} aria-label={title} className="pt-4">
                                <h3 className={`${LABEL} flex items-center gap-2 pb-2`}>
                                    {title}
                                    <span data-numeric="" className="tabular-nums">
                                        [{String(items.length).padStart(2, "0")}]
                                    </span>
                                    <span aria-hidden="true" className="h-px flex-1 bg-border" />
                                </h3>
                                <ul className="grid gap-px overflow-hidden rounded-[8px] border border-border bg-border">
                                    {items.map((item, index) => (
                                        <ConnectorRow
                                            key={item.name}
                                            item={item}
                                            index={index}
                                            onChange={(next) => setEnabled(item.name, next)}
                                        />
                                    ))}
                                </ul>
                            </section>
                        );
                    })
                )}
            </div>
        </div>
    );
}
