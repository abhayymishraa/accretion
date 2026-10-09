"use client";

import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Input } from "@/components/ui/input";
import { useId, useState } from "react";

interface KeyValueFormProps {
    name: string;
    onSave: (name: string, value: string) => Promise<string>;
    onCancel?: () => void;
    // The chat card puts the field and Save on one line; Replace stacks them with a note.
    inline?: boolean;
}

/** A new value for one named key, in a password field. Replace and the chat card both use it. */
export function KeyValueForm({ name, onSave, onCancel, inline = false }: KeyValueFormProps) {
    const id = useId();
    const [value, setValue] = useState("");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const submit = (
        <Button type="submit" disabled={busy}>
            {busy ? "Saving…" : inline ? "Save" : "Save new value"}
        </Button>
    );

    return (
        <form
            className="grid gap-2.5"
            noValidate
            onSubmit={async (event) => {
                event.preventDefault();
                if (!value.trim()) return setError("Paste the value first.");
                setBusy(true);
                const failure = await onSave(name, value);
                setBusy(false);
                setError(failure);
                if (!failure) setValue("");
            }}
        >
            <label htmlFor={id} className={inline ? "sr-only" : "text-[13px] font-medium"}>
                New value for <span className="font-mono">{name}</span>
            </label>
            <div className="flex gap-2">
                <Input
                    id={id}
                    type="password"
                    autoComplete="off"
                    spellCheck={false}
                    value={value}
                    onChange={(event) => setValue(event.target.value)}
                    aria-invalid={error ? true : undefined}
                    className="font-mono h-8 pointer-coarse:h-11 sm:text-[13px]"
                />
                {inline && submit}
            </div>
            {!inline && (
                <p className="text-[12.5px] leading-[1.5] text-muted-foreground">
                    The old value is thrown away. It can&apos;t be brought back.
                </p>
            )}
            <ErrorBox
                message={error}
                className="rounded-none border-0 bg-transparent p-0 text-[12.5px]"
            />
            {!inline && (
                <div className="flex flex-wrap gap-2">
                    {submit}
                    <Button type="button" variant="secondary" onClick={onCancel} disabled={busy}>
                        Cancel
                    </Button>
                </div>
            )}
        </form>
    );
}
