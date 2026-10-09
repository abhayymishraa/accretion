"use client";

import { ErrorBox } from "@/components/ui/ErrorBox";
import { Skeleton } from "@/components/ui/skeleton";
import { useProjectSecrets } from "@/hooks/secrets/useProjectSecrets";
import { ChevronDown, Lock, RotateCw, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { AddKeyForm } from "./AddKeyForm";
import { PegRail } from "./PegRail";
import { SecretRow } from "./SecretRow";

// The backend's limit (agent/sandbox/secrets.py MAX_SECRETS).
const LIMIT = 100;

/** The workspace's Keys tab: the private keys the user's app reads when it runs. */
export function ProjectSecretsPanel({ projectId }: { projectId: string }) {
    const { secrets, failed, retry, save, remove } = useProjectSecrets(projectId);
    // After a save or remove the running preview restarts with it: said for a few seconds, from the latest change.
    const [changedAt, setChangedAt] = useState(0);
    useEffect(() => {
        if (!changedAt) return;
        const timer = setTimeout(() => setChangedAt(0), 6000);
        return () => clearTimeout(timer);
    }, [changedAt]);
    const noted = (failure: string) => {
        if (!failure) setChangedAt(Date.now());
        return failure;
    };
    const saveKey = async (name: string, value: string) => noted(await save(name, value));
    const removeKey = async (name: string) => noted(await remove(name));
    const keys = secrets?.secrets ?? [];
    const full = keys.length >= LIMIT;
    // The keys there when the panel first loaded: only a key added after that unfolds into the list.
    const [firstNames, setFirstNames] = useState<Set<string> | null>(null);
    // Whether this mount showed the skeleton, so the list's fade plays only after a real wait.
    const [waited, setWaited] = useState(false);
    if (!secrets && !failed && !waited) setWaited(true);
    if (secrets && !firstNames) setFirstNames(new Set(keys));

    return (
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-surface-1">
            <header className="border-b border-border px-4 py-3">
                <div className="flex items-baseline gap-3">
                    <h2 className="text-sm font-semibold text-foreground">App keys</h2>
                    {secrets && (
                        <span
                            data-numeric=""
                            className={`ml-auto font-mono text-[11px] tabular-nums ${full ? "text-destructive" : "text-muted-foreground"}`}
                        >
                            {keys.length} of {LIMIT}
                        </span>
                    )}
                </div>
                <p className="mt-1 max-w-[60ch] text-xs leading-[1.5] text-pretty text-muted-foreground">
                    Keys your app reads when it runs, like a Stripe or OpenAI key. A saved value is
                    never shown again, and the builder sees only the names.
                </p>
                {/* Stays mounted, so it leaves the way it came (globals.css [data-disclosure]). */}
                <div role="status">
                    <div data-disclosure={changedAt > 0 ? "open" : ""}>
                        <p className="mt-2 flex items-center gap-2 rounded-[10px] border border-border bg-surface-2 px-2.5 py-1.5 text-xs">
                            <RotateCw
                                size={14}
                                aria-hidden="true"
                                className="shrink-0 text-muted-foreground"
                            />
                            Saved. A running preview restarts so your app gets the change.
                        </p>
                    </div>
                </div>
            </header>
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain pb-[calc(16px+env(safe-area-inset-bottom))]">
                {failed && !secrets ? (
                    <div className="p-4">
                        <ErrorBox message="Couldn't load your keys. They are still saved, and your app still has them.">
                            <button
                                type="button"
                                onClick={() => void retry()}
                                className="cursor-pointer rounded-[4px] underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-ring pointer-coarse:min-h-11"
                            >
                                Try again
                            </button>
                        </ErrorBox>
                    </div>
                ) : !secrets ? (
                    <div className="grid gap-1.5 p-4" aria-label="Loading keys" aria-busy="true">
                        {[0, 1, 2].map((row) => (
                            <Skeleton key={row} className="h-12 rounded-[10px]" />
                        ))}
                    </div>
                ) : (
                    // Fades in over the skeleton it replaces (globals.css [data-loaded-in]), only when one was shown:
                    // the list is cached after the first load, and a tab that opens often must not replay it.
                    <div data-loaded-in={waited ? "" : undefined}>
                        <div className="border-b border-border px-4 py-3">
                            {full ? (
                                <p className="flex gap-2 rounded-[10px] border border-border px-3 py-2.5 text-[12.5px] leading-[1.5] text-muted-foreground">
                                    <Lock
                                        size={14}
                                        aria-hidden="true"
                                        className="mt-0.5 shrink-0"
                                    />
                                    This project has {LIMIT} keys, the most it can hold. Delete one
                                    to add another.
                                </p>
                            ) : (
                                <AddKeyForm
                                    saved={keys}
                                    managed={secrets.managed}
                                    onSave={saveKey}
                                />
                            )}
                        </div>
                        {keys.length === 0 ? (
                            <div className="grid justify-items-center px-6 pt-1 pb-3 text-center">
                                <PegRail />
                                <h3 className="text-[13px] font-semibold">No keys yet</h3>
                                <p className="mt-0.5 max-w-[34ch] text-xs leading-[1.5] text-pretty text-muted-foreground">
                                    When a feature needs one, the builder asks for it in chat.
                                </p>
                            </div>
                        ) : (
                            <section aria-label="Your keys" className="px-2 pt-3">
                                <div className="flex items-baseline gap-2 px-2 pb-1.5">
                                    <h3 className="text-xs font-semibold">Your keys</h3>
                                </div>
                                <ul className="grid gap-0.5">
                                    {keys.map((secret) => (
                                        <SecretRow
                                            key={secret}
                                            name={secret}
                                            isNew={!firstNames?.has(secret)}
                                            onReplace={saveKey}
                                            onRemove={removeKey}
                                        />
                                    ))}
                                </ul>
                            </section>
                        )}
                        {secrets.managed.length > 0 && (
                            <details
                                data-faq=""
                                className="group mx-4 mt-3 border-t border-border"
                                open={keys.length === 0}
                            >
                                <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-ring [&::-webkit-details-marker]:hidden">
                                    <ShieldCheck
                                        size={14}
                                        aria-hidden="true"
                                        className="text-muted-foreground"
                                    />
                                    Set by Accretion
                                    <span className="font-mono font-normal text-muted-foreground">
                                        {secrets.managed.length}
                                    </span>
                                    <ChevronDown
                                        size={14}
                                        aria-hidden="true"
                                        className="ml-auto text-muted-foreground transition-transform duration-[260ms] ease-[var(--ease-out)] group-open:rotate-180 motion-reduce:transition-none"
                                    />
                                </summary>
                                <p className="mb-1.5 text-xs leading-[1.5] text-muted-foreground">
                                    Your app needs these to run, so Accretion sets them for you. You
                                    can&apos;t see or change them, and you can&apos;t use these
                                    names.
                                </p>
                                <ul>
                                    {secrets.managed.map((name) => (
                                        <li
                                            key={name}
                                            className="flex min-h-10 items-center gap-2 border-t border-dashed border-border"
                                        >
                                            <span className="flex-1 font-mono text-xs wrap-anywhere text-muted-foreground">
                                                {name}
                                            </span>
                                            <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                                                <Lock size={12} aria-hidden="true" />
                                                Managed
                                            </span>
                                        </li>
                                    ))}
                                </ul>
                            </details>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
