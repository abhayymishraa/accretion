"use client";

import { SkillSearch } from "@/components/skills/SkillFilters";
import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Skeleton } from "@/components/ui/skeleton";
import type { useGithubAccount } from "@/hooks/github/useGithubAccount";
import { Lock } from "lucide-react";
import { useState } from "react";

const DAY = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" });

/** The repositories Accretion can reach, each one a tap away from being a new project. */
export function ImportList({ github }: { github: ReturnType<typeof useGithubAccount> }) {
    const { repos } = github;
    const [query, setQuery] = useState("");
    // One import at a time: it opens the new project when done.
    const [busy, setBusy] = useState<number | null>(null);
    const [error, setError] = useState<{ id: number; text: string } | null>(null);
    const needle = query.trim().toLowerCase();
    const shown = (repos ?? []).filter((repo) => repo.full_name.toLowerCase().includes(needle));

    return (
        <section aria-label="Bring in a repository" className="mt-10">
            <h2 className="text-[14px] leading-5 font-semibold">Bring in a repository</h2>
            <p className="mt-1 mb-3 text-[13px] leading-5 text-muted-foreground">
                It becomes a new project that saves back to the same repository.
            </p>
            {github.reposError ? (
                <ErrorBox message={github.reposError} onRetry={() => void github.retryRepos()} />
            ) : !repos ? (
                <div className="grid gap-1.5" aria-label="Loading repositories" aria-busy="true">
                    {[0, 1, 2].map((row) => (
                        <Skeleton key={row} className="h-14 rounded-[10px]" />
                    ))}
                </div>
            ) : !repos.length ? (
                <p
                    data-loaded-in=""
                    className="rounded-[12px] border border-border bg-surface-1 px-4 py-6 text-center text-[13px] text-muted-foreground"
                >
                    No repositories yet. Choose some on GitHub, then come back.
                </p>
            ) : (
                // Fades in over the skeleton it replaces (globals.css [data-loaded-in]).
                <div data-loaded-in="">
                    <div className="mb-2 flex">
                        <SkillSearch
                            value={query}
                            onChange={setQuery}
                            label="Search repositories"
                            className="h-9 rounded-[8px] text-[13px] sm:text-[13px]"
                        />
                    </div>
                    <ul className="grid gap-px overflow-hidden rounded-[12px] border border-border bg-border">
                        {shown.map((repo) => (
                            <li key={repo.id} className="bg-surface-1 px-3 py-2.5">
                                <div className="flex min-h-11 items-center gap-3">
                                    <div className="min-w-0 flex-1">
                                        <p className="flex items-center gap-1.5 text-[14px] leading-5 font-medium">
                                            <span className="truncate">{repo.full_name}</span>
                                            {repo.private && (
                                                <Lock
                                                    size={12}
                                                    aria-label="Private"
                                                    className="shrink-0 text-muted-foreground"
                                                />
                                            )}
                                        </p>
                                        {repo.updated_at && (
                                            <p className="text-[12px] leading-4 text-muted-foreground">
                                                Updated {DAY.format(new Date(repo.updated_at))}
                                            </p>
                                        )}
                                    </div>
                                    <Button
                                        variant="secondary"
                                        disabled={busy !== null}
                                        onClick={async () => {
                                            setBusy(repo.id);
                                            setError(null);
                                            const failure = await github.importRepo(repo.id);
                                            // Imported: the new project is opening, so the button stays pressed.
                                            if (failure) {
                                                setBusy(null);
                                                setError({ id: repo.id, text: failure });
                                            }
                                        }}
                                    >
                                        {busy === repo.id ? "Bringing in…" : "Bring in"}
                                    </Button>
                                </div>
                                <ErrorBox
                                    message={error?.id === repo.id ? error.text : ""}
                                    className="mt-1 rounded-none border-0 bg-transparent p-0 text-[12.5px]"
                                />
                            </li>
                        ))}
                        {!shown.length && (
                            <li className="bg-surface-1 px-3 py-5 text-[13px] text-muted-foreground">
                                No repositories match &ldquo;{query.trim()}&rdquo;.
                            </li>
                        )}
                    </ul>
                </div>
            )}
        </section>
    );
}
