"use client";

import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Skeleton } from "@/components/ui/skeleton";
import type { ProjectSkills } from "@/hooks/skills/useProjectSkills";
import type { ProjectSkill } from "@/types/skill.type";
import { ArrowUpRight, Check } from "lucide-react";
import Link from "next/link";
import { Fragment, useEffect, useState, type ReactNode } from "react";
import styles from "./skills.module.css";
import { SkillSearch, TOOLBAR_LINK } from "./SkillFilters";
import { matches } from "./SkillSections";
import { Required, SkillSwitch, STATUS } from "./SkillSwitch";

// The workspace's small filled action: the utility button on a surface.
const SMALL =
    "h-7 shrink-0 rounded-[6px] px-2.5 text-[11.5px] bg-surface-2 text-foreground pointer-fine:hover:bg-accent pointer-fine:hover:text-accent-foreground";

function Section({
    title,
    note,
    skills,
    action,
}: {
    title: string;
    note: string;
    skills: ProjectSkill[];
    action: (skill: ProjectSkill) => ReactNode;
}) {
    if (!skills.length) return null;
    return (
        <section aria-label={title} className="px-2 pb-3">
            {/* Sticks while its rows scroll, so a long list always says which group you are in. */}
            <div className="sticky top-0 z-10 flex items-baseline justify-between gap-3 bg-surface-1 px-2 pt-4 pb-1.5">
                <h3 className="text-[12px] font-medium text-foreground">
                    {title}
                    <span data-numeric="" className="ml-1.5 text-muted-foreground tabular-nums">
                        {skills.length}
                    </span>
                </h3>
                <span className="text-[11.5px] text-muted-foreground">{note}</span>
            </div>
            <ul className="flex flex-col">
                {skills.map((skill, index) => (
                    <Fragment key={skill.name}>
                        {/* Built-ins arrive grouped: a subheading wherever the subcategory changes. */}
                        {skill.subcategory &&
                            skill.subcategory !== skills[index - 1]?.subcategory && (
                                <li className="px-2 pt-2 pb-0.5 text-[11px] text-muted-foreground">
                                    {skill.subcategory}
                                </li>
                            )}
                        <li className="flex items-center gap-3 rounded-[8px] px-2 py-1.5 [transition:background-color_130ms_ease] pointer-fine:hover:bg-surface-2">
                            <div
                                className={`min-w-0 flex-1 [transition:opacity_150ms_ease] ${skill.enabled ? "" : "opacity-50"}`}
                            >
                                <p className="truncate font-mono text-[12px] text-foreground">
                                    /{skill.name}
                                </p>
                                <p className="mt-0.5 line-clamp-2 text-[12px] leading-[1.5] text-muted-foreground">
                                    {skill.description}
                                </p>
                            </div>
                            {action(skill)}
                        </li>
                    </Fragment>
                ))}
            </ul>
        </section>
    );
}

/** The workspace's Skills tab: the project's own skills (always on), then every other skill, on or
 * off for this project. */
export function ProjectSkillsPanel({ projectSkills }: { projectSkills: ProjectSkills }) {
    const { skills, error, retry, ensureLoaded, setEnabled, saveToLibrary } = projectSkills;
    const [query, setQuery] = useState("");
    const [saving, setSaving] = useState("");
    // Only the skill saved here animates its "In library"; ones saved before just show it.
    const [justSaved, setJustSaved] = useState("");
    // Fetched the first time the tab opens, as the "/" menu does.
    useEffect(() => {
        ensureLoaded();
    }, [ensureLoaded]);
    const shown = (skills ?? []).filter((skill) => matches(skill, query));
    const of = (source: ProjectSkill["source"]) => shown.filter((skill) => skill.source === source);
    async function save(name: string) {
        setSaving(name);
        setJustSaved(name);
        await saveToLibrary(name);
        setSaving("");
    }
    // A required skill, or one turned off for the whole account, shows why it has no switch here
    // instead of a control that would do nothing.
    const toggle = (skill: ProjectSkill) =>
        skill.required ? (
            <Required />
        ) : skill.off_everywhere ? (
            <Link
                href="/skills"
                className={`${STATUS} underline-offset-2 [transition:color_130ms_ease,scale_100ms_var(--ease-out)] active:scale-[0.97] motion-reduce:active:scale-100 focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:text-foreground pointer-fine:hover:underline`}
            >
                Off in your library
                <ArrowUpRight size={12} aria-hidden="true" />
            </Link>
        ) : (
            <SkillSwitch
                checked={skill.enabled}
                label={`Use /${skill.name} in this project`}
                onChange={(on) => setEnabled(skill.name, on)}
            />
        );

    return (
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-surface-1">
            <header className="border-b border-border px-4 py-3">
                <h2 className="text-sm font-semibold text-foreground">Skills in this project</h2>
                <p className="mt-1 max-w-[62ch] text-xs leading-[1.5] text-pretty text-muted-foreground">
                    Choose which skills Accretion can use in this project. A skill you turn off is
                    never used here, even with /name. Your other projects are not affected.
                </p>
                {/* One toolbar row: the search and the way out to the library share height, corners and surface. */}
                <div className="mt-3 flex items-center gap-2">
                    <SkillSearch
                        value={query}
                        onChange={setQuery}
                        className="h-8 rounded-[6px] text-[12.5px] sm:text-[12.5px]"
                    />
                    <Link href="/skills" className={TOOLBAR_LINK}>
                        Library
                        <ArrowUpRight
                            size={13}
                            aria-hidden="true"
                            className="text-muted-foreground"
                        />
                    </Link>
                </div>
            </header>
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain pb-[env(safe-area-inset-bottom)]">
                {error && !skills ? (
                    <div className="p-4">
                        <ErrorBox message={error}>
                            <Button
                                variant="utility"
                                type="button"
                                onClick={retry}
                                className={SMALL}
                            >
                                Try again
                            </Button>
                        </ErrorBox>
                    </div>
                ) : skills && !shown.length ? (
                    <p className="px-4 py-6 text-xs text-muted-foreground">
                        No skills match &ldquo;{query.trim()}&rdquo;.
                    </p>
                ) : skills ? (
                    <div data-loaded-in="">
                        <Section
                            title="In this project"
                            note="Always on"
                            skills={of("project")}
                            action={(skill) =>
                                skill.in_library ? (
                                    <span
                                        className={`${STATUS} ${skill.name === justSaved ? styles.settle : ""}`}
                                    >
                                        <Check size={13} aria-hidden="true" />
                                        In library
                                    </span>
                                ) : (
                                    <Button
                                        variant="utility"
                                        type="button"
                                        onClick={() => save(skill.name)}
                                        disabled={saving !== ""}
                                        className={`${SMALL} disabled:opacity-60`}
                                    >
                                        {saving === skill.name ? "Saving" : "Save to library"}
                                    </Button>
                                )
                            }
                        />
                        <Section
                            title="Your skills"
                            note="From your library"
                            skills={of("library")}
                            action={toggle}
                        />
                        {/* Built-ins by category, in the order the API groups them. */}
                        {[...new Set(of("builtin").map((skill) => skill.category))].map(
                            (category) => (
                                <Section
                                    key={category}
                                    title={category ?? "Built in"}
                                    note="Included with Accretion"
                                    skills={of("builtin").filter(
                                        (skill) => skill.category === category,
                                    )}
                                    action={toggle}
                                />
                            ),
                        )}
                    </div>
                ) : (
                    <div className="flex flex-col gap-1.5 p-4" aria-label="Loading skills">
                        {[0, 1, 2, 3, 4].map((row) => (
                            <Skeleton key={row} className="h-12 rounded-[8px]" />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
