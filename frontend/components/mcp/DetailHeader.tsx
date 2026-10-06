"use client";

import { SkillSwitch } from "@/components/skills/SkillSwitch";
import { Button } from "@/components/ui/button";
import type { Connections } from "@/hooks/connections/useConnections";
import { KeyRound, LogIn, Plus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { KeyForm } from "./KeyForm";
import styles from "./mcp.module.css";
import { StateBadge } from "./McpShell";
import { badge, type ServiceEntry } from "./serviceEntries";
import { ServerSettings } from "./ServerSettings";
import { ServiceLogo } from "./ServiceLogo";

const ACTION = "h-9 rounded-[8px] px-4 text-[14px] pointer-coarse:h-11 max-sm:w-full";

/** The service's logo, name and description, its one next step, and its account-wide switch. */
export function DetailHeader({
    entry,
    connections,
}: {
    entry: ServiceEntry;
    connections: Connections;
}) {
    const { server } = entry;
    const [busy, setBusy] = useState(false);
    const [keying, setKeying] = useState(false);
    const [error, setError] = useState("");
    // The switch moves at once and settles on what the server saved.
    const [pending, setPending] = useState<boolean | null>(null);
    // "Connect" on a service that signs in adds it first; the sign-in starts once it is in the list.
    const signInNext = useRef(false);
    const { signIn } = connections;
    useEffect(() => {
        if (!signInNext.current || !server || server.connected) return;
        signInNext.current = false;
        void signIn(server.id);
    }, [server, signIn]);

    async function addThen(next: "sign-in" | "key" | "none") {
        if (!entry.catalog) return;
        setBusy(true);
        setError("");
        signInNext.current = next === "sign-in";
        const failure = await connections.add({ catalog_id: entry.catalog.id });
        // A sign-in leaves the page; keep the button pressed until it does.
        if (failure || next !== "sign-in") setBusy(false);
        if (failure) {
            signInNext.current = false;
            setError(failure);
        } else if (next === "key") setKeying(true);
    }

    let action = null;
    if (!server)
        action = (
            <Button
                className={ACTION}
                disabled={busy}
                onClick={() =>
                    addThen(
                        entry.auth === "oauth"
                            ? "sign-in"
                            : entry.auth === "header"
                              ? "key"
                              : "none",
                    )
                }
            >
                {entry.auth === "none" && <Plus size={14} aria-hidden="true" />}
                {busy
                    ? entry.auth === "oauth"
                        ? "Opening sign-in"
                        : "Adding"
                    : entry.auth === "none"
                      ? "Add"
                      : "Connect"}
            </Button>
        );
    else if (!server.connected && server.auth === "oauth")
        action = (
            <Button
                className={ACTION}
                disabled={busy}
                onClick={async () => {
                    setBusy(true);
                    await signIn(server.id);
                    setBusy(false);
                }}
            >
                <LogIn size={14} aria-hidden="true" />
                {busy ? "Opening sign-in" : `Sign in to ${server.title}`}
            </Button>
        );
    else if (!server.connected && !keying)
        action = (
            <Button className={ACTION} onClick={() => setKeying(true)}>
                <KeyRound size={14} aria-hidden="true" />
                Add your key
            </Button>
        );
    // A service that works without a key, but gives a higher limit with one: offered, never required.
    else if (server.auth === "none" && server.key_hint && !keying)
        action = (
            <Button variant="secondary" className={ACTION} onClick={() => setKeying(true)}>
                <KeyRound size={14} aria-hidden="true" />
                Add your key
            </Button>
        );

    const state = badge(entry);
    const enabled = pending ?? server?.enabled ?? false;
    return (
        <header className="mb-8">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-4">
                <ServiceLogo id={entry.logo} icon={server?.icon} />
                <div className="min-w-0 flex-1 basis-[220px]">
                    <h1 className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[20px] leading-7 font-semibold">
                        <span className="min-w-0 wrap-anywhere">{entry.title}</span>
                        {state && (
                            <span key={state.text} className={`${styles.badge} inline-flex`}>
                                <StateBadge badge={state} />
                            </span>
                        )}
                    </h1>
                    <p className="text-[14px] leading-5 text-foreground/85">{entry.description}</p>
                </div>
                {action && <div className="max-sm:w-full">{action}</div>}
            </div>
            {server && (
                <div className="mt-8 flex min-h-16 items-center justify-between gap-4 rounded-[12px] border border-border bg-surface-1 py-3 pr-3 pl-4">
                    <div className="min-w-0">
                        <p className="text-[14px] leading-5 font-medium">
                            {enabled ? "On in all your projects" : "Off in all your projects"}
                        </p>
                        <p className="text-[12px] leading-4 text-foreground/70">
                            {enabled
                                ? `Every build can use ${server.title}'s ticked tools.`
                                : `No build uses ${server.title} until you switch it on.`}
                        </p>
                    </div>
                    <SkillSwitch
                        checked={enabled}
                        label={`Use ${server.title} in all your projects`}
                        onChange={async (next) => {
                            setPending(next);
                            await connections.setEnabled(server.id, next);
                            setPending(null);
                        }}
                    />
                </div>
            )}
            {server && (
                <ServerSettings server={server} custom={!entry.catalog} connections={connections} />
            )}
            {error && (
                <p role="alert" className={`${styles.ask} mt-3 text-[13px] text-destructive`}>
                    {error}
                </p>
            )}
            {server &&
                keying &&
                (server.auth === "none" || (!server.connected && server.auth === "header")) && (
                    <div className="mt-5">
                        <KeyForm
                            server={server}
                            saveKey={connections.saveKey}
                            onCancel={() => setKeying(false)}
                        />
                    </div>
                )}
        </header>
    );
}
