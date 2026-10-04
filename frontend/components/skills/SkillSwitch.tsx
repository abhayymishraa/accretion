"use client";

import type { SkillSummary } from "@/types/skill.type";
import { Lock } from "lucide-react";

/** On or off for one skill: a pill switch in a 44px touch target, its track on the right edge. */
export function SkillSwitch({
    checked,
    label,
    onChange,
}: {
    checked: boolean;
    /** What the switch controls, for screen readers: "Use /name in this project". */
    label: string;
    onChange: (checked: boolean) => void;
}) {
    return (
        <button
            type="button"
            role="switch"
            aria-checked={checked}
            aria-label={label}
            onClick={() => onChange(!checked)}
            className="group flex size-11 shrink-0 cursor-pointer items-center justify-end rounded-[8px] focus-visible:outline-2 focus-visible:outline-ring"
        >
            <span
                className={`relative h-[18px] w-8 rounded-full [transition:background-color_150ms_ease,scale_100ms_var(--ease-out)] group-active:scale-[0.96] motion-reduce:transition-none motion-reduce:group-active:scale-100 ${checked ? "bg-primary" : "bg-muted-foreground/40"}`}
            >
                <span
                    className={`absolute top-[2px] left-[2px] size-3.5 rounded-full bg-background shadow-sm [transition:transform_150ms_var(--ease-out)] motion-reduce:transition-none ${checked ? "translate-x-3.5" : ""}`}
                />
            </span>
        </button>
    );
}

// A status in a control's place: "Required", "In library", "Off in your library". 44px tall, like the switch.
export const STATUS = "flex h-11 shrink-0 items-center gap-1 text-[11.5px] text-muted-foreground";

/** A platform skill's badge where its switch would be. */
export function Required() {
    return (
        <span className={STATUS}>
            <Lock size={12} aria-hidden="true" />
            Required
        </span>
    );
}

/** The account-wide control on the Skills page: a switch, or a lock for a skill Accretion keeps on. */
export function EverywhereToggle({
    skill,
    onToggle,
}: {
    skill: SkillSummary;
    onToggle: (name: string, enabled: boolean) => void;
}) {
    if (skill.required) return <Required />;
    return (
        <SkillSwitch
            checked={!skill.off_everywhere}
            label={`Use /${skill.name} in all your projects`}
            onChange={(on) => onToggle(skill.name, on)}
        />
    );
}
