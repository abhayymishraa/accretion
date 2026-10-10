"use client";

import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { PUBLIC } from "@/hooks/secrets/useProjectSecrets";
import { Globe, Lock, Trash2 } from "lucide-react";
import { useReducedMotion } from "motion/react";
import { useRef, useState } from "react";
import { KeyValueForm } from "./KeyValueForm";

// The Replace step under a row. It opens and closes on the shared disclosure (globals.css [data-disclosure]).
const STEP =
    "mx-2 mb-2.5 grid gap-2.5 rounded-[10px] border border-border bg-surface-1 p-3 sm:ml-7";
// The row folds before it is removed (globals.css [data-row]): 200ms, or at once with reduced motion.
const FOLD_MS = 200;

interface SecretRowProps {
    name: string;
    // Added after the list opened: it unfolds in (globals.css [data-row-new]).
    isNew: boolean;
    onReplace: (name: string, value: string) => Promise<string>;
    onRemove: (name: string) => Promise<string>;
}

/** One saved key on one line: its name, then Replace or Delete, confirmed in place. Its value is never shown. */
export function SecretRow({ name, isNew, onReplace, onRemove }: SecretRowProps) {
    const isPublic = PUBLIC.test(name);
    const Icon = isPublic ? Globe : Lock;
    const [step, setStep] = useState<"replace" | "remove" | null>(null);
    const [leaving, setLeaving] = useState(false);
    const [error, setError] = useState("");
    // Each opening of Replace starts a fresh form; it stays mounted while closing so it can fold away.
    const [opens, setOpens] = useState(0);
    const reduce = useReducedMotion();
    const trash = useRef<HTMLButtonElement>(null);
    // Back to the button that asked, so the keyboard does not lose its place.
    const cancel = () => {
        setStep(null);
        requestAnimationFrame(() => trash.current?.focus());
    };

    const remove = async () => {
        setLeaving(true);
        await new Promise((done) => setTimeout(done, reduce ? 0 : FOLD_MS));
        const failure = await onRemove(name);
        // Removed: the list drops the row. Refused: it unfolds with the reason on its line.
        if (failure) {
            setLeaving(false);
            setError(failure);
        }
    };

    return (
        <li
            data-row=""
            data-row-new={isNew ? "" : undefined}
            data-leaving={leaving ? "" : undefined}
        >
            <div className="rounded-[10px] transition-colors duration-150 pointer-fine:hover:bg-surface-2/60">
                <div className="flex min-h-10 items-center gap-2 py-1 pr-1 pl-2.5">
                    <Icon
                        size={14}
                        aria-hidden="true"
                        className={`shrink-0 ${isPublic ? "text-amber-700 dark:text-amber-300" : "text-muted-foreground"}`}
                    />
                    <p className="min-w-0 flex-1 font-mono text-[12.5px] wrap-anywhere text-foreground">
                        {name}
                        {isPublic && (
                            <span className="ml-2 rounded-full bg-amber-500/15 px-1.5 py-px font-sans text-[10px] font-semibold tracking-[0.05em] text-amber-800 uppercase dark:text-amber-300">
                                Public
                                <span className="sr-only">
                                    : built into the web page, anyone can read it
                                </span>
                            </span>
                        )}
                    </p>
                    {step === "remove" ? (
                        <div
                            data-row-confirm=""
                            role="group"
                            aria-label={`Delete ${name}`}
                            className="flex shrink-0 items-center gap-1.5"
                            onKeyDown={(event) => {
                                if (event.key === "Escape") cancel();
                            }}
                        >
                            <span className="text-xs text-muted-foreground">Delete?</span>
                            <Button
                                variant="utility"
                                // The safe choice takes focus; Escape does the same.
                                autoFocus
                                disabled={leaving}
                                onClick={cancel}
                            >
                                Cancel
                            </Button>
                            <Button
                                disabled={leaving}
                                onClick={() => void remove()}
                                className="h-8 bg-destructive px-3 text-destructive-foreground pointer-coarse:h-11 pointer-fine:hover:bg-destructive/90"
                            >
                                Delete
                            </Button>
                        </div>
                    ) : (
                        <div className="flex shrink-0 items-center gap-0.5">
                            <Button
                                variant="utility"
                                aria-expanded={step === "replace"}
                                onClick={() => {
                                    if (step !== "replace") setOpens(opens + 1);
                                    setStep(step === "replace" ? null : "replace");
                                }}
                            >
                                Replace
                            </Button>
                            <Button
                                ref={trash}
                                variant="icon"
                                aria-label={`Delete ${name}`}
                                onClick={() => {
                                    setError("");
                                    setStep("remove");
                                }}
                            >
                                <Trash2 size={15} aria-hidden="true" />
                            </Button>
                        </div>
                    )}
                </div>
                <ErrorBox
                    message={error}
                    className="rounded-none border-0 bg-transparent px-2.5 pt-0 pb-2 text-xs sm:pl-7"
                />
                {opens > 0 && (
                    <div data-disclosure={step === "replace" ? "open" : ""}>
                        <div className={STEP}>
                            <KeyValueForm
                                key={opens}
                                name={name}
                                onCancel={() => setStep(null)}
                                onSave={async (key, value) => {
                                    const failure = await onReplace(key, value);
                                    if (!failure) setStep(null);
                                    return failure;
                                }}
                            />
                        </div>
                    </div>
                )}
            </div>
        </li>
    );
}
