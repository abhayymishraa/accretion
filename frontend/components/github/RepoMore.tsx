"use client";

import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { type useProjectRepo, useRepoBranches } from "@/hooks/github/useProjectRepo";
import type { ProjectRepo } from "@/types/github.type";
import { ChevronDown, ExternalLink, GitBranch, GitPullRequest } from "lucide-react";
import { useId, useState } from "react";
import { PANEL_LINK } from "./RepoStatus";
import { RemoveRow } from "./RemoveRow";

const LABEL = "text-xs font-semibold";

/** "More": branches, a pull request into the main branch, and unlinking. Folded away until asked for. */
export function RepoMore({
    projectId,
    repo,
    project,
}: {
    projectId: string;
    repo: ProjectRepo;
    project: ReturnType<typeof useProjectRepo>;
}) {
    const id = useId();
    const [open, setOpen] = useState(false);
    const { branches, failed, reload, openPull } = useRepoBranches(projectId, open);
    // Branches listed when the panel first loaded them; one made later unfolds (globals.css [data-row-new]).
    const [listed, setListed] = useState<Set<string> | null>(null);
    if (branches && !listed) setListed(new Set(branches.map((branch) => branch.name)));
    const [name, setName] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const [pull, setPull] = useState("");
    const act = async (work: () => Promise<string>) => {
        setBusy(true);
        const failure = await work();
        setError(failure);
        setBusy(false);
        if (!failure) void reload();
        return failure;
    };

    return (
        <details
            // Height opens on the chevron's 260ms (globals.css details[data-faq]).
            data-faq=""
            className="group border-t border-border"
            onToggle={(event) => setOpen(event.currentTarget.open)}
        >
            <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-ring [&::-webkit-details-marker]:hidden">
                More
                <ChevronDown
                    size={14}
                    aria-hidden="true"
                    className="ml-auto text-muted-foreground transition-transform duration-[260ms] ease-[var(--ease-out)] group-open:rotate-180 motion-reduce:transition-none"
                />
            </summary>
            <div className="grid gap-4 pb-2">
                <section aria-label="Branches" className="grid gap-1.5">
                    <h3 className={LABEL}>Branches</h3>
                    {failed ? (
                        <ErrorBox message="Couldn't list the branches." className="text-xs" />
                    ) : !branches ? (
                        <Skeleton className="h-20 rounded-[10px]" />
                    ) : (
                        <ul
                            // Mounts only once "More" opens; fades in over the skeleton (globals.css [data-loaded-in]).
                            data-loaded-in=""
                            className="grid gap-px overflow-hidden rounded-[10px] border border-border bg-border"
                        >
                            {branches.map((branch) => (
                                <li
                                    key={branch.name}
                                    data-row=""
                                    data-row-new={
                                        listed && !listed.has(branch.name) ? "" : undefined
                                    }
                                    className="bg-surface-1"
                                >
                                    <div className="flex min-h-11 items-center gap-2 pr-1 pl-3">
                                        <GitBranch
                                            size={13}
                                            aria-hidden="true"
                                            className="shrink-0 text-muted-foreground"
                                        />
                                        <span className="min-w-0 flex-1 truncate font-mono text-xs">
                                            {branch.name}
                                        </span>
                                        {branch.current ? (
                                            <span className="px-2 text-[11px] text-muted-foreground">
                                                Current
                                            </span>
                                        ) : (
                                            <Button
                                                variant="utility"
                                                disabled={busy}
                                                onClick={() =>
                                                    act(() => project.switchBranch(branch.name))
                                                }
                                            >
                                                Switch
                                            </Button>
                                        )}
                                    </div>
                                </li>
                            ))}
                        </ul>
                    )}
                    <p className="text-xs leading-[1.5] text-muted-foreground">
                        Switching loads that branch here. Changes not yet saved to GitHub go to a
                        pull request first.
                    </p>
                    <form
                        className="flex flex-wrap gap-2"
                        onSubmit={async (event) => {
                            event.preventDefault();
                            if (!name.trim()) return setError("Give the branch a name.");
                            if (!(await act(() => project.createBranch(name.trim())))) setName("");
                        }}
                    >
                        <label htmlFor={id} className="sr-only">
                            New branch name
                        </label>
                        <Input
                            id={id}
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                            placeholder="New branch name"
                            autoComplete="off"
                            spellCheck={false}
                            maxLength={255}
                            className="h-9 min-w-0 flex-1 basis-[160px] font-mono pointer-coarse:h-11 sm:text-[13px]"
                        />
                        <Button
                            type="submit"
                            variant="secondary"
                            disabled={busy}
                            className="max-sm:w-full"
                        >
                            Make branch
                        </Button>
                    </form>
                </section>
                {repo.branch !== repo.default_branch && (
                    <section aria-label="Pull request" className="grid gap-1.5">
                        <h3 className={LABEL}>Pull request</h3>
                        <p className="text-xs leading-[1.5] text-muted-foreground">
                            Ask to bring {repo.branch} into {repo.default_branch}.
                        </p>
                        {pull ? (
                            <a href={pull} target="_blank" rel="noreferrer" className={PANEL_LINK}>
                                Open the pull request
                                <ExternalLink size={13} aria-hidden="true" />
                            </a>
                        ) : (
                            <Button
                                variant="secondary"
                                disabled={busy}
                                className="justify-self-start max-sm:w-full"
                                onClick={async () => {
                                    setBusy(true);
                                    const made = await openPull();
                                    setBusy(false);
                                    if ("url" in made) setPull(made.url);
                                    else setError(made.error);
                                }}
                            >
                                <GitPullRequest size={14} aria-hidden="true" />
                                Make a pull request
                            </Button>
                        )}
                    </section>
                )}
                <ErrorBox message={error} className="text-xs" />
                <RemoveRow
                    note="Stop saving this project to GitHub. The repository stays."
                    label="Unlink"
                    question={`Unlink ${repo.name}? This project stops saving to it.`}
                    onConfirm={project.unlink}
                />
            </div>
        </details>
    );
}
