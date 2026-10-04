"use client";

import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Skeleton } from "@/components/ui/skeleton";
import type { SkillDraft, SkillSummary } from "@/types/skill.type";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import Image from "next/image";
import type { CSSProperties, ReactNode } from "react";
import { type AddSkillActions, AddSkillMenu } from "./AddSkillMenu";
import { SkillCard } from "./SkillCard";
import styles from "./skills.module.css";
import { StarterSkills } from "./StarterSkills";
import { EverywhereToggle } from "./SkillSwitch";

const GRID =
    "grid gap-px border border-border bg-border sm:grid-cols-2 sm:[&>*:last-child:nth-child(odd)]:col-span-2";
// Stagger only the first rows; cards further down arrive with them, not after.
export const slot = (index: number) => ({ "--i": Math.min(index, 8) }) as CSSProperties;

/** The search box's filter: a case-blind match on the name or the description. */
export function matches(skill: SkillSummary, query: string) {
    const needle = query.trim().toLowerCase();
    return (
        !needle || skill.name.includes(needle) || skill.description.toLowerCase().includes(needle)
    );
}

function NoMatch({ query }: { query: string }) {
    return (
        <p className="border border-dashed border-border px-5 py-4 text-[13px] text-muted-foreground">
            No skills match &ldquo;{query.trim()}&rdquo;.
        </p>
    );
}

function SectionHeading({
    id,
    title,
    count,
    children,
}: {
    id: string;
    title: string;
    count: number | null;
    children: ReactNode;
}) {
    return (
        <div className="mb-4 min-w-0">
            <h2
                id={id}
                className="flex items-baseline gap-3 text-[18px] font-medium tracking-[-0.1px]"
            >
                {title}
                {count !== null && (
                    <span
                        data-numeric=""
                        className="font-mono text-[12px] font-normal tracking-normal text-muted-foreground"
                    >
                        [{String(count).padStart(2, "0")}]
                    </span>
                )}
            </h2>
            {children}
        </div>
    );
}

/** Loading shape: the same compartments the cards will fill. */
function GridSkeleton({ cells }: { cells: number }) {
    return (
        <div className={GRID} aria-hidden="true">
            {Array.from({ length: cells }, (_, index) => (
                <div key={index} className="flex flex-col gap-3 bg-background p-5">
                    <Skeleton className="h-5 w-32 rounded-none" />
                    <Skeleton className="h-3.5 w-full rounded-none" />
                    <Skeleton className="h-3.5 w-4/5 rounded-none" />
                </div>
            ))}
        </div>
    );
}

interface WorkspaceProps {
    skills: SkillSummary[] | null;
    query: string;
    add: AddSkillActions;
    onStarter: (draft: SkillDraft) => Promise<string>;
    onPreview: (skill: SkillSummary) => void;
    onEdit: (id: string) => void;
    onDelete: (id: string) => Promise<string>;
    onToggle: (name: string, enabled: boolean) => void;
}

