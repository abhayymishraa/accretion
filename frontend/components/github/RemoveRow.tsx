"use client";

import styles from "@/components/mcp/mcp.module.css";
import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Unplug } from "lucide-react";
import { useState } from "react";

/**
 * A disconnect behind a question asked in place, like a connector's Remove: what it does, then Keep or the
 * action. Shared by the GitHub and Supabase pages and their project tabs.
 */
export function RemoveRow({
    note,
    label,
    question,
    onConfirm,
}: {
    note: string;
    label: string;
    question: string;
    // Returns the error to show, or "".
    onConfirm: () => Promise<string>;
}) {
    const [asking, setAsking] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    return (
        <div className="flex min-h-14 flex-wrap items-center gap-x-3 gap-y-2 border-t border-border pt-4">
            {asking ? (
                <div
                    role="group"
                    aria-label={question}
                    className={`${styles.ask} flex w-full flex-wrap items-center gap-x-3 gap-y-2`}
                    onKeyDown={(event) => {
                        if (event.key === "Escape") setAsking(false);
                    }}
                >
                    <p className="mr-auto text-[13px]">{question}</p>
                    <Button
                        variant="secondary"
                        autoFocus
                        disabled={busy}
                        onClick={() => setAsking(false)}
                    >
                        Keep
                    </Button>
                    <Button
                        variant="secondary"
                        className="text-destructive"
                        disabled={busy}
                        onClick={async () => {
                            setBusy(true);
                            const failure = await onConfirm();
                            setBusy(false);
                            setError(failure);
                            if (!failure) setAsking(false);
                        }}
                    >
                        {busy ? "Working…" : label}
                    </Button>
                </div>
            ) : (
                <>
                    <p className="mr-auto text-[13px] text-muted-foreground">{note}</p>
                    <Button variant="secondary" onClick={() => setAsking(true)}>
                        <Unplug size={14} aria-hidden="true" />
                        {label}
                    </Button>
                </>
            )}
            <ErrorBox message={error} className="w-full rounded-none border-0 bg-transparent p-0" />
        </div>
    );
}
