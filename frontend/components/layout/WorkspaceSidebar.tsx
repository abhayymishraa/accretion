"use client";

import { SidebarAccount } from "@/components/layout/SidebarAccount";
import { SIDEBAR_ROW, SidebarProjects } from "@/components/layout/SidebarProjects";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SIDEBAR_WIDTH, useSidebarLayout, useSidebarResize } from "@/hooks/layout/useSidebarLayout";
import type { UserData } from "@/types/auth.type";
import { LayoutGrid, Plug, Plus, ScrollText, Search } from "lucide-react";
import Link from "next/link";
import { useRef, useState, type CSSProperties } from "react";

// Labels stay readable to screen readers when the sidebar folds to icons.
const LABEL = "min-w-0 truncate group-data-[collapsed=true]/sidebar:sr-only";
// Undoes the Button's centring and focus offset, so its rows match the link rows.
const RAIL_ROW = `${SIDEBAR_ROW} justify-start focus-visible:outline-offset-0 group-data-[collapsed=true]/sidebar:justify-center group-data-[collapsed=true]/sidebar:px-0`;

/** The workspace sidebar; the logo folds it to a strip of icons and back. */
export function WorkspaceSidebar({
    current,
    userData,
    onSignOut,
}: {
    current?: "new" | "projects" | "skills" | "connections";
    userData: UserData | null;
    onSignOut: () => void;
}) {
    const layout = useSidebarLayout();
    const { collapsed, setCollapsed, width } = layout;
    const sidebar = useRef<HTMLElement>(null);
    const resize = useSidebarResize(sidebar, layout);
    const [searching, setSearching] = useState(false);
    const [query, setQuery] = useState("");
    const closeSearch = () => {
        setSearching(false);
        setQuery("");
    };
    return (
        <aside
            ref={sidebar}
            data-collapsed={collapsed}
            style={{ "--sidebar-width": `${width}px` } as CSSProperties}
            className="ember-workspace-sidebar group/sidebar relative flex md:sticky md:top-0 md:h-dvh md:self-start w-(--sidebar-width) shrink-0 flex-col gap-3 overflow-hidden border-r border-r-border bg-background px-3 py-3 [transition:width_200ms_var(--ease-out)] data-[collapsed=true]:w-14 data-[collapsed=true]:px-2 motion-reduce:[transition:none] data-[resizing]:[transition:none] max-md:hidden"
        >
            <Button
                variant={null}
                type="button"
                onClick={() => setCollapsed(!collapsed)}
                aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
                aria-expanded={!collapsed}
                className={`${RAIL_ROW} h-9 gap-2 text-foreground`}
            >
                <svg
                    viewBox="0 0 100 100"
                    width={22}
                    height={22}
                    aria-hidden="true"
                    focusable="false"
                >
                    <use href="/brand/accretion-mark.svg#mark" />
                </svg>
                <span className="font-brand text-[17px] font-semibold tracking-[-0.6px] group-data-[collapsed=true]/sidebar:hidden">
                    accretion
                </span>
            </Button>
            <Link
                href="/chat"
                title="New project"
                className={`${buttonVariants({ variant: "default" })} group-data-[collapsed=true]/sidebar:px-0`}
                aria-current={current === "new" ? "page" : undefined}
            >
                <Plus size={15} />
                <span className={LABEL}>New project</span>
            </Link>
            <nav aria-label="Workspace navigation" className="grid gap-px">
                {searching && !collapsed ? (
                    <Input
                        autoFocus
                        aria-label="Search projects"
                        placeholder="Search projects"
                        value={query}
                        onChange={(event) => setQuery(event.target.value)}
                        onKeyDown={(event) => event.key === "Escape" && closeSearch()}
                        onBlur={() => !query && closeSearch()}
                        className="h-8 rounded-[8px] px-2.5 text-[12.5px] sm:text-[12.5px] pointer-coarse:h-11 pointer-coarse:text-[16px]"
                    />
                ) : (
                    <Button
                        variant={null}
                        type="button"
                        title="Search projects"
                        onClick={() => {
                            setCollapsed(false);
                            setSearching(true);
                        }}
                        className={RAIL_ROW}
                    >
                        <Search size={15} aria-hidden="true" />
                        <span className={LABEL}>Search</span>
                    </Button>
                )}
                <Link
                    href="/projects"
                    title="All projects"
                    aria-current={current === "projects" ? "page" : undefined}
                    className={RAIL_ROW}
                >
                    <LayoutGrid size={15} aria-hidden="true" />
                    <span className={LABEL}>Projects</span>
                </Link>
                <Link
                    href="/skills"
                    title="Skills library"
                    aria-current={current === "skills" ? "page" : undefined}
                    className={RAIL_ROW}
                >
                    <ScrollText size={15} aria-hidden="true" />
                    <span className={LABEL}>Skills</span>
                </Link>
                <Link
                    href="/connectors"
                    title="Connectors"
                    aria-current={current === "connections" ? "page" : undefined}
                    className={RAIL_ROW}
                >
                    <Plug size={15} aria-hidden="true" />
                    <span className={LABEL}>Connectors</span>
                </Link>
            </nav>
            {/* Logo, actions and account stay put; only the lists scroll. */}
            <div className="-mx-1 min-h-0 flex-1 overflow-y-auto overscroll-contain px-1 pt-2 [transition:opacity_150ms_var(--ease-out),visibility_150ms] motion-reduce:[transition:none] group-data-[collapsed=true]/sidebar:invisible group-data-[collapsed=true]/sidebar:opacity-0 group-data-[collapsed=true]/sidebar:overflow-hidden">
                <SidebarProjects query={query} />
            </div>
            <SidebarAccount userData={userData} onSignOut={onSignOut} />
            <div
                role="separator"
                aria-orientation="vertical"
                aria-label="Resize sidebar"
                aria-valuenow={collapsed ? SIDEBAR_WIDTH.rail : width}
                aria-valuemin={SIDEBAR_WIDTH.rail}
                aria-valuemax={SIDEBAR_WIDTH.max}
                tabIndex={0}
                title="Drag to resize. Double-click to reset."
                {...resize}
                className="absolute inset-y-0 right-0 z-10 w-1.5 cursor-col-resize touch-none after:absolute after:inset-y-0 after:right-0 after:w-px after:[transition:background-color_140ms_ease] focus-visible:outline-none focus-visible:after:w-0.5 focus-visible:after:bg-ring group-data-[resizing]/sidebar:after:bg-ring pointer-fine:hover:after:bg-ring"
            />
        </aside>
    );
}