/** The user's own skills, or an empty state that says how to add one. */
export function WorkspaceSkills({
    skills,
    query,
    add,
    onStarter,
    onPreview,
    onEdit,
    onDelete,
    onToggle,
}: WorkspaceProps) {
    const shown = (skills ?? []).filter((skill) => matches(skill, query));
    const reduce = useReducedMotion();
    // Empty state and list swap with a fade when the first skill arrives (however it was added) or
    // the last one goes. Not on page load: the switch starts after the skeleton, initial={false}.
    const swap = {
        initial: reduce ? { opacity: 0 } : { opacity: 0, scale: 0.97 },
        animate: { opacity: 1, scale: 1 },
        exit: { opacity: 0, transition: { duration: 0.14 } },
        transition: { duration: 0.2, ease: [0.23, 1, 0.32, 1] as const },
    };
    return (
        <section
            aria-labelledby="own-title"
            // popLayout lifts the leaving state out of the flow; it is placed against this section.
            className={`${styles.rise} relative mb-10`}
            style={slot(2)}
        >
            <SectionHeading id="own-title" title="Your skills" count={skills?.length ?? null}>
                <p className="mt-1.5 text-[13.5px] text-muted-foreground">
                    Available in every project you build.
                </p>
            </SectionHeading>
            {skills === null ? (
                <GridSkeleton cells={2} />
            ) : (
                <AnimatePresence initial={false} mode="popLayout">
                    {skills.length === 0 ? (
                        <motion.div
                            key="empty"
                            {...swap}
                            className="border border-dashed border-border"
                        >
                            <div className="grid gap-px sm:grid-cols-[112px_minmax(0,1fr)]">
                                <div className="grid place-items-center px-4 pt-6 sm:py-5">
                                    <Image
                                        src="/skills/empty-orbit.webp"
                                        alt=""
                                        width={72}
                                        height={72}
                                    />
                                </div>
                                <div className="flex flex-col items-start gap-3 px-5 pt-3 pb-6 max-sm:items-center max-sm:text-center sm:py-5 sm:pl-0">
                                    <div>
                                        <h3 className="text-[15px] font-medium">
                                            No skills in your workspace yet
                                        </h3>
                                        <p className="mt-1 max-w-[52ch] text-[13px] leading-[1.5] text-muted-foreground">
                                            Write one to teach Accretion something it should always
                                            know, like your brand voice or how you like pages laid
                                            out.
                                        </p>
                                    </div>
                                    <AddSkillMenu {...add} />
                                </div>
                            </div>
                            <StarterSkills onAdd={onStarter} />
                        </motion.div>
                    ) : (
                        <motion.div key="list" {...swap}>
                            {shown.length === 0 ? (
                                <NoMatch query={query} />
                            ) : (
                                <div className={GRID}>
                                    <AnimatePresence initial={false}>
                                        {shown.map((skill) => (
                                            <motion.div
                                                key={skill.id ?? skill.name}
                                                layout
                                                className="grid"
                                                initial={{ opacity: 0, scale: 0.97 }}
                                                animate={{ opacity: 1, scale: 1 }}
                                                exit={{
                                                    opacity: 0,
                                                    scale: 0.97,
                                                    transition: { duration: 0.14 },
                                                }}
                                                transition={{
                                                    duration: 0.22,
                                                    ease: [0.23, 1, 0.32, 1],
                                                }}
                                            >
                                                <SkillCard
                                                    skill={skill}
                                                    onPreview={() => onPreview(skill)}
                                                    onEdit={() => skill.id && onEdit(skill.id)}
                                                    onToggle={onToggle}
                                                    onDelete={() =>
                                                        skill.id
                                                            ? onDelete(skill.id)
                                                            : Promise.resolve("")
                                                    }
                                                />
                                            </motion.div>
                                        ))}
                                    </AnimatePresence>
                                </div>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>
            )}
        </section>
    );
}

/** The skills Accretion ships with, on in every project: one row each, tap to read it in full. */
export function BuiltinSkills({
    skills,
    query,
    error,
    retry,
    onPreview,
    onToggle,
}: {
    skills: SkillSummary[] | null;
    query: string;
    error: string;
    retry: () => void;
    onPreview: (skill: SkillSummary) => void;
    onToggle: (name: string, enabled: boolean) => void;
}) {
    const shown = skills?.filter((skill) => matches(skill, query)) ?? null;
    return (
        <section aria-labelledby="builtin-title" className={styles.rise} style={slot(3)}>
            <SectionHeading id="builtin-title" title="Built in" count={skills?.length ?? null}>
                <p className="mt-1.5 max-w-[60ch] text-[13.5px] leading-[1.6] text-muted-foreground">
                    The switch turns a skill on or off in all your projects; to turn one off for a
                    single project, use that project&apos;s Skills tab. Required skills are part of
                    Accretion and always stay on.
                </p>
            </SectionHeading>
            {error ? (
                <ErrorBox message={error}>
                    <Button
                        variant="utility"
                        onClick={retry}
                        className="h-auto p-0 text-[13px] text-destructive underline pointer-coarse:h-auto"
                    >
                        Try again
                    </Button>
                </ErrorBox>
            ) : shown === null ? (
                <GridSkeleton cells={6} />
            ) : shown.length === 0 ? (
                <NoMatch query={query} />
            ) : (
                <ul className="divide-y divide-border border border-border">
                    {shown.map((skill, index) => (
                        <li
                            key={skill.name}
                            className={`${styles.rise} flex items-center gap-3 pr-4 [transition:background-color_140ms_ease] pointer-fine:hover:bg-surface-1`}
                            style={slot(index)}
                        >
                            <button
                                type="button"
                                onClick={() => onPreview(skill)}
                                aria-label={`Preview /${skill.name}`}
                                className={`flex min-h-14 min-w-0 flex-1 items-center py-2.5 pl-4 text-left [transition:opacity_150ms_ease,scale_100ms_var(--ease-out)] active:scale-[0.99] motion-reduce:active:scale-100 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring ${skill.off_everywhere ? "opacity-50" : ""}`}
                            >
                                <span className="min-w-0 flex-1">
                                    <code
                                        className={`${styles.chip} inline-block max-w-full truncate px-1.5 py-0.5 font-mono text-[12px] leading-none`}
                                    >
                                        /{skill.name}
                                    </code>
                                    <span className="mt-1 block truncate text-[13px] text-muted-foreground">
                                        {skill.description}
                                    </span>
                                </span>
                            </button>
                            <EverywhereToggle skill={skill} onToggle={onToggle} />
                        </li>
                    ))}
                </ul>
            )}
        </section>
    );
}
