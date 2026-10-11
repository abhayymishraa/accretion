"use client";

import { HairlineMark } from "@/components/github/HairlineMark";
import { IntegrationHeader } from "@/components/github/IntegrationHeader";
import { RemoveRow } from "@/components/github/RemoveRow";
import { McpShell, StateBadge } from "@/components/mcp/McpShell";
import styles from "@/components/mcp/mcp.module.css";
import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Skeleton } from "@/components/ui/skeleton";
import { useSupabaseAccount } from "@/hooks/supabase/useSupabaseAccount";
import { type ReactNode, useState } from "react";
import { SiSupabase } from "react-icons/si";
import { mount } from "./hairline/bolt.js";

const NOTE = "rounded-[12px] border border-border bg-surface-1 px-4 py-4 text-[14px] leading-5";

/** The Supabase page: connect once, then give any project a Supabase database from its Database tab. */
export default function SupabasePage() {
    const supabase = useSupabaseAccount();
    const { account } = supabase;
    const [opening, setOpening] = useState(false);

    let body: ReactNode;
    if (supabase.error)
        body = <ErrorBox message={supabase.error} onRetry={() => void supabase.retry()} />;
    else if (!account) body = <Skeleton className="h-16 w-full rounded-[12px]" />;
    else if (!account.configured)
        body = <p className={NOTE}>Supabase is not available here yet.</p>;
    else if (!account.connected)
        body = (
            <div className={`${NOTE} flex flex-wrap items-center gap-4`}>
                <p className="min-w-0 flex-1 basis-[220px] text-foreground/85">
                    Sign in to Supabase and choose which organizations Accretion can use.
                </p>
                <Button
                    className="rounded-[8px] px-4 text-[14px] max-sm:w-full"
                    disabled={opening}
                    onClick={async () => {
                        // Connecting leaves the page; the button stays pressed until it does.
                        setOpening(true);
                        await supabase.connect();
                        setOpening(false);
                    }}
                >
                    <SiSupabase size={14} aria-hidden="true" />
                    {opening ? "Opening Supabase" : "Connect Supabase"}
                </Button>
            </div>
        );
    else
        body = (
            <div className={styles.reveal}>
                <div className="flex min-h-16 flex-wrap items-center gap-3 rounded-[12px] border border-border bg-surface-1 py-3 pr-3 pl-4">
                    <SiSupabase size={20} aria-hidden="true" className="shrink-0" />
                    <p className="min-w-0 flex-1 text-[14px] font-medium">Supabase</p>
                    <StateBadge badge={{ tone: "ok", text: "Connected" }} />
                </div>
                <section aria-label="Organizations" className="mt-8">
                    <h2 className="mb-3 text-[14px] leading-5 font-semibold">Organizations</h2>
                    {account.organizations.length ? (
                        <ul className="grid gap-px overflow-hidden rounded-[12px] border border-border bg-border">
                            {account.organizations.map((org) => (
                                <li
                                    key={org.id}
                                    className="flex min-h-12 items-center bg-surface-1 px-4 text-[14px]"
                                >
                                    {org.name}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className={NOTE}>No organizations yet. Make one on Supabase first.</p>
                    )}
                    <p className="mt-3 text-[13px] leading-5 text-muted-foreground">
                        To give an app a Supabase database, open the project and choose Database.
                    </p>
                </section>
                <div className="mt-10">
                    <RemoveRow
                        note="Disconnect Supabase from your account. Your Supabase projects stay."
                        label="Disconnect"
                        question="Disconnect Supabase? Your apps' data stays on Supabase."
                        onConfirm={supabase.disconnect}
                    />
                </div>
            </div>
        );

    return (
        <McpShell>
            <IntegrationHeader
                title="Supabase"
                description="Give an app its own Supabase database, with sign-in and storage. Its data moves there, and you can see it in Supabase."
                figure={
                    <HairlineMark
                        mount={mount}
                        label="The Supabase bolt in two halves, sliding together into one."
                        className="w-[180px]"
                    />
                }
            />
            {body}
        </McpShell>
    );
}
