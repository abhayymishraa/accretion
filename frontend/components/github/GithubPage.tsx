"use client";

import { McpShell, StateBadge } from "@/components/mcp/McpShell";
import styles from "@/components/mcp/mcp.module.css";
import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Skeleton } from "@/components/ui/skeleton";
import { useGithubAccount } from "@/hooks/github/useGithubAccount";
import { SiGithub } from "react-icons/si";
import { type ReactNode, useState } from "react";
import { mount } from "./hairline/dock.js";
import { HairlineMark } from "./HairlineMark";
import { ImportList } from "./ImportList";
import { IntegrationHeader } from "./IntegrationHeader";
import { RemoveRow } from "./RemoveRow";

const ACTION = "rounded-[8px] px-4 text-[14px] max-sm:w-full";
const NOTE = "rounded-[12px] border border-border bg-surface-1 px-4 py-4 text-[14px] leading-5";

/** The GitHub page: connect once, then save projects to GitHub and bring repositories in. */
export default function GithubPage() {
    const github = useGithubAccount();
    const { account } = github;
    const [opening, setOpening] = useState(false);
    // Connecting leaves the page; the button stays pressed until it does.
    const connect = async () => {
        setOpening(true);
        await github.connect();
        setOpening(false);
    };

    let body: ReactNode;
    if (github.error)
        body = <ErrorBox message={github.error} onRetry={() => void github.retry()} />;
    else if (!account) body = <Skeleton className="h-16 w-full rounded-[12px]" />;
    else if (!account.configured)
        body = <p className={NOTE}>Saving to GitHub is not available here yet.</p>;
    else if (!account.connected)
        body = (
            <div className={`${NOTE} flex flex-wrap items-center gap-4`}>
                <p className="min-w-0 flex-1 basis-[220px] text-foreground/85">
                    You choose which repositories Accretion can reach. You can change that on GitHub
                    at any time.
                </p>
                <Button className={ACTION} disabled={opening} onClick={connect}>
                    <SiGithub size={14} aria-hidden="true" />
                    {opening ? "Opening GitHub" : "Connect GitHub"}
                </Button>
            </div>
        );
    else
        body = (
            <div className={styles.reveal}>
                <div className="flex min-h-16 flex-wrap items-center gap-3 rounded-[12px] border border-border bg-surface-1 py-3 pr-3 pl-4">
                    <SiGithub size={20} aria-hidden="true" className="shrink-0" />
                    <p className="min-w-0 flex-1 truncate text-[14px] font-medium">
                        {account.login}
                    </p>
                    {/* Keyed on its text, so "Needs access" turning "Connected" settles in (mcp.module.css .badge). */}
                    <span key={String(account.installed)} className={`${styles.badge} inline-flex`}>
                        <StateBadge
                            badge={
                                account.installed
                                    ? { tone: "ok", text: "Connected" }
                                    : { tone: "warn", text: "Needs access" }
                            }
                        />
                    </span>
                </div>
                {!account.installed && (
                    <div className={`${NOTE} mt-4 flex flex-wrap items-center gap-4`}>
                        <p className="min-w-0 flex-1 basis-[220px] text-foreground/85">
                            Accretion can&apos;t reach any of your repositories yet. Choose the ones
                            it may use.
                        </p>
                        <Button className={ACTION} disabled={opening} onClick={connect}>
                            {opening ? "Opening GitHub" : "Choose repositories"}
                        </Button>
                    </div>
                )}
                {account.installed && <ImportList github={github} />}
                <div className="mt-10">
                    <RemoveRow
                        note="Disconnect GitHub from your account. Your repositories stay on GitHub."
                        label="Disconnect"
                        question="Disconnect GitHub? Your projects stop saving to it."
                        onConfirm={github.disconnect}
                    />
                </div>
            </div>
        );

    return (
        <McpShell>
            <IntegrationHeader
                title="GitHub"
                description="Save each project to its own GitHub repository, kept up to date after every change. Or bring one of your repositories in as a new project."
                figure={
                    <HairlineMark
                        mount={mount}
                        label="The GitHub mark as a coin, hovering over a slot it settles into."
                        className="w-[180px]"
                    />
                }
            />
            {/* The account's state replaces its skeleton with the house fade. */}
            {account ? <div data-loaded-in="">{body}</div> : body}
        </McpShell>
    );
}
