"use client";

import { ProjectDeleteDialog } from "./ProjectDeleteDialog";

import { useProjectCollection } from "@/hooks/projects/useProjectCollection";

import { ProjectCollectionSkeleton } from "@/components/projects/ProjectCollectionSkeleton";
import styles from "@/components/projects/project-shelf.module.css";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { type ProjectPeriod, type ProjectSort } from "@/lib/projects/filters";
import { ArrowUpRight, ChevronDown, FolderOpen, Search, Trash2 } from "lucide-react";
import Link from "next/link";

function createdLabel(value: string) {
    const date = new Date(value);
    return Number.isFinite(date.getTime())
        ? date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
        : "Date unavailable";
}

export function ProjectCollection({
    compact = false,
    onOpen,
}: {
    compact?: boolean;
    onOpen?: () => void;
}) {
    const {
        id,
        searchRef,
        deleteTrigger,
        projects,
        loading,
        error,
        query,
        setQuery,
        sort,
        setSort,
        period,
        setPeriod,
        setAttempt,
        setLoading,
        setError,
        pendingDelete,
        setPendingDelete,
        deleteTitle,
        setDeleteTitle,
        dialogMotion,
        setDialogMotion,
        deletingId,
        deleteError,
        setDeleteError,
        moveSpotlight,
        deleteProject,
        visible,
        narrowed,
        changed,
        resetFilters,
    } = useProjectCollection(compact, onOpen);

    return (
        <div>
            <div
                className={`mb-4 grid gap-4 ${compact ? "" : "sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_10rem_12rem] lg:items-end"}`}
            >
                <div className={compact ? "" : "min-w-0 sm:col-span-2 lg:col-span-1"}>
                    <label
                        htmlFor={`${id}-search`}
                        className="mb-2 block text-xs text-muted-foreground"
                    >
                        Search projects
                    </label>
                    <div className="relative">
                        <Search
                            size={16}
                            aria-hidden="true"
                            className="pointer-events-none absolute left-3 top-3.5 text-muted-foreground"
                        />
                        <Input
                            id={`${id}-search`}
                            ref={searchRef}
                            type="search"
                            placeholder="Find a project by name"
                            value={query}
                            onChange={(event) => setQuery(event.target.value)}
                            className="pl-9"
                        />
                    </div>
                </div>
                {!compact && (
                    <>
                        <label className="min-w-0 text-xs text-muted-foreground">
                            <span className="mb-2 block">Created</span>
                            <div className="relative">
                                <select
                                    aria-label="Filter by creation date"
                                    value={period}
                                    onChange={(event) =>
                                        setPeriod(event.target.value as ProjectPeriod)
                                    }
                                    className="h-11 w-full appearance-none rounded-[8px] border border-input bg-card py-2 pl-3 pr-10 text-base text-foreground shadow-xs outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]"
                                >
                                    <option value="all">All time</option>
                                    <option value="7">Last 7 days</option>
                                    <option value="30">Last 30 days</option>
                                </select>
                                <ChevronDown
                                    size={16}
                                    aria-hidden="true"
                                    className="pointer-events-none absolute right-3 top-3.5 text-muted-foreground"
                                />
                            </div>
                        </label>
                        <label className="min-w-0 text-xs text-muted-foreground">
                            <span className="mb-2 block">Sort by</span>
                            <div className="relative">
                                <select
                                    aria-label="Sort projects"
                                    value={sort}
                                    onChange={(event) => setSort(event.target.value as ProjectSort)}
                                    className="h-11 w-full appearance-none rounded-[8px] border border-input bg-card py-2 pl-3 pr-10 text-base text-foreground shadow-xs outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]"
                                >
                                    <option value="recent">Recently updated</option>
                                    <option value="newest">Newest created</option>
                                    <option value="oldest">Oldest created</option>
                                    <option value="name-asc">Name A–Z</option>
                                    <option value="name-desc">Name Z–A</option>
                                </select>
                                <ChevronDown
                                    size={16}
                                    aria-hidden="true"
                                    className="pointer-events-none absolute right-3 top-3.5 text-muted-foreground"
                                />
                            </div>
                        </label>
                    </>
                )}
            </div>
            {!loading && !error && (
                <div className="mb-5 flex min-h-11 items-center justify-between gap-3">
                    <p role="status" className="text-xs text-muted-foreground">
                        {narrowed
                            ? `${visible.length} of ${projects.length} projects`
                            : `${projects.length} ${projects.length === 1 ? "project" : "projects"}`}
                    </p>
                    {changed && (
                        <Button variant="utility" onClick={resetFilters}>
                            Reset filters
                        </Button>
                    )}
                </div>
            )}
            {loading ? (
                <ProjectCollectionSkeleton compact={compact} />
            ) : error ? (
                <div className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-border px-6 py-16 text-center text-muted-foreground">
                    <p role="alert">{error}</p>
                    <Button
                        variant="secondary"
                        onClick={() => {
                            setLoading(true);
                            setError("");
                            setAttempt((value) => value + 1);
                        }}
                    >
                        Try again
                    </Button>
                </div>
            ) : !visible.length ? (
                <div className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-border px-6 py-16 text-center text-muted-foreground">
                    <FolderOpen size={30} aria-hidden="true" />
                    <h2 className="text-xl text-foreground">
                        {projects.length
                            ? "No matching projects."
                            : "A blank canvas, just for you."}
                    </h2>
                    <p className="max-w-92 text-sm">
                        {projects.length
                            ? "Try another name or a different creation period."
                            : "Start with an idea. Your projects will be waiting here."}
                    </p>
                    {projects.length ? (
                        <Button variant="secondary" onClick={resetFilters}>
                            Clear filters
                        </Button>
                    ) : (
                        <Link
                            href="/chat"
                            className={buttonVariants({ variant: "default" })}
                            onClick={onOpen}
                        >
                            Start a project <ArrowUpRight size={15} />
                        </Link>
                    )}
                </div>
            ) : (
                <div
                    aria-label="Your projects"
                    className={
                        compact
                            ? "flex flex-col gap-3"
                            : "grid grid-cols-1 gap-x-9 gap-y-10 px-1 pb-3 md:grid-cols-2"
                    }
                >
                    {visible.map((project) => (
                        <article
                            key={project.id}
                            className={`${styles.cardEnter} flex min-w-0 flex-col ${compact ? "rounded-xl border border-border bg-card" : "h-full"}`}
                        >
                            <div
                                className={`relative isolate flex min-w-0 flex-1 ${compact ? "" : styles.card}`}
                            >
                                {!compact && (
                                    <div
                                        aria-hidden="true"
                                        className="pointer-events-none absolute inset-0 -z-10 -translate-x-0.5 translate-y-1.5 rounded-[24px] border border-foreground/25 bg-surface-2"
                                    />
                                )}
                                <Link
                                    href={`/chat/${project.id}`}
                                    onClick={onOpen}
                                    onPointerEnter={compact ? undefined : moveSpotlight}
                                    onPointerMove={compact ? undefined : moveSpotlight}
                                    className={`relative isolate flex min-w-0 flex-1 flex-col text-foreground no-underline focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-4 ${compact ? "gap-3 rounded-xl p-4" : `${styles.paper} min-h-72 rounded-[24px] border border-foreground/55 bg-card p-6 sm:p-8`}`}
                                >
                                    {!compact && (
                                        <div className="flex items-center justify-between gap-3 text-accent-foreground">
                                            <span className="font-mono text-xs uppercase tracking-widest">
                                                Project
                                            </span>
                                            <ArrowUpRight
                                                size={22}
                                                strokeWidth={1.5}
                                                aria-hidden="true"
                                            />
                                        </div>
                                    )}
                                    <h2
                                        className={`wrap-anywhere ${compact ? "text-base font-medium" : "flex-1 py-8 font-mono text-[clamp(24px,2.4vw,30px)] font-medium leading-[1.25] tracking-[-.04em]"}`}
                                    >
                                        {project.title}
                                    </h2>
                                    <span
                                        className={`flex items-center gap-2 text-muted-foreground ${compact ? "text-xs" : "font-mono text-xs uppercase tracking-wide"}`}
                                    >
                                        <span aria-hidden="true" className="text-accent-foreground">
                                            &gt;
                                        </span>{" "}
                                        Open workspace
                                    </span>
                                </Link>
                            </div>
                            <div
                                className={`flex min-h-12 items-center justify-between gap-2 px-2 ${compact ? "" : "mt-2"}`}
                            >
                                <p className="text-xs text-muted-foreground">
                                    Created {createdLabel(project.created_at)}
                                </p>
                                <Button
                                    variant="utility"
                                    aria-label={`Delete ${project.title}`}
                                    disabled={deletingId !== null}
                                    onClick={(event) => {
                                        deleteTrigger.current = event.currentTarget;
                                        setDeleteError("");
                                        setDeleteTitle(project.title);
                                        setDialogMotion(event.detail > 0 ? "open" : null);
                                        setPendingDelete(project);
                                    }}
                                    className="shrink-0 px-2"
                                >
                                    <Trash2 size={14} aria-hidden="true" />
                                    <span className={compact ? "" : "sr-only"}>Delete</span>
                                </Button>
                            </div>
                        </article>
                    ))}
                </div>
            )}
            <ProjectDeleteDialog
                open={pendingDelete !== null}
                deleting={deletingId !== null}
                title={deleteTitle}
                error={deleteError}
                dialogMotion={dialogMotion}
                setDialogMotion={setDialogMotion}
                onClose={() => setPendingDelete(null)}
                onConfirm={deleteProject}
                onRestoreFocus={() =>
                    (deleteTrigger.current?.isConnected
                        ? deleteTrigger.current
                        : searchRef.current
                    )?.focus()
                }
            />
        </div>
    );
}
