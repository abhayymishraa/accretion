"use client";

import { Button } from "@/components/ui/button";
import type { SkillDraft } from "@/types/skill.type";
import { Plus } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { useState } from "react";
import { toast } from "sonner";
import styles from "./skills.module.css";

// Ready-made skills a new library starts from. Each becomes the user's own, to edit like any other.
const STARTERS: SkillDraft[] = [
    {
        name: "brand-voice",
        description:
            "Use when writing any text people read on a page: headlines, buttons, empty states and errors. Not for code comments.",
        instructions: `Write the way a friendly expert talks: warm, direct, never stiff.

- Headlines: under eight words, say what the visitor gets.
- Buttons: start with a verb ("Start free", "Book a call"), never "Submit" or "Click here".
- Empty states: say what goes here and how to add the first one.
- Errors: say what happened and what to do next. Never blame the reader.
- No jargon, no exclamation marks, no filler like "seamless" or "cutting-edge".

Edit this skill to describe your own brand: its name, who it talks to, and words it always or never uses.`,
    },
    {
        name: "mobile-first",
        description:
            "Use when building or changing any page layout, so it works on a phone first and then widens for tablets and desktops.",
        instructions: `Design for a 390px wide phone first, then add room for wider screens.

- One column on a phone. Add grid columns only at wider breakpoints.
- Every tap target is at least 44px tall.
- Full-height sections use dvh, not vh, so the browser bar does not cut them off.
- Keep content clear of the notch and home bar with env(safe-area-inset-*).
- Nothing important appears only on hover.
- Form inputs use at least 16px text, so phones do not zoom in on focus.
- No sideways scrolling of the page at any width.`,
    },
    {
        name: "accessible-forms",
        description:
            "Use when building forms, inputs, sign-up or checkout flows, so everyone can fill them in, including keyboard and screen reader users.",
        instructions: `Every form must work for everyone.

- Every field has a visible label, not only a placeholder.
- Use the right input type and autocomplete (email, tel, name, current-password).
- Show each error next to its field, in words, and link it with aria-describedby.
- Never disable the submit button to hide errors: let people submit, then show what to fix and focus the first problem.
- Everything works with the keyboard alone, in a sensible tab order, with a visible focus ring.
- Mark required fields in the label, not with colour alone.`,
    },
];

/** One tap adds a ready-made skill; shown while the library is empty. */
export function StarterSkills({ onAdd }: { onAdd: (draft: SkillDraft) => Promise<string> }) {
    const [adding, setAdding] = useState("");
    const reduce = useReducedMotion();

    async function add(draft: SkillDraft) {
        setAdding(draft.name);
        const failure = await onAdd(draft);
        setAdding("");
        if (failure) toast.error(failure);
        else toast.success(`Added /${draft.name}. Edit it to make it yours.`);
    }

    return (
        <div className="border-t border-dashed border-border px-5 pt-4 pb-5">
            <p className="font-mono text-[11px] tracking-[0.1em] text-muted-foreground uppercase">
                Or start from one of these
            </p>
            <ul className="mt-3 grid gap-px border border-border bg-border sm:grid-cols-3">
                {STARTERS.map((starter) => (
                    <li key={starter.name} className="flex flex-col bg-background p-3">
                        <motion.code
                            layoutId={reduce ? undefined : `skill-chip-${starter.name}`}
                            className={`${styles.chip} self-start px-1.5 py-0.5 font-mono text-[12px] leading-none`}
                        >
                            /{starter.name}
                        </motion.code>
                        <p className="mt-2 line-clamp-3 flex-1 text-[12.5px] leading-[1.5] text-muted-foreground">
                            {starter.description}
                        </p>
                        <Button
                            variant="utility"
                            className="mt-2 -mb-1 -ml-2 h-11 self-start rounded-none px-2 text-[12.5px] pointer-fine:h-8"
                            disabled={adding !== ""}
                            onClick={() => add(starter)}
                            aria-label={`Add /${starter.name}`}
                        >
                            <Plus size={14} />
                            {adding === starter.name ? "Adding" : "Add"}
                        </Button>
                    </li>
                ))}
            </ul>
        </div>
    );
}
