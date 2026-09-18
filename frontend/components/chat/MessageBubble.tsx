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
        <div className="transcript-answer text-[14px] leading-[1.7] wrap-anywhere whitespace-pre-wrap mt-3 [&_p]:mt-0 [&_p]:mx-0 [&_p]:mb-3 max-[481px]:text-[13px]">
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
            <div className="ember-message-user flex justify-end pl-8 [&>div]:border [&>div]:border-border [&>div]:rounded-[14px_14px_4px_14px] [&>div]:bg-secondary [&>div]:text-foreground [&>div]:max-w-full [&>div]:py-[13px] [&>div]:px-4 [&>div]:wrap-anywhere [&>div]:whitespace-pre-wrap">
                <div>
                    <p className="transcript-userText text-[14px] leading-[1.7] wrap-anywhere whitespace-pre-wrap max-[481px]:text-[13px]">
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
            className="ember-message-assistant text-[14px] text-foreground min-w-0 wrap-anywhere transcript-message min-w-0 w-full [&_summary:focus-visible]:outline-2 [&_summary:focus-visible]:outline-solid [&_summary:focus-visible]:outline-primary [&_summary:focus-visible]:outline-offset-0.5"
            aria-label="WebBuilder response"
        >
            <span className="ember-message-label block text-accent-foreground text-[11px] font-medium mb-2.5">
                WebBuilder
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
                        <div className="transcript-responseActions flex items-center gap-1">
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
