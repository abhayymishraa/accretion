"use client";

import { splitMentions } from "@/hooks/chat/useComposerMenu";
import type { Message, WorkflowProposal } from "@/types/chat.type";
import { ScrollText } from "lucide-react";
import { Streamdown } from "streamdown";
import { RunActivity } from "./RunActivity";
import { WorkflowCard } from "./WorkflowCard";

// An approved plan replays as kind "execute"; the run trace shows it instead.
const CARD_KINDS: WorkflowProposal["kind"][] = ["clarify", "plan", "answer"];

// Replies are markdown. Streamdown (Vercel's chatbot, Onlook) sanitizes raw HTML and copes with unfinished
// markdown; the overrides keep headings chat-sized instead of document-sized.
function MessageContent({ content }: { content: string }) {
    return (
        <Streamdown
            mode="static"
            linkSafety={{ enabled: false }}
            className="transcript-answer mt-3 text-[14.5px] leading-[1.7] wrap-anywhere text-pretty max-[481px]:text-[14px] [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&_:is(h1,h2,h3,h4)]:mt-6 [&_:is(h1,h2,h3,h4)]:mb-1.5 [&_:is(h1,h2,h3,h4)]:text-[15px] [&_:is(h1,h2,h3,h4)]:font-semibold [&_p]:my-3 [&_:is(ul,ol)]:my-3.5 [&_:is(ul,ol)]:list-outside [&_:is(ul,ol)]:pl-5 [&_li]:my-2 [&_li]:pl-1 [&_li]:py-0 [&_li]:marker:text-muted-foreground [&_strong]:font-semibold [&_strong]:text-foreground [&_a]:underline [&_a]:underline-offset-2 [&_:not(pre)>code]:rounded-[4px] [&_:not(pre)>code]:bg-surface-3 [&_:not(pre)>code]:px-1 [&_:not(pre)>code]:py-0.5 [&_:not(pre)>code]:font-mono [&_:not(pre)>code]:text-[0.88em]"
        >
            {content}
        </Streamdown>
    );
}

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
    onWorkflowChanged?: () => void;
    canRespond?: boolean;
}) {
    if (message.role === "user")
        return (
            <div className="ember-message-user flex justify-end">
                {/* Vercel's chatbot: fits short prompts, wraps long ones at a readable measure. */}
                <div className="w-fit max-w-[min(80%,56ch)] rounded-[16px_16px_6px_16px] bg-primary text-primary-foreground px-4 py-3 wrap-anywhere whitespace-pre-wrap">
                    <p className="transcript-userText text-[14.5px] leading-[1.7] wrap-anywhere whitespace-pre-wrap max-[481px]:text-[14px]">
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
            className="ember-message-assistant transcript-message w-full min-w-0 text-[14.5px] text-foreground wrap-anywhere"
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
