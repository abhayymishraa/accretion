"use client";

import { Button } from "@/components/ui/button";
import type { SkillSummary } from "@/types/skill.type";
import { Eye, Pencil, Trash2 } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { useState } from "react";
import styles from "./skills.module.css";
import { EverywhereToggle } from "./SkillSwitch";

const ACTION = "h-11 rounded-none px-3 text-[12.5px] pointer-fine:h-8";

interface SkillCardProps {
    skill: SkillSummary;
    /** Open the full instructions in the preview panel. */
    onPreview: () => void;
    /** Open the editor for this skill. */
    onEdit: () => void;
    /** Returns the error to show, or "". */
    onDelete: () => Promise<string>;
    /** On or off for every project. */
    onToggle: (name: string, enabled: boolean) => void;
}

/** One of the user's skills in a grid compartment: its `/name`, what it is for, and its actions. */
export function SkillCard({ skill, onPreview, onEdit, onDelete, onToggle }: SkillCardProps) {
    const reduce = useReducedMotion();
    // Turned off for the whole account: the name and description fade back, the controls stay.
    const dim = `[transition:opacity_150ms_ease] ${skill.off_everywhere ? "opacity-50" : ""}`;
    const [confirming, setConfirming] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [error, setError] = useState("");
    async function confirmDelete() {
        setDeleting(true);
        const failure = await onDelete();
        // On success the card leaves the list, so only a failure needs state.
        if (failure) {
            setError(failure);
            setDeleting(false);
            setConfirming(false);
        }
    }

    return (
        <article className="flex h-full flex-col bg-background px-4 pt-4 pb-2 [transition:background-color_140ms_ease] pointer-fine:hover:bg-surface-1">
            {/* The switch keeps its 44px target without making the header row taller. */}
            <div className="-my-2.5 flex items-center justify-between gap-2">
                <h3 className={`min-w-0 ${dim}`}>
                    {/* Shares its id with the starter tile's chip, so an added starter travels into its card. */}
                    <motion.code
                        layoutId={reduce ? undefined : `skill-chip-${skill.name}`}
                        transition={{ type: "spring", duration: 0.45, bounce: 0.15 }}
                        className={`${styles.chip} inline-block max-w-full truncate px-2 py-1 font-mono text-[12.5px] leading-none`}
                    >
                        /{skill.name}
                    </motion.code>
                </h3>
                <EverywhereToggle skill={skill} onToggle={onToggle} />
            </div>
            <p
                className={`mt-2.5 text-[13px] leading-[1.55] text-muted-foreground wrap-anywhere line-clamp-2 ${dim}`}
            >
                {skill.description}
            </p>
            {error && (
                <p
                    data-error-box="shown"
                    role="alert"
                    className="mt-2 text-[12.5px] text-destructive"
                >
                    {error}
                </p>
            )}
            <div className="mt-auto flex min-h-11 flex-wrap items-center gap-1 pt-3">
                {confirming ? (
                    <div className={`${styles.ask} flex flex-1 flex-wrap items-center gap-1`}>
                        <span className="mr-auto text-[12.5px] text-foreground">
                            Delete for good?
                        </span>
                        <Button
                            variant="utility"
                            className={ACTION}
                            onClick={() => setConfirming(false)}
                            disabled={deleting}
                        >
                            Keep
                        </Button>
                        <Button
                            variant="utility"
                            className={`${ACTION} text-destructive pointer-fine:hover:text-destructive`}
                            onClick={confirmDelete}
                            disabled={deleting}
                        >
                            {deleting ? "Deleting" : "Delete"}
                        </Button>
                    </div>
                ) : (
                    <>
                        <Button
                            variant="utility"
                            className={`${ACTION} -ml-3 mr-auto`}
                            onClick={onPreview}
                        >
                            <Eye size={14} />
                            Preview
                        </Button>
                        <Button variant="utility" className={ACTION} onClick={onEdit}>
                            <Pencil size={14} />
                            Edit
                        </Button>
                        <Button
                            variant="utility"
                            className={ACTION}
                            onClick={() => {
                                setError("");
                                setConfirming(true);
                            }}
                        >
                            <Trash2 size={14} />
                            Delete
                        </Button>
                    </>
                )}
            </div>
        </article>
    );
}
