"use client";

import { Button } from "@/components/ui/button";
import { useProjectSecrets } from "@/hooks/secrets/useProjectSecrets";
import { Check } from "lucide-react";
import { useParams } from "next/navigation";
import { KeyValueForm } from "./KeyValueForm";

/**
 * The keys a builder's question asks for: a value field per key, saved as a project key. Once all are saved,
 * Continue answers with their names, so a value never enters the chat.
 */
export function SecretRequest({
    names,
    busy,
    onAnswer,
}: {
    names: string[];
    busy: boolean;
    onAnswer: (text: string) => void;
}) {
    const { id: projectId = "" } = useParams<{ id?: string }>();
    const { secrets, save } = useProjectSecrets(projectId);
    const saved = new Set(secrets?.secrets);
    const done = names.filter((name) => saved.has(name)).length;

    return (
        <div role="group" aria-label="Keys the builder needs" className="border-t border-hairline">
            <ul className="divide-y divide-hairline">
                {names.map((name) => {
                    const ready = saved.has(name);
                    return (
                        <li key={name} className="grid gap-2 px-4 py-3">
                            <div className="flex min-h-6 items-center gap-2">
                                <span className="min-w-0 flex-1 font-mono text-[12.5px] wrap-anywhere">
                                    {name}
                                </span>
                                {ready && (
                                    <span
                                        // Fades in once (globals.css [data-loaded-in]): the build can go on now.
                                        data-loaded-in=""
                                        className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 dark:text-emerald-400"
                                    >
                                        <Check size={13} aria-hidden="true" />
                                        Saved
                                    </span>
                                )}
                            </div>
                            {!ready && secrets && <KeyValueForm name={name} inline onSave={save} />}
                        </li>
                    );
                })}
            </ul>
            <div className="flex flex-wrap items-center gap-3 border-t border-hairline bg-surface-1 px-4 py-2.5">
                <p className="mr-auto text-xs text-muted-foreground">
                    <span data-numeric="" className="tabular-nums">
                        {done} of {names.length}
                    </span>{" "}
                    saved. Only your app gets the values; the builder sees the names.
                </p>
                <Button
                    disabled={busy || done < names.length}
                    onClick={() => onAnswer(`I saved ${names.join(", ")}.`)}
                >
                    {busy ? "Saving…" : "Continue"}
                </Button>
            </div>
        </div>
    );
}
