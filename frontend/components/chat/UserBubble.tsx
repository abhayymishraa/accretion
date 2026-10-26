"use client";

import { splitMentions } from "@/hooks/chat/useComposerMenu";
import { ScrollText } from "lucide-react";
import { CopyButton } from "./ToolBlocks";

// Project files and skill names: a mention of a real one shows as a pill, as it did while typed.
export type Pills = { targets: Set<string>; skills: Set<string> };

/** A message the user wrote. */
export function UserBubble({
    content,
    pills,
}: {
    content: string;
    pills: Pills;
}) {
    return (
        // The copy action sits under the bubble and stays visible: touch has no hover to reveal it.
        <div data-loaded-in="" className="flex flex-col items-end gap-0.5">
            {/* Fits short prompts, wraps long ones at a readable measure. */}
            <div
                className={`w-fit max-w-[min(80%,56ch)] rounded-[16px_16px_6px_16px] bg-primary text-primary-foreground px-4 py-3 wrap-anywhere whitespace-pre-wrap`}
            >
                <p className="text-[14.5px] leading-[1.7] wrap-anywhere whitespace-pre-wrap max-[481px]:text-[14px]">
                    {splitMentions(content, pills.targets, pills.skills).map((part, index) =>
                        typeof part === "string" ? (
                            part
                        ) : (
                            <span
                                key={index}
                                className="rounded-[4px] bg-primary-foreground/18 px-1 py-px font-mono text-[0.92em]"
                            >
                                {"skill" in part ? (
                                    <>
                                        <ScrollText
                                            aria-label="Skill"
                                            className="mr-1 inline size-[0.95em] -translate-y-px"
                                        />
                                        {part.skill}
                                    </>
                                ) : (
                                    `@${part.path}`
                                )}
                            </span>
                        ),
                    )}
                </p>
            </div>
            <CopyButton text={content} label="Copy message" />
        </div>
    );
}
