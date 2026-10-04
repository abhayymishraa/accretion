"use client";

import { AnimatedSpan, Terminal, TypingAnimation } from "@/components/ui/terminal";
import type { GitHubSkills } from "@/types/skill.type";
import { useReducedMotion } from "motion/react";

/** The search, told as it happens: what was asked, what was read, what came back. */
export function GitHubFindLog({
    url,
    found,
    error,
}: {
    url: string;
    found: GitHubSkills | null;
    error: string;
}) {
    // Reduced motion: the command appears at once; lines still fade in, nothing moves.
    const reduce = useReducedMotion();
    const total = found ? found.skills.length + found.skipped.length : 0;
    return (
        <Terminal>
            <TypingAnimation duration={reduce ? 1 : 18} className="text-foreground">
                {`$ find skills ${url}`}
            </TypingAnimation>
            <AnimatedSpan className="text-muted-foreground">
                {found ? `› read ${found.repository}@${found.ref}` : "› reading the repository…"}
            </AnimatedSpan>
            {found && (
                <AnimatedSpan className="text-muted-foreground">
                    {`› ${total} SKILL.md ${total === 1 ? "file" : "files"}`}
                </AnimatedSpan>
            )}
            {found && (
                <AnimatedSpan className="text-primary">
                    {`✓ ${found.skills.length} ready to import`}
                </AnimatedSpan>
            )}
            {found && found.skipped.length > 0 && (
                <AnimatedSpan className="text-muted-foreground">
                    {`– ${found.skipped.length} skipped`}
                </AnimatedSpan>
            )}
            {error && !found && (
                <AnimatedSpan className="text-destructive">{`✗ ${error}`}</AnimatedSpan>
            )}
        </Terminal>
    );
}
