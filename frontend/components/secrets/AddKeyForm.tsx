"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PUBLIC, SECRET_NAME, secretName } from "@/hooks/secrets/useProjectSecrets";
import { Eye, EyeOff } from "lucide-react";
import { useId, useState } from "react";

// A name or value that reads as private, saved under a public name: offer to keep it private.
const LOOKS_PRIVATE = /SECRET|PRIVATE|PASSWORD|TOKEN/;
const PRIVATE_VALUE = /^(sk[-_]|rk_|whsec_)/;
// Compact on a mouse; 44px and 16px on touch, below which iOS zooms into the field.
const FIELD = "h-8 font-mono pointer-coarse:h-11 sm:text-[13px]";

interface AddKeyFormProps {
    saved: string[];
    managed: string[];
    onSave: (name: string, value: string) => Promise<string>;
}

/** One row, always open: a name typed in plain words, a value pasted once, Save. */
export function AddKeyForm({ saved, managed, onSave }: AddKeyFormProps) {
    const id = useId();
    const [typed, setTyped] = useState("");
    const [value, setValue] = useState("");
    const [shown, setShown] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const name = secretName(typed);
    const EyeIcon = shown ? EyeOff : Eye;
    const taken = managed.includes(name)
        ? `${name} is set by Accretion. Pick another name.`
        : saved.includes(name)
          ? `${name} is already saved. Use Replace on it.`
          : "";
    const risky =
        PUBLIC.test(name) && (LOOKS_PRIVATE.test(name) || PRIVATE_VALUE.test(value.trim()));
    // One line under the row, only when there is something to say.
    const note = error || taken;

    return (
        <form
            className="grid gap-1.5"
            noValidate
            onSubmit={async (event) => {
                event.preventDefault();
                if (!SECRET_NAME.test(name))
                    return setError(
                        name
                            ? "A name starts with a letter or _ and has at most 128 characters."
                            : "Give the key a name.",
                    );
                if (taken) return setError(taken);
                if (!value) return setError("Paste the value first.");
                setBusy(true);
                const failure = await onSave(name, value);
                setBusy(false);
                if (failure) return setError(failure);
                setTyped("");
                setValue("");
                setShown(false);
            }}
        >
            <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-end">
                <div className="grid gap-1">
                    <label htmlFor={`${id}-name`} className="text-xs text-muted-foreground">
                        Key
                    </label>
                    <Input
                        id={`${id}-name`}
                        placeholder="e.g. STRIPE_SECRET_KEY"
                        autoComplete="off"
                        autoCapitalize="characters"
                        spellCheck={false}
                        value={typed}
                        onChange={(event) => {
                            setTyped(event.target.value);
                            setError("");
                        }}
                        onBlur={() => setTyped(name)}
                        className={FIELD}
                    />
                </div>
                <div className="grid gap-1">
                    <label htmlFor={`${id}-value`} className="text-xs text-muted-foreground">
                        Value
                    </label>
                    <div className="relative flex">
                        <Input
                            id={`${id}-value`}
                            type={shown ? "text" : "password"}
                            autoComplete="off"
                            spellCheck={false}
                            value={value}
                            onChange={(event) => {
                                setValue(event.target.value);
                                setError("");
                            }}
                            className={`pr-9 pointer-coarse:pr-11 ${FIELD}`}
                        />
                        <button
                            type="button"
                            onClick={() => setShown(!shown)}
                            aria-label={shown ? "Hide value" : "Show value"}
                            aria-pressed={shown}
                            className="absolute inset-y-px right-px grid w-8 cursor-pointer place-items-center rounded-r-[8px] text-muted-foreground focus-visible:outline-2 focus-visible:outline-ring pointer-coarse:w-11"
                        >
                            <EyeIcon size={14} aria-hidden="true" />
                        </button>
                    </div>
                </div>
                <Button type="submit" disabled={busy} className="h-8 pointer-coarse:h-11">
                    {busy ? "Saving…" : "Save"}
                </Button>
            </div>
            <div aria-live="polite" className="text-xs leading-[1.45]">
                {note ? (
                    <p role="alert" className="text-destructive">
                        {note}
                    </p>
                ) : risky ? (
                    <p className="text-amber-800 dark:text-amber-300">
                        Public: {name.match(PUBLIC)?.[0]} keys are built into the web page, where
                        anyone can read them.{" "}
                        <button
                            type="button"
                            onClick={() => setTyped(name.replace(PUBLIC, ""))}
                            className="cursor-pointer font-medium underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-ring pointer-coarse:min-h-11"
                        >
                            Make it private
                        </button>
                    </p>
                ) : typed && name !== typed ? (
                    <p className="text-muted-foreground">Saved as {name}</p>
                ) : null}
            </div>
        </form>
    );
}
