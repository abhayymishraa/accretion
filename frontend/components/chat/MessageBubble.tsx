"use client";

import type { DecisionAction, Message, WorkflowProposal } from "@/types/chat.type";
import { MessageContent } from "./MessageContent";
import { RunActivity } from "./RunActivity";
import { UserBubble, type Pills } from "./UserBubble";
import { WorkflowCard } from "./WorkflowCard";

// An approved plan replays as kind "execute"; the run trace shows it instead.
const CARD_KINDS: WorkflowProposal["kind"][] = ["clarify", "plan", "answer"];

export function MessageBubble({
    message,
    steers = [],
    pills,
    connected = true,
    onWorkflowChanged,
    canRespond = false,
}: {
    message: Message;
    // Messages the user sent while this run worked: they show inside it.
    steers?: Message[];
    pills: Pills;
    connected?: boolean;
    onWorkflowChanged?: (action: DecisionAction) => void;
    canRespond?: boolean;
}) {
    if (message.role === "user") return <UserBubble content={message.content} pills={pills} />;
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
            {text && (
                // The reply lands at the end of a build: it eases in like the edited-files card below it.
                <MessageContent
                    content={text}
                    className="[transition:opacity_180ms_var(--ease-out),translate_180ms_var(--ease-out)] starting:translate-y-1 starting:opacity-0 motion-reduce:starting:translate-y-0"
                />
            )}
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
                <RunActivity message={message} steers={steers} pills={pills} connected={connected}>
                    {reply}
                </RunActivity>
            ) : (
                reply
            )}
        </article>
    );
}
