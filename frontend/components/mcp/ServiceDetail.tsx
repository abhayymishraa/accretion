"use client";

import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Skeleton } from "@/components/ui/skeleton";
import { type Connections, useConnections } from "@/hooks/connections/useConnections";
import { ChevronLeft, ExternalLink, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type ReactNode, useState } from "react";
import { DetailHeader } from "./DetailHeader";
import { Board } from "./Board";
import styles from "./mcp.module.css";
import { McpShell } from "./McpShell";
import { findEntry, type ServiceEntry, serviceEntries } from "./serviceEntries";
import { ToolReview } from "./ToolReview";

function Section({ title, children }: { title: string; children: ReactNode }) {
    return (
        <section className="mb-8" aria-label={title}>
            <h2 className="mb-3 text-[14px] leading-5 font-semibold">{title}</h2>
            {children}
        </section>
    );
}

/** Tools before there are any to show: an empty port, and what will bring them. */
function NoTools({ entry }: { entry: ServiceEntry }) {
    const step = !entry.server
        ? `Connect ${entry.title} to see what it can do.`
        : entry.server.auth === "header"
          ? `Add your ${entry.title} key to see what it can do.`
          : `Sign in to ${entry.title} to see what it can do.`;
    return (
        <div className="grid place-items-center rounded-[12px] border border-border bg-surface-1 px-6 pt-4 pb-8 text-center">
            <Board
                states={["attention"]}
                label="A patch panel with one empty port, waiting for a cable."
                className="w-[140px]"
            />
            <p className="mt-1 text-[14px] leading-5 font-medium">No tools found</p>
            <p className="mt-1 max-w-[40ch] text-[14px] leading-5 text-foreground/85">{step}</p>
        </div>
    );
}

/** Remove, behind a question asked in place. A service added by address leaves the list with it. */
function RemoveControl({ entry, remove }: { entry: ServiceEntry; remove: Connections["remove"] }) {
    const router = useRouter();
    const [asking, setAsking] = useState(false);
    const [busy, setBusy] = useState(false);
    if (!entry.server) return null;
    const { id, title } = entry.server;
    return (
        <div className="flex min-h-14 flex-wrap items-center gap-x-3 gap-y-2 border-t border-border pt-4">
            {asking ? (
                <div
                    role="group"
                    aria-label={`Remove ${title}?`}
                    className={`${styles.ask} flex w-full flex-wrap items-center gap-x-3 gap-y-2`}
                >
                    <p className="mr-auto text-[13px]">
                        Remove {title}? Your builds stop using it.
                    </p>
                    <Button variant="secondary" disabled={busy} onClick={() => setAsking(false)}>
                        Keep
                    </Button>
                    <Button
                        variant="secondary"
                        className="text-destructive"
                        disabled={busy}
                        onClick={async () => {
                            setBusy(true);
                            // A failure has already been shown as a toast.
                            const failure = await remove(id);
                            setBusy(false);
                            setAsking(false);
                            if (!failure && !entry.catalog) router.replace("/connectors");
                        }}
                    >
                        {busy ? "Removing" : "Remove"}
                    </Button>
                </div>
            ) : (
                <>
                    <p className="mr-auto text-[13px] text-muted-foreground">
                        Remove {title} from your account.
                    </p>
                    <Button variant="secondary" onClick={() => setAsking(true)}>
                        <Trash2 size={14} aria-hidden="true" />
                        Remove
                    </Button>
                </>
            )}
        </div>
    );
}

function Loading() {
    return (
        <div aria-hidden="true">
            <div className="mb-10 flex gap-4">
                <Skeleton className="size-10 rounded-[8px]" />
                <div className="flex flex-1 flex-col gap-2 pt-1">
                    <Skeleton className="h-6 w-40" />
                    <Skeleton className="h-3.5 w-full max-w-[420px]" />
                </div>
            </div>
            <Skeleton className="mb-3 h-4 w-20" />
            <Skeleton className="mb-10 h-3.5 w-full max-w-[560px]" />
            <Skeleton className="mb-3 h-4 w-14" />
            <Skeleton className="h-40 w-full rounded-[12px]" />
        </div>
    );
}

/** One service's page: what it is, its next step, its tools, and its details. */
export default function ServiceDetail({ id }: { id: string }) {
    const connections = useConnections();
    const { servers, catalog, error, retry } = connections;
    const entry = servers && catalog ? findEntry(serviceEntries(catalog, servers), id) : null;
    let body: ReactNode;
    if (error)
        body = (
            <ErrorBox message={error}>
                <Button
                    variant="utility"
                    className="h-8 px-2 text-destructive underline"
                    onClick={() => void retry()}
                >
                    Try again
                </Button>
            </ErrorBox>
        );
    else if (!servers || !catalog) body = <Loading />;
    else if (!entry)
        body = (
            <div className="rounded-[12px] border border-border bg-surface-1 px-6 py-10 text-center">
                <h1 className="text-[16px] font-medium">This service is not here</h1>
                <p className="mt-1 text-[13px] text-muted-foreground">
                    It may have been removed. Go back to see the services you can connect.
                </p>
            </div>
        );
    else
        body = (
            <div className={styles.reveal}>
                <DetailHeader entry={entry} connections={connections} />
                <Section title="Overview">
                    <p className="text-[14px] leading-5 text-foreground/85">
                        {entry.description} When it is on, your builds can use the tools you tick
                        below, and nothing else.
                    </p>
                </Section>
                <Section title="Tools">
                    {entry.server?.connected ? (
                        <ToolReview server={entry.server} connections={connections} />
                    ) : (
                        <NoTools entry={entry} />
                    )}
                </Section>
                <Section title="Details">
                    <dl className="flex flex-wrap gap-x-12 gap-y-4 text-[14px] leading-5">
                        {entry.catalog ? (
                            <>
                                <div className="grid gap-1">
                                    <dt className="text-muted-foreground">Created by</dt>
                                    <dd>{entry.catalog.maker}</dd>
                                </div>
                                <div className="grid min-w-0 gap-1">
                                    <dt className="text-muted-foreground">Docs</dt>
                                    <dd className="min-w-0">
                                        <a
                                            href={entry.catalog.docs_url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="inline-flex max-w-full items-center gap-1.5 break-all text-primary no-underline focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:underline"
                                        >
                                            {entry.catalog.docs_url}
                                            <ExternalLink
                                                size={14}
                                                aria-hidden="true"
                                                className="shrink-0"
                                            />
                                        </a>
                                    </dd>
                                </div>
                            </>
                        ) : (
                            <div className="grid min-w-0 gap-1">
                                <dt className="text-muted-foreground">Address</dt>
                                <dd className="font-mono text-[13px] break-all">{entry.url}</dd>
                            </div>
                        )}
                    </dl>
                </Section>
                <RemoveControl entry={entry} remove={connections.remove} />
            </div>
        );

    return (
        <McpShell>
            <Link
                href="/connectors"
                className="-ml-2 mb-6 inline-flex h-11 items-center gap-1.5 rounded-[8px] px-2 text-[14px] leading-5 font-medium text-foreground no-underline focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:text-foreground/80"
            >
                <ChevronLeft size={16} aria-hidden="true" />
                Connectors
            </Link>
            {body}
        </McpShell>
    );
}
