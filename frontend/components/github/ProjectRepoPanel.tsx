"use client";

import { Button, buttonVariants } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { repoBusy, useProjectRepo } from "@/hooks/github/useProjectRepo";
import { ExternalLink, RefreshCw } from "lucide-react";
import Link from "next/link";
import { type ReactNode, useId, useState } from "react";
import { SiGithub } from "react-icons/si";
import { mount } from "./hairline/dock.js";
import { HairlineMark } from "./HairlineMark";
import { RepoMore } from "./RepoMore";
import { PANEL_LINK, StatusLine } from "./RepoStatus";
import { WorkspaceTabPanel } from "@/components/chat/WorkspaceTabPanel";

/** The first save: a name for the new private repository, or the project's own. */
function SaveForm({ create }: { create: (name?: string) => Promise<string> }) {
    const id = useId();
    const [name, setName] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    return (
        <form
            className="grid gap-2"
            onSubmit={async (event) => {
                event.preventDefault();
                setBusy(true);
                setError(await create(name.trim() || undefined));
                setBusy(false);
            }}
        >
            <label htmlFor={id} className="text-xs text-muted-foreground">
                Repository name (optional)
            </label>
            <div className="flex flex-wrap gap-2">
                <Input
                    id={id}
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="Uses the project's name"
                    autoComplete="off"
                    spellCheck={false}
                    maxLength={100}
                    className="h-9 min-w-0 flex-1 basis-[180px] pointer-coarse:h-11"
                />
                <Button type="submit" disabled={busy} className="max-sm:w-full">
                    <SiGithub size={14} aria-hidden="true" />
                    {busy ? "Saving…" : "Save to GitHub"}
                </Button>
            </div>
            <p className="text-xs leading-[1.5] text-muted-foreground">
                A new private repository. Every change you make here is saved to it.
            </p>
            <ErrorBox message={error} className="text-xs" />
        </form>
    );
}

/** The workspace's GitHub tab: save the project to a repository, see its status, and act on it. */
export function ProjectRepoPanel({ projectId }: { projectId: string }) {
    const project = useProjectRepo(projectId);
    const { repo, account } = project;
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    const act = async (work: () => Promise<string>) => {
        setBusy(true);
        setError(await work());
        setBusy(false);
    };
    const files = repo?.detail.files ?? [];
    // The linked view fades in only right after the first save, never each time the tab opens.
    const [formShown, setFormShown] = useState(false);
    if (repo && !repo.linked && !formShown) setFormShown(true);

    let body: ReactNode;
    // A linked repository shows without the account; only the first save needs it.
    if (project.failed && (!repo || (!repo.linked && !account)))
        body = (
            <ErrorBox
                message="Couldn't load this project's GitHub status."
                onRetry={() => void project.retry()}
            />
        );
    else if (!repo || (!repo.linked && !account))
        body = <Skeleton className="h-24 rounded-[10px]" aria-label="Loading" />;
    else if (!repo.linked && !account?.configured)
        body = (
            <p className="text-xs text-muted-foreground">
                Saving to GitHub is not available here yet.
            </p>
        );
    else if (!repo.linked && !(account?.connected && account.installed))
        body = (
            <div className="grid justify-items-center pb-4 text-center">
                <HairlineMark
                    mount={mount}
                    label="The GitHub mark as a coin, hovering over its slot."
                    className="w-[150px]"
                />
                <h3 className="text-[13px] font-semibold">Not saved to GitHub</h3>
                <p className="mt-0.5 max-w-[36ch] text-xs leading-[1.5] text-muted-foreground">
                    Connect GitHub once, then save this project to its own repository.
                </p>
                <Link
                    href="/integrations/github"
                    className={`${buttonVariants({ variant: "secondary" })} mt-4`}
                >
                    Connect GitHub
                </Link>
            </div>
        );
    else if (!repo.linked) body = <SaveForm create={project.create} />;
    else
        body = (
            <div data-loaded-in={formShown ? "" : undefined} className="grid gap-3">
                <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
                    <a
                        href={repo.url ?? undefined}
                        target="_blank"
                        rel="noreferrer"
                        className={`${PANEL_LINK} min-w-0`}
                    >
                        <SiGithub
                            size={14}
                            aria-hidden="true"
                            className="shrink-0 text-foreground"
                        />
                        <span className="truncate">
                            {repo.owner}/{repo.name}
                        </span>
                        <ExternalLink size={13} aria-hidden="true" className="shrink-0" />
                    </a>
                    <span className="rounded-full bg-foreground/7 px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
                        {repo.branch}
                    </span>
                </div>
                <div className="rounded-[10px] border border-border bg-surface-2 px-3 py-2.5 text-[13px]">
                    <StatusLine
                        busy={repoBusy(repo)}
                        fine={repo.status === "synced"}
                        text={repo.message ?? "Saved to GitHub"}
                    />
                    {files.length > 0 && (
                        <ul className="mt-2 grid gap-0.5 border-t border-dashed border-border pt-2">
                            {files.map((file) => (
                                <li
                                    key={file}
                                    className="font-mono text-xs wrap-anywhere text-muted-foreground"
                                >
                                    {file}
                                </li>
                            ))}
                        </ul>
                    )}
                    {repo.status === "conflict" && repo.detail.pull_url && (
                        <a
                            href={repo.detail.pull_url}
                            target="_blank"
                            rel="noreferrer"
                            className={PANEL_LINK}
                        >
                            Review the pull request
                            <ExternalLink size={13} aria-hidden="true" />
                        </a>
                    )}
                    {repo.status === "reconnect" && (
                        <Link href="/integrations/github" className={PANEL_LINK}>
                            Reconnect GitHub
                        </Link>
                    )}
                </div>
                <div className="flex flex-wrap gap-2">
                    {repo.status === "approval" && (
                        <Button
                            disabled={busy}
                            onClick={() => act(project.approve)}
                            className="max-sm:w-full"
                        >
                            Approve and keep saving
                        </Button>
                    )}
                    <Button
                        variant="secondary"
                        disabled={busy || repoBusy(repo)}
                        onClick={() => act(project.sync)}
                        className="max-sm:w-full"
                    >
                        <RefreshCw size={14} aria-hidden="true" />
                        Sync now
                    </Button>
                </div>
                <ErrorBox message={error} className="text-xs" />
                <RepoMore projectId={projectId} repo={repo} project={project} />
            </div>
        );

    return (
        <WorkspaceTabPanel
            title="GitHub"
            note="Keep this project in a GitHub repository. Changes here are saved there, and changes made there come back here."
        >
            {body}
        </WorkspaceTabPanel>
    );
}
