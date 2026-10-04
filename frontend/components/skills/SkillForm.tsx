"use client";

import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Input } from "@/components/ui/input";
import type { SkillDetail, SkillDraft } from "@/types/skill.type";
import { MarkdownField } from "./MarkdownField";
import { useState, type FormEvent, type ReactNode } from "react";
import { SKILL_NAME } from "@/hooks/chat/useComposerMenu";

// The server's limits, repeated so a mistake shows before the round trip.
const NAME_MAX = 64;
const DESCRIPTION_MAX = 1024;
const NAME_PATTERN = new RegExp(`${SKILL_NAME.source}$`);

const FIELD =
    "w-full rounded-none border border-border bg-surface-2 px-3 py-2.5 text-[16px] leading-[1.55] text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-input focus-visible:ring-[3px] focus-visible:ring-ring/35 aria-invalid:border-destructive sm:text-[14.5px]";

type Errors = Partial<Record<keyof SkillDraft, string>>;

function validate(draft: SkillDraft, creating: boolean): Errors {
    const errors: Errors = {};
    if (creating && !draft.name) errors.name = "Give the skill a name.";
    else if (creating && !NAME_PATTERN.test(draft.name))
        errors.name =
            "Use lowercase letters, numbers and hyphens, starting with a letter or number.";
    if (!draft.description.trim()) errors.description = "Say when Accretion should use this skill.";
    if (!draft.instructions.trim())
        errors.instructions = "Write the instructions Accretion should follow.";
    return errors;
}

interface SkillFormProps {
    /** The skill being edited; null when creating one. */
    initial: SkillDetail | null;
    onCancel: () => void;
    /** Returns the error to show, or "". */
    onSubmit: (draft: SkillDraft) => Promise<string>;
}

export function SkillForm({ initial, onCancel, onSubmit }: SkillFormProps) {
    const creating = initial === null;
    const [draft, setDraft] = useState<SkillDraft>(
        initial ?? { name: "", description: "", instructions: "" },
    );
    const [errors, setErrors] = useState<Errors>({});
    const [failure, setFailure] = useState("");
    const [saving, setSaving] = useState(false);

    function update(field: keyof SkillDraft, value: string) {
        setDraft((current) => ({ ...current, [field]: value }));
        if (errors[field]) setErrors((current) => ({ ...current, [field]: undefined }));
    }

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const found = validate(draft, creating);
        setErrors(found);
        // validate() adds errors in field order, so the first key is the first field to fix.
        const first = Object.keys(found)[0];
        if (first) {
            document.getElementById(`skill-${first}`)?.focus();
            return;
        }
        setSaving(true);
        setFailure(await onSubmit(draft));
        setSaving(false);
    }

    return (
        <form noValidate onSubmit={submit} className="flex flex-1 flex-col">
            <div className="flex flex-col gap-7 px-5 py-6 sm:px-7">
                <Field
                    id="skill-name"
                    label="Name"
                    hint="Lowercase letters, numbers and hyphens. You type it after / in chat."
                    count={creating ? `${draft.name.length}/${NAME_MAX}` : undefined}
                    error={errors.name}
                >
                    <div className="flex">
                        <span className="grid w-10 shrink-0 place-items-center border border-r-0 border-border bg-surface-1 font-mono text-[15px] text-primary">
                            /
                        </span>
                        <Input
                            id="skill-name"
                            value={draft.name}
                            // Spaces and capitals are the usual slip; fix them while typing.
                            onChange={(e) =>
                                update("name", e.target.value.toLowerCase().replace(/\s+/g, "-"))
                            }
                            maxLength={NAME_MAX}
                            placeholder="my-skill"
                            autoComplete="off"
                            autoCapitalize="none"
                            spellCheck={false}
                            disabled={!creating}
                            aria-invalid={Boolean(errors.name)}
                            aria-describedby="skill-name-hint skill-name-error"
                            className="h-11 rounded-none font-mono"
                        />
                    </div>
                </Field>
                <Field
                    id="skill-description"
                    label="Description"
                    hint="Start with “Use when”, then say what it covers and where it stops."
                    count={`${draft.description.length}/${DESCRIPTION_MAX}`}
                    error={errors.description}
                >
                    <textarea
                        id="skill-description"
                        value={draft.description}
                        // The description is one line in the model's catalog, so line breaks become spaces.
                        onChange={(e) =>
                            update("description", e.target.value.replace(/[\r\n]+/g, " "))
                        }
                        maxLength={DESCRIPTION_MAX}
                        rows={3}
                        placeholder="Use when writing page copy, so it matches our brand voice. Not for code."
                        aria-invalid={Boolean(errors.description)}
                        aria-describedby="skill-description-hint skill-description-error"
                        className={`${FIELD} resize-y`}
                    />
                </Field>
                <Field
                    id="skill-instructions"
                    label="Instructions"
                    hint="What Accretion should do when this skill applies. Plain sentences work best; Markdown works too."
                    error={errors.instructions}
                >
                    <MarkdownField
                        id="skill-instructions"
                        value={draft.instructions}
                        onChange={(value) => update("instructions", value)}
                        rows={10}
                        placeholder={
                            "Write in a warm, direct tone.\nKeep headlines under eight words."
                        }
                        aria-invalid={Boolean(errors.instructions)}
                        aria-describedby="skill-instructions-hint skill-instructions-error"
                        className={`${FIELD} min-h-48 resize-y`}
                    />
                </Field>
                <ErrorBox message={failure} />
            </div>
            <div className="sticky bottom-0 mt-auto grid grid-cols-2 gap-px border-t border-border bg-border">
                <Button
                    type="button"
                    variant="secondary"
                    onClick={onCancel}
                    className="h-13 rounded-none border-0 bg-background pointer-coarse:h-13"
                >
                    Cancel
                </Button>
                <Button
                    type="submit"
                    disabled={saving}
                    className="h-13 rounded-none pointer-coarse:h-13"
                >
                    {saving ? "Saving" : creating ? "Create skill" : "Save changes"}
                </Button>
            </div>
        </form>
    );
}

function Field(props: {
    id: string;
    label: string;
    hint: string;
    count?: string;
    error?: string;
    children: ReactNode;
}) {
    return (
        <div className="flex flex-col gap-2">
            <div className="flex items-baseline justify-between gap-3">
                <label htmlFor={props.id} className="text-[14px] font-semibold">
                    {props.label}
                </label>
                {props.count && (
                    <span data-numeric="" className="font-mono text-[11px] text-muted-foreground">
                        {props.count}
                    </span>
                )}
            </div>
            {props.children}
            <p
                id={`${props.id}-hint`}
                className="text-[12.5px] leading-[1.5] text-muted-foreground"
            >
                {props.hint}
            </p>
            <p
                id={`${props.id}-error`}
                data-error-box={props.error ? "shown" : ""}
                role="alert"
                className="text-[12.5px] leading-[1.5] text-destructive"
            >
                {props.error}
            </p>
        </div>
    );
}
