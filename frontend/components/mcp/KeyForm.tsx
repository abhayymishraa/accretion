"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Connections } from "@/hooks/connections/useConnections";
import type { Connection } from "@/types/connection.type";
import { useId, useState } from "react";
import styles from "./mcp.module.css";

/** Paste a key. A service added by address has no hint, so it may also need the key's name. */
export function KeyForm({
    server,
    saveKey,
    onCancel,
}: {
    server: Connection;
    saveKey: Connections["saveKey"];
    onCancel: () => void;
}) {
    const id = useId();
    const [value, setValue] = useState("");
    const [name, setName] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const custom = server.key_hint === null;

    return (
        <form
            className={`${styles.ask} grid gap-4 rounded-[12px] border border-border bg-surface-1 p-4`}
            onSubmit={async (event) => {
                event.preventDefault();
                if (!value.trim()) return setError("Paste the key first.");
                setBusy(true);
                setError(await saveKey(server.id, value.trim(), name.trim() || undefined));
                setBusy(false);
            }}
        >
            <div className="grid gap-2">
                <label htmlFor={`${id}-key`} className="text-[13px] font-medium">
                    Your {server.title} key
                </label>
                <Input
                    id={`${id}-key`}
                    type="password"
                    autoComplete="off"
                    spellCheck={false}
                    value={value}
                    onChange={(event) => setValue(event.target.value)}
                    aria-invalid={error ? true : undefined}
                    aria-describedby={`${id}-hint`}
                />
                <p id={`${id}-hint`} className="text-[12.5px] leading-[1.5] text-muted-foreground">
                    {server.key_hint
                        ? `Where to find it: ${server.key_hint}`
                        : "Use the key the service gave you. It is stored safely and never shown again."}
                </p>
            </div>
            {custom && (
                <div className="grid gap-2">
                    <label htmlFor={`${id}-name`} className="text-[13px] font-medium">
                        Key name{" "}
                        <span className="font-normal text-muted-foreground">(optional)</span>
                    </label>
                    <Input
                        id={`${id}-name`}
                        autoComplete="off"
                        spellCheck={false}
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        aria-describedby={`${id}-name-hint`}
                    />
                    <p
                        id={`${id}-name-hint`}
                        className="text-[12.5px] leading-[1.5] text-muted-foreground"
                    >
                        Only if the service&apos;s guide names one, such as x-api-key. Empty sends
                        it as a bearer token.
                    </p>
                </div>
            )}
            {error && (
                <p role="alert" className="text-[12.5px] text-destructive">
                    {error}
                </p>
            )}
            <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={busy}>
                    {busy ? "Saving" : "Save key"}
                </Button>
                <Button type="button" variant="secondary" onClick={onCancel} disabled={busy}>
                    Cancel
                </Button>
            </div>
        </form>
    );
}
