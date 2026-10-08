"use client";

import { splitMentions } from "@/hooks/chat/useComposerMenu";
import type { DecisionAction, Message, WorkflowProposal } from "@/types/chat.type";
import { ScrollText } from "lucide-react";
import { MessageContent } from "./MessageContent";
import { RunActivity } from "./RunActivity";
import { CopyButton } from "./ToolBlocks";
import { WorkflowCard } from "./WorkflowCard";

// An approved plan replays as kind "execute"; the run trace shows it instead.
const CARD_KINDS: WorkflowProposal["kind"][] = ["clarify", "plan", "answer"];

export function MessageBubble({
    message,
    pills,
    connected = true,
    onWorkflowChanged,
    canRespond = false,
}: {
    message: Message;
    // Project files and skill names: a mention of a real one shows as a pill, as it did while typed.
    pills: { targets: Set<string>; skills: Set<string> };
    connected?: boolean;
    onWorkflowChanged?: (action: DecisionAction) => void;
    canRespond?: boolean;
}) {
    if (message.role === "user")
        return (
            // The copy action sits under the bubble and stays visible: touch has no hover to reveal it.
            <div className="flex flex-col items-end gap-0.5">
                {/* Fits short prompts, wraps long ones at a readable measure. */}
                <div className="w-fit max-w-[min(80%,56ch)] rounded-[16px_16px_6px_16px] bg-primary text-primary-foreground px-4 py-3 wrap-anywhere whitespace-pre-wrap">
                    <p className="text-[14.5px] leading-[1.7] wrap-anywhere whitespace-pre-wrap max-[481px]:text-[14px]">
                        {splitMentions(message.content, pills.targets, pills.skills).map(
                            (part, index) =>
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
                <CopyButton text={message.content} label="Copy message" />
            </div>
        );
    const text =
        message.content && message.content !== message.workflow?.summary ? message.content : "";
    const reply = (
        <>
            {message.workflow &&
                CARD_KINDS.includes(message.workflow.kind) &&
                onWorkflowChanged && (
                    <WorkflowCard
                        message={message}
                        onChanged={onWorkflowChanged}
                        canRespond={canRespond}
                    />
                )}
            {text && <MessageContent content={text} />}
        </>
    );
    const hasRun = Boolean(
        message.run_status || message.tool_calls?.length || message.activity?.length,
    );
    return (
        <article
            className="w-full min-w-0 text-[14.5px] text-foreground wrap-anywhere"
            aria-label="Accretion response"
        >
            {hasRun ? (
                <RunActivity message={message} connected={connected}>
                    {reply}
                </RunActivity>
            ) : (
                reply
            )}
        </article>
    );
}
