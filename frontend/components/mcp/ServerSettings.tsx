"use client";

import type { Connections } from "@/hooks/connections/useConnections";
import type { Connection, ConnectionAuth } from "@/types/connection.type";
import { ImageUp } from "lucide-react";
import { useId, useState } from "react";
import { KeyForm } from "./KeyForm";
import styles from "./mcp.module.css";

// The server refuses anything larger; checked here first so the user hears why at once.
const ICON_BYTES = 32_768;
const CHOICES: { auth: ConnectionAuth; label: string }[] = [
    { auth: "none", label: "None" },
    { auth: "header", label: "API key" },
    { auth: "oauth", label: "Sign in" },
];
const ROW =
    "flex min-h-16 flex-wrap items-center justify-between gap-x-4 gap-y-3 px-4 py-3 max-sm:flex-col max-sm:items-stretch";
// A segment's text; the selected background is one thumb behind them that slides to the choice.
const PILL =
    "relative min-h-9 flex-1 cursor-pointer rounded-[6px] px-3 text-[13px] [transition:color_130ms_ease,scale_100ms_var(--ease-out)] active:scale-[0.97] motion-reduce:active:scale-100 focus-visible:outline-2 focus-visible:outline-ring pointer-coarse:min-h-11 aria-pressed:text-foreground text-muted-foreground pointer-fine:hover:text-foreground";

/** How a server signs in (for one added by address, which has no catalog entry to say so), and its logo. */
export function ServerSettings({
    server,
    custom,
    connections,
}: {
    server: Connection;
    custom: boolean;
    connections: Connections;
}) {
    const id = useId();
    // The choice the user is making, until the server saves it: a key waits for the form.
    const [picked, setPicked] = useState<ConnectionAuth | null>(null);
    const [error, setError] = useState("");
    const current = picked ?? server.auth;

    async function choose(auth: ConnectionAuth) {
        setError("");
        if (auth === "header") return setPicked("header");
        setPicked(null);
        if (auth === "oauth") return connections.signIn(server.id);
        if (server.auth !== "none") await connections.clearKey(server.id);
    }

    async function upload(file: File) {
        if (file.size > ICON_BYTES) return setError("Use an image of 32 KB or less.");
        const reader = new FileReader();
        reader.onload = async () =>
            setError(await connections.saveIcon(server.id, String(reader.result)));
        reader.readAsDataURL(file);
    }

    return (
        <section className="mt-3 divide-y divide-border rounded-[12px] border border-border bg-surface-1">
            {custom && (
                <div className={ROW}>
                    <div className="min-w-0">
                        <p id={`${id}-auth`} className="text-[14px] leading-5 font-medium">
                            Authentication
                        </p>
                        <p className="text-[12px] leading-4 text-foreground/70">
                            Found when you added it. Change it if the service&apos;s guide says
                            otherwise.
                        </p>
                    </div>
                    <div
                        role="group"
                        aria-labelledby={`${id}-auth`}
                        className="relative flex rounded-[8px] border border-border bg-surface-2 p-1 sm:w-[264px]"
                    >
                        <span
                            aria-hidden="true"
                            className="absolute inset-y-1 left-1 w-[calc((100%-8px)/3)] rounded-[6px] bg-surface-3 transition-transform duration-200 ease-[var(--ease-out)] motion-reduce:transition-none"
                            style={{
                                transform: `translateX(${CHOICES.findIndex((choice) => choice.auth === current) * 100}%)`,
                            }}
                        />
                        {CHOICES.map(({ auth, label }) => (
                            <button
                                key={auth}
                                type="button"
                                aria-pressed={current === auth}
                                onClick={() => void choose(auth)}
                                className={PILL}
                            >
                                {label}
                            </button>
                        ))}
                    </div>
                </div>
            )}
            {picked === "header" && (
                <div className="p-3">
                    <KeyForm
                        server={server}
                        saveKey={async (...args) => {
                            const failure = await connections.saveKey(...args);
                            if (!failure) setPicked(null);
                            return failure;
                        }}
                        onCancel={() => setPicked(null)}
                    />
                </div>
            )}
            <div className={ROW}>
                <div className="min-w-0">
                    <p className="text-[14px] leading-5 font-medium">Logo</p>
                    <p className="text-[12px] leading-4 text-foreground/70">
                        PNG, JPEG, WebP, GIF, SVG or ICO, up to 32 KB. It replaces the one shown.
                    </p>
                </div>
                <label className="inline-flex min-h-9 shrink-0 cursor-pointer items-center justify-center gap-1.5 rounded-[8px] border border-border bg-surface-2 px-3 text-[13px] [transition:background-color_130ms_ease,scale_100ms_var(--ease-out)] active:scale-[0.97] motion-reduce:active:scale-100 focus-within:outline-2 focus-within:outline-ring pointer-coarse:min-h-11 pointer-fine:hover:bg-surface-3">
                    <ImageUp size={14} aria-hidden="true" className="text-muted-foreground" />
                    Upload logo
                    <input
                        type="file"
                        accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml,image/x-icon,.ico"
                        className="sr-only"
                        onChange={(event) => {
                            const file = event.target.files?.[0];
                            event.target.value = "";
                            if (file) void upload(file);
                        }}
                    />
                </label>
            </div>
            {error && (
                <p role="alert" className={`${styles.ask} px-4 py-3 text-[13px] text-destructive`}>
                    {error}
                </p>
            )}
        </section>
    );
}
