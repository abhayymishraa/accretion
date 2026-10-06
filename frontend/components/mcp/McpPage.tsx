"use client";

import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Skeleton } from "@/components/ui/skeleton";
import { useConnections } from "@/hooks/connections/useConnections";
import Link from "next/link";
import type { CSSProperties } from "react";
import styles from "./mcp.module.css";
import { McpShell, StateBadge } from "./McpShell";
import { badge, type ServiceEntry, serviceEntries } from "./serviceEntries";
import { ServiceLogo } from "./ServiceLogo";

const GRID = "grid gap-2 sm:grid-cols-2 lg:grid-cols-3";
// The whole card is the link: one target, at least 44px tall, that dips a little on press.
const CARD =
    "group flex min-h-[82px] gap-3 rounded-[12px] border p-3 no-underline [transition:background-color_140ms_ease,border-color_140ms_ease,scale_120ms_var(--ease-out)] active:scale-[0.99] motion-reduce:active:scale-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring h-full border-border bg-surface-1 pointer-fine:hover:border-input pointer-fine:hover:bg-surface-2";

// Each cell's place in the entrance; cells past the eighth arrive with it.
const slot = (index: number) => ({ "--i": Math.min(index, 8) }) as CSSProperties;

function Card({ entry, index }: { entry: ServiceEntry; index: number }) {
    const state = badge(entry);
    return (
        <li className={`${styles.cascade} min-w-0`} style={slot(index)}>
            <Link href={`/connectors/${encodeURIComponent(entry.key)}`} className={CARD}>
                <ServiceLogo id={entry.logo} icon={entry.server?.icon} />
                <span className="min-w-0 flex-1">
                    <span className="flex min-w-0 items-center gap-2">
                        <span className="truncate text-[14px] leading-5 font-medium text-foreground">
                            {entry.title}
                        </span>
                        {state && <StateBadge badge={state} />}
                    </span>
                    <span className="mt-0.5 line-clamp-2 text-[12px] leading-4 text-foreground/85">
                        {entry.description}
                    </span>
                </span>
            </Link>
        </li>
    );
}

/** The first cell: any other service, by the web address its maker gives. */
function AddCard() {
    return (
        <li className={`${styles.cascade} min-w-0`}>
            <Link href="/connectors/new" className={`${CARD} border-dashed`}>
                <ServiceLogo id="add" />
                <span className="min-w-0 flex-1">
                    <span className="block text-[14px] leading-5 font-medium text-foreground">
                        Custom service
                    </span>
                    <span className="mt-0.5 line-clamp-2 text-[12px] leading-4 text-foreground/85">
                        Connect any other service by the web address its maker gives you.
                    </span>
                </span>
            </Link>
        </li>
    );
}

/** Loading shape: the same cards, a logo tile and two lines of text each. */
function GridSkeleton() {
    return (
        <ul className={GRID} aria-hidden="true">
            {Array.from({ length: 9 }, (_, index) => (
                <li
                    key={index}
                    className="flex min-h-[82px] gap-3 rounded-[12px] border border-border p-3"
                >
                    <Skeleton className="size-10 rounded-[8px]" />
                    <div className="flex flex-1 flex-col gap-2 pt-0.5">
                        <Skeleton className="h-4 w-24" />
                        <Skeleton className="h-3 w-full" />
                        <Skeleton className="h-3 w-3/5" />
                    </div>
                </li>
            ))}
        </ul>
    );
}

/** Connectors: every service a build can use, as one grid of cards. */
export default function McpPage() {
    const { servers, catalog, error, retry } = useConnections();
    const entries = servers && catalog ? serviceEntries(catalog, servers) : null;
    return (
        <McpShell>
            <header className={`${styles.rise} mb-6`}>
                <h1 className="text-[18px] leading-7 font-semibold">Connectors</h1>
                <p className="mt-3 text-[14px] leading-5 text-foreground/95">
                    Choose a ready service or add your own. Your builds use only the tools you
                    allow.
                </p>
            </header>
            {error ? (
                <ErrorBox message={error}>
                    <Button
                        variant="utility"
                        className="h-8 px-2 text-destructive underline"
                        onClick={() => void retry()}
                    >
                        Try again
                    </Button>
                </ErrorBox>
            ) : entries === null ? (
                <GridSkeleton />
            ) : (
                <ul className={GRID} aria-label="Services">
                    <AddCard />
                    {entries.map((entry, index) => (
                        <Card key={entry.key} entry={entry} index={index + 1} />
                    ))}
                </ul>
            )}
        </McpShell>
    );
}
