"use client";

import { DemoRuns } from "@/components/admin/DemoRuns";
import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Input } from "@/components/ui/input";
import { useDemoAccounts } from "@/hooks/admin/useDemoAccounts";
import { useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

const label = "text-[11px] tracking-[0.08em] text-muted-foreground uppercase";
// The link box folds before it is removed (globals.css [data-row]): 200ms, or at once with reduced motion.
const FOLD_MS = 200;

/**
 * Demo accounts: each has its own one-time budget and a link that signs anyone who opens it in,
 * until it is revoked. The prompt field goes into the next link made, created or replaced.
 */
export function DemoAccounts() {
    const demo = useDemoAccounts();
    const [name, setName] = useState("");
    const [prompt, setPrompt] = useState("");
    const [open, setOpen] = useState<number | null>(null);
    // Builds stay mounted once opened, so the panel folds closed with them in it.
    const [opened, setOpened] = useState<Set<number>>(() => new Set());
    // Accounts listed when the page first loaded them; one made later unfolds (globals.css [data-row-new]).
    const [listed, setListed] = useState<Set<number> | null>(null);
    if (demo.accounts && !listed) setListed(new Set(demo.accounts.map((account) => account.id)));
    const reduce = useReducedMotion();
    // The last link shown: it stays while its box folds away after a revoke.
    const [link, setLink] = useState<string | null>(null);
    if (demo.link && demo.link !== link) setLink(demo.link);
    const leaving = link !== null && demo.link === null;
    useEffect(() => {
        if (!leaving) return;
        const timer = setTimeout(() => setLink(null), reduce ? 0 : FOLD_MS);
        return () => clearTimeout(timer);
    }, [leaving, reduce]);

    async function copy(url: string) {
        try {
            await navigator.clipboard.writeText(url);
            toast.success("Link copied");
        } catch {
            // In-app browsers may block the clipboard; the field stays selectable.
            toast.error("Could not copy. Select the link and copy it.");
        }
    }

    return (
        <section aria-labelledby="demo-title" className="mt-16">
            <p className={label}>Admin</p>
            <h2
                id="demo-title"
                className="font-serif text-[clamp(1.6rem,3.4vw,2.2rem)] leading-tight font-normal tracking-[-0.03em]"
            >
                Demo accounts
            </h2>
            <p className="mt-2 max-w-2xl text-[13.5px] text-muted-foreground">
                Each person gets their own account with a one-time build budget. Anyone with the
                link can use the account until you revoke the link.
            </p>

            <form
                className="mt-6 grid gap-3 rounded-xl border border-border bg-card p-4 sm:p-6"
                onSubmit={async (event) => {
                    event.preventDefault();
                    if (await demo.create(name, prompt)) setName("");
                }}
            >
                <Input
                    aria-label="Who the demo is for"
                    placeholder="Who is it for? e.g. Priya at Acme"
                    maxLength={100}
                    required
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                />
                <textarea
                    aria-label="Prompt in the link (optional)"
                    placeholder="Prompt waiting in their composer (optional). /skill and /service picks work."
                    rows={3}
                    maxLength={4000}
                    value={prompt}
                    onChange={(event) => setPrompt(event.target.value)}
                    className="w-full resize-y rounded-[10px] border border-input bg-surface-2 px-3 py-2 text-[16px] sm:text-[14px]"
                />
                <Button type="submit" disabled={demo.pending !== null || !name.trim()}>
                    {demo.pending === "new" ? "Creating…" : "Create demo account and link"}
                </Button>
            </form>

            {/* Unfolds and folds (globals.css [data-row]), so the list below glides instead of
                jumping. A link that replaces another fades in place ([data-loaded-in]): the box
                stays, so the list does not dip. */}
            {link ? (
                <div data-row="" data-row-new="" data-leaving={leaving ? "" : undefined}>
                    {/* The folding child carries no padding, or the fold stops at it. */}
                    <div>
                        <div
                            key={link}
                            data-loaded-in=""
                            className="mt-4 grid gap-2 rounded-xl border border-primary/40 bg-primary/5 p-4"
                        >
                            <p className="text-[13px]">
                                Copy this link now. It is not shown again; make a new one if you
                                lose it.
                            </p>
                            <div className="flex flex-col gap-2 sm:flex-row">
                                <Input
                                    readOnly
                                    aria-label="Demo link"
                                    value={link}
                                    onFocus={(event) => event.target.select()}
                                    className="font-mono text-[13px]"
                                />
                                <Button type="button" onClick={() => copy(link)}>
                                    Copy link
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            ) : null}

            {demo.error ? (
                <div className="mt-4">
                    <ErrorBox message={demo.error} />
                </div>
            ) : null}

            <ul aria-label="Demo accounts" className="mt-6 grid gap-3">
                {demo.accounts?.length === 0 ? (
                    <li className="text-muted-foreground">No demo accounts yet.</li>
                ) : null}
                {demo.accounts?.map((account) => (
                    <li
                        key={account.id}
                        data-row=""
                        data-row-new={listed && !listed.has(account.id) ? "" : undefined}
                    >
                        <div className="rounded-xl border border-border bg-card p-4">
                            <div className="flex flex-wrap items-center justify-between gap-3">
                                <div className="min-w-0">
                                    <p className="truncate font-medium">{account.name}</p>
                                    <p className="text-[12.5px] text-muted-foreground">
                                        ${account.spent_usd.toFixed(2)} used ·{" "}
                                        {account.link_active ? "Link active" : "No link"}
                                    </p>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    <Button
                                        type="button"
                                        variant="secondary"
                                        aria-expanded={open === account.id}
                                        onClick={() => {
                                            setOpen(open === account.id ? null : account.id);
                                            setOpened((ids) => new Set(ids).add(account.id));
                                        }}
                                    >
                                        Builds
                                    </Button>
                                    <Button
                                        type="button"
                                        variant="secondary"
                                        disabled={demo.pending !== null}
                                        onClick={() => demo.replace(account.id, prompt)}
                                    >
                                        {demo.pending === account.id ? "Saving…" : "New link"}
                                    </Button>
                                    {account.link_active ? (
                                        <Button
                                            type="button"
                                            variant="secondary"
                                            disabled={demo.pending !== null}
                                            onClick={() => demo.revoke(account.id)}
                                        >
                                            Revoke
                                        </Button>
                                    ) : null}
                                </div>
                            </div>
                            {/* The shared expand (globals.css [data-disclosure]): height and fade. */}
                            <div data-disclosure={open === account.id ? "open" : ""}>
                                <div className="pt-4">
                                    {opened.has(account.id) ? (
                                        <DemoRuns userId={account.id} />
                                    ) : null}
                                </div>
                            </div>
                        </div>
                    </li>
                ))}
            </ul>
        </section>
    );
}
