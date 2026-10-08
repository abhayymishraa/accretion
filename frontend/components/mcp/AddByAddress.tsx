"use client";

import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useConnections } from "@/hooks/connections/useConnections";
import { cn } from "@/lib/utils";
import { ChevronLeft, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";
import styles from "./mcp.module.css";
import { McpShell } from "./McpShell";
import { Board } from "./Board";
import { ServiceLogo } from "./ServiceLogo";

/** Any other service, by the web address its maker gives. Once added, its own page opens. */
export default function AddByAddress() {
    const { servers, add } = useConnections();
    const router = useRouter();
    const id = useId();
    const [name, setName] = useState("");
    const [url, setUrl] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const [added, setAdded] = useState("");
    // The saved server reaches the list after the add returns; open its page once it is there.
    useEffect(() => {
        const server = added ? servers?.find((item) => item.url === added) : null;
        if (server) router.replace(`/connectors/${encodeURIComponent(server.id)}`);
    }, [added, servers, router]);

    return (
        <McpShell>
            <div className={styles.reveal}>
                <Link
                    href="/connectors"
                    className="-ml-2 mb-6 inline-flex h-11 items-center gap-1.5 rounded-[8px] px-2 text-[14px] leading-5 font-medium text-foreground no-underline focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:text-foreground/80"
                >
                    <ChevronLeft size={16} aria-hidden="true" />
                    Connectors
                </Link>
                <header className="mb-8 flex items-start gap-4">
                    <ServiceLogo id="add" />
                    <div className="min-w-0">
                        <h1 className="text-[20px] leading-7 font-semibold">Custom service</h1>
                        <p className="text-[14px] leading-5 text-foreground/85">
                            Connect a service that is not in the list. Its maker&apos;s help page
                            gives the address.
                        </p>
                    </div>
                </header>
                <div className="mb-8 grid place-items-center rounded-[12px] border border-border bg-surface-1 px-6 py-4">
                    <Board
                        states={["live", "live", "attention", "live"]}
                        label="A patch panel with one empty port among plugged ones."
                        className="w-[220px]"
                    />
                </div>
                <form
                    className="grid gap-6"
                    onSubmit={async (event) => {
                        event.preventDefault();
                        const address = url.trim();
                        if (!/^https:\/\/\S+\.\S+/i.test(address))
                            return setError("Enter the full address, starting with https://");
                        setBusy(true);
                        setError("");
                        const failure = await add({
                            url: address,
                            title: name.trim() || undefined,
                        });
                        if (failure) {
                            setError(failure);
                            setBusy(false);
                        } else setAdded(address);
                    }}
                >
                    <div className="grid gap-2">
                        <label htmlFor={`${id}-name`} className="text-[14px] leading-5 font-medium">
                            Name{" "}
                            <span className="font-normal text-muted-foreground">(optional)</span>
                        </label>
                        <Input
                            id={`${id}-name`}
                            autoComplete="off"
                            maxLength={120}
                            placeholder="e.g. Stripe"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                            className="h-11 rounded-[8px] bg-surface-1 text-[14px]"
                        />
                    </div>
                    <div className="grid gap-2">
                        <label htmlFor={`${id}-url`} className="text-[14px] leading-5 font-medium">
                            Web address
                        </label>
                        <Input
                            id={`${id}-url`}
                            type="url"
                            inputMode="url"
                            autoComplete="off"
                            spellCheck={false}
                            placeholder="https://"
                            value={url}
                            onChange={(event) => setUrl(event.target.value)}
                            aria-invalid={error ? true : undefined}
                            aria-describedby={`${id}-hint`}
                            className="h-11 rounded-[8px] bg-surface-1 text-[14px]"
                        />
                        <p
                            id={`${id}-hint`}
                            className="text-[12px] leading-4 text-muted-foreground"
                        >
                            It starts with https://. After you add it, you choose which of its tools
                            your builds may use.
                        </p>
                    </div>
                    {error && (
                        <p role="alert" className="text-[12px] leading-4 text-destructive">
                            {error}
                        </p>
                    )}
                    <div className="flex flex-wrap justify-end gap-2">
                        <Link
                            href="/connectors"
                            className={cn(
                                buttonVariants({ variant: "secondary" }),
                                "rounded-[8px] px-4 text-[14px] max-sm:flex-1",
                            )}
                        >
                            Cancel
                        </Link>
                        <Button
                            type="submit"
                            disabled={busy}
                            className="rounded-[8px] px-4 text-[14px] max-sm:flex-1"
                        >
                            <Plus size={14} aria-hidden="true" />
                            {busy ? "Adding" : "Add service"}
                        </Button>
                    </div>
                </form>
            </div>
        </McpShell>
    );
}
