"use client";

import { HairlineMark } from "@/components/github/HairlineMark";
import { RemoveRow } from "@/components/github/RemoveRow";
import { PANEL_LINK, StatusLine } from "@/components/github/RepoStatus";
import { buttonVariants } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Findings } from "@/components/ui/Findings";
import { Skeleton } from "@/components/ui/skeleton";
import { databaseBusy, useProjectDatabase } from "@/hooks/supabase/useProjectDatabase";
import { ExternalLink } from "lucide-react";
import Link from "next/link";
import { type ReactNode, useState } from "react";
import { mount } from "./hairline/bolt.js";
import { LinkDatabaseForm } from "./LinkDatabaseForm";
import { WorkspaceTabPanel } from "@/components/chat/WorkspaceTabPanel";

const NOTE = "text-xs leading-[1.5] text-muted-foreground";

/** The workspace's Database tab: keep the app's data in Supabase, see its status, and act on it. */
export function ProjectDatabasePanel({ projectId }: { projectId: string }) {
    const project = useProjectDatabase(projectId);
    const { database, account } = project;
    // The linked view fades in only right after linking, never each time the tab opens.
    const [formShown, setFormShown] = useState(false);
    if (database && !database.linked && !formShown) setFormShown(true);

    let body: ReactNode;
    // A linked database shows without the account; only linking one needs it.
    if (project.failed && (!database || (!database.linked && !account)))
        body = (
            <ErrorBox
                message="Couldn't load this project's database."
                onRetry={() => void project.retry()}
            />
        );
    else if (!database || (!database.linked && !account))
        body = <Skeleton className="h-24 rounded-[10px]" aria-label="Loading" />;
    else if (!database.offered)
        body = (
            <p className={NOTE}>
                This app keeps its data in a kind of database Supabase can&apos;t hold, so it keeps
                its built-in database.
            </p>
        );
    else if (!database.linked && !account?.configured)
        body = <p className={NOTE}>Supabase is not available here yet.</p>;
    else if (!database.linked && !account?.connected)
        body = (
            <div className="grid justify-items-center pb-4 text-center">
                <HairlineMark
                    mount={mount}
                    label="The Supabase bolt in two halves, waiting to join."
                    className="w-[150px]"
                />
                <h3 className="text-[13px] font-semibold">Using the built-in database</h3>
                <p className={`${NOTE} mt-0.5 max-w-[36ch]`}>
                    Connect Supabase once, then move this app&apos;s data there.
                </p>
                <Link
                    href="/integrations/supabase"
                    className={`${buttonVariants({ variant: "secondary" })} mt-4`}
                >
                    Connect Supabase
                </Link>
            </div>
        );
    else if (!database.linked)
        body = (
            <LinkDatabaseForm organizations={account?.organizations ?? []} link={project.link} />
        );
    else
        body = (
            <div data-loaded-in={formShown ? "" : undefined} className="grid gap-4">
                <div className="grid gap-1">
                    <p className="text-[13px] font-medium">
                        {database.name}
                        <span className="ml-2 font-mono text-[11px] font-normal text-muted-foreground">
                            {database.region}
                        </span>
                    </p>
                    <div className="rounded-[10px] border border-border bg-surface-2 px-3 py-2.5">
                        <StatusLine
                            busy={databaseBusy(database)}
                            fine={database.status === "ready"}
                            text={database.message ?? "Connected to Supabase"}
                            wrap
                            className="text-[13px]"
                        />
                        {database.status === "reconnect" && (
                            <Link href="/integrations/supabase" className={PANEL_LINK}>
                                Reconnect Supabase
                            </Link>
                        )}
                    </div>
                    {database.dashboard_url && (
                        <a
                            href={database.dashboard_url}
                            target="_blank"
                            rel="noreferrer"
                            className={PANEL_LINK}
                        >
                            See your data in Supabase
                            <ExternalLink size={13} aria-hidden="true" />
                        </a>
                    )}
                </div>
                <Findings
                    findings={database.findings}
                    footer={<p className={NOTE}>You can ask the builder in chat to fix these.</p>}
                />
                <RemoveRow
                    note="Go back to the built-in database. Your data on Supabase stays there."
                    label="Disconnect"
                    question="Disconnect Supabase? Your app goes back to its built-in database."
                    onConfirm={project.unlink}
                />
            </div>
        );

    return (
        <WorkspaceTabPanel
            title="Database"
            note="Where your app keeps its data. It starts with a built-in database; Supabase gives it one you can see and manage yourself."
        >
            {body}
        </WorkspaceTabPanel>
    );
}
