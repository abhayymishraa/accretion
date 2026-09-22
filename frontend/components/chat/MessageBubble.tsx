"use client";

import { Button } from "@/components/ui/button";

import type { Message, WorkflowProposal } from "@/types/chat.type";
import { CheckIcon, CopyIcon } from "@radix-ui/react-icons";
import { useState } from "react";
import { CodeListing } from "./CodeListing";
import { RunActivity } from "./RunActivity";
import { WorkflowCard } from "./WorkflowCard";

// An approved plan replays as kind "execute"; the run trace shows it instead.
const CARD_KINDS: WorkflowProposal["kind"][] = ["clarify", "plan", "answer"];

function MessageContent({ content }: { content: string }) {
    // Parse complete fences before paragraphs so blank lines inside code survive.
    const parts = content.split(/(```[^\n]*\n[\s\S]*?```)/g);
    return (
        <div className="transcript-answer mt-3 text-[14.5px] leading-[1.75] wrap-anywhere whitespace-pre-wrap text-pretty [&_p]:m-0 [&_p+p]:mt-3.5 max-[481px]:text-[14px]">
            {parts.map((part, i) => {
                const fence = part.match(/^```([^\n]*)\n([\s\S]*?)```$/);
                if (fence)
                    return (
                        <CodeListing
                            key={i}
                            value={fence[2].replace(/\n$/, "")}
                            language={fence[1].trim() || "code"}
                        />
                    );
                return part.trim() ? <p key={i}>{part}</p> : null;
            })}
        </div>
    );
}

export function MessageBubble({
    message,
    connected = true,
    onWorkflowChanged,
    canRespond = false,
}: {
    message: Message;
    connected?: boolean;
    onWorkflowChanged?: () => void;
    canRespond?: boolean;
}) {
    const [copyStatus, setCopyStatus] = useState("");
    if (message.role === "user")
        return (
            <div className="ember-message-user flex justify-end pl-10">
                <div className="max-w-full rounded-[16px_16px_6px_16px] bg-surface-2 px-4 py-3 wrap-anywhere whitespace-pre-wrap">
                    <p className="transcript-userText text-[14.5px] leading-[1.7] wrap-anywhere whitespace-pre-wrap max-[481px]:text-[14px]">
                        {message.content}
                    </p>
                </div>
            </div>
        );
    const hasRun = Boolean(
        message.run_status || message.tool_calls?.length || message.activity?.length,
    );
    return (
        <article
            className="ember-message-assistant transcript-message w-full min-w-0 text-[14.5px] text-foreground wrap-anywhere"
            aria-label="Accretion response"
        >
            <span className="ember-message-label mb-2.5 block text-[11px] font-semibold tracking-[0.02em] text-accent-foreground">
                accretion
            </span>
            {hasRun && <RunActivity message={message} connected={connected} />}
            {message.workflow &&
                CARD_KINDS.includes(message.workflow.kind) &&
                onWorkflowChanged && (
                    <WorkflowCard
                        message={message}
                        onChanged={onWorkflowChanged}
                        canRespond={canRespond}
                    />
                )}
            {message.content && message.content !== message.workflow?.summary && (
                <>
                    <MessageContent content={message.content} />
                    {message.run_status !== "running" && (
                        <div className="transcript-responseActions mt-1 flex items-center gap-1">
                            <Button
                                type="button"
                                variant="utility"
                                aria-label="Copy response"
                                onClick={async () => {
                                    try {
                                        await navigator.clipboard.writeText(message.content);
                                        setCopyStatus("Copied");
                                    } catch {
                                        setCopyStatus(
                                            "Could not copy. Select the response text to copy it.",
                                        );
                                    }
                                }}
                            >
                                {copyStatus === "Copied" ? <CheckIcon /> : <CopyIcon />}
                            </Button>
                            <span
                                role="status"
                                className="transcript-caption font-mono text-[11px] text-muted-foreground"
                            >
                                {copyStatus}
                            </span>
                        </div>
                    )}
                </>
            )}
        </article>
    );
}
