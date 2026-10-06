"use client";

import { WorkspaceSidebar } from "@/components/layout/WorkspaceSidebar";
import { useProjectsPage } from "@/hooks/projects/useProjectsPage";
import type { ReactNode } from "react";
import { inter } from "./inter";
import styles from "./mcp.module.css";
import type { Badge } from "./serviceEntries";

/**
 * The app sidebar, then the page in a rounded panel set in from the edges, its content in a centred column:
 * shared by the grid, a service's page and the address form.
 */
export function McpShell({ children }: { children: ReactNode }) {
    const { user, signOut } = useProjectsPage();
    return (
        <div className="flex min-h-dvh">
            <WorkspaceSidebar current="connections" userData={user} onSignOut={signOut} />
            <main
                id="main-content"
                className={`${styles.panel} ${inter.className} flex min-w-0 flex-1 bg-surface-1 p-2 pt-[calc(8px+env(safe-area-inset-top))] pb-[calc(8px+env(safe-area-inset-bottom))] text-foreground md:p-4`}
            >
                <div className="min-h-full w-full rounded-[12px] border border-border bg-background px-4 pt-8 pb-12 sm:px-8 md:px-12 md:pt-12">
                    <div className="mx-auto w-full max-w-[896px]">{children}</div>
                </div>
            </main>
        </div>
    );
}

const TONE = {
    ok: "bg-[#22c55e]/10 text-emerald-700 dark:text-[#22c55e]",
    wait: "bg-foreground/7 text-muted-foreground",
    warn: "bg-amber-500/14 text-amber-800 dark:text-amber-300",
} as const;

/** "Connected", "Needs sign-in", "Needs a key" or "Check tools", as a small tinted pill. */
export function StateBadge({ badge }: { badge: NonNullable<Badge> }) {
    return (
        <span
            className={`inline-flex shrink-0 items-center rounded-full px-1.5 py-0.5 text-[12px] leading-4 font-medium whitespace-nowrap ${TONE[badge.tone]}`}
        >
            {badge.text}
        </span>
    );
}
