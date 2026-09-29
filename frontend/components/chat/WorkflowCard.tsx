"use client";

import { Check } from "lucide-react";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Input } from "@/components/ui/input";
import { useWorkflowDecision } from "@/hooks/chat/useWorkflowDecision";
import type { Message } from "@/types/chat.type";

interface WorkflowCardProps {
    message: Message;
    onChanged: () => void;
    canRespond: boolean;
}

export function WorkflowCard(props: WorkflowCardProps) {
    // A newly proposed question must never inherit the previous answer draft.
    return <WorkflowDecisionCard key={props.message.id} {...props} />;
}

function WorkflowDecisionCard({ message, onChanged, canRespond }: WorkflowCardProps) {
    const fieldId = useId();
    const headingId = useId();
    const [text, setText] = useState("");
    const [revising, setRevising] = useState(false);
    const { busy, error, respond } = useWorkflowDecision(onChanged);
    const proposal = message.workflow;
    if (!proposal) return null;

    const plan = proposal.kind === "plan";
    const question = proposal.kind === "clarify";
    const pending = message.run_status === "awaiting_input" && !proposal.resolution;
    const waiting = canRespond && pending;
    const runId = message.id.replace(/^run:/, "");
    const options = proposal.options ?? [];
    const heading = question
        ? "A quick question"
        : plan
          ? "Proposed plan"
          : proposal.kind === "answer"
            ? "Response"
            : "Approach";
    const status = proposal.resolution
        ? proposal.resolution === "dismiss"
            ? "Dismissed"
            : proposal.resolution === "approve"
              ? "Approved"
              : proposal.resolution === "revise"
                ? "Changes requested"
                : "Answer saved"
        : pending
          ? plan
              ? "Awaiting approval"
              : "Your input needed"
          : null;

    return (
        <section
            className="my-3 min-w-0 animate-in overflow-hidden rounded-[10px] border border-border bg-surface-2 fade-in slide-in-from-bottom-1 duration-200 ease-out motion-reduce:slide-in-from-bottom-0"
            aria-labelledby={headingId}
            aria-busy={busy}
        >
            <div className="space-y-2 p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 text-xs text-muted-foreground">
                    <span>{heading}</span>
                    {status && !(question && pending) && <span>{status}</span>}
                </div>
                <h3
                    id={headingId}
                    className="text-[15px] font-medium leading-snug wrap-anywhere whitespace-pre-wrap"
                >
                    {question && proposal.question ? proposal.question : proposal.summary}
                </h3>
                {question && proposal.question && (
                    <details className="text-xs text-muted-foreground">
                        <summary className="cursor-pointer rounded-[4px] py-1 focus-visible:outline-2 focus-visible:outline-ring">
                            Why this question?
                        </summary>
                        <p className="mt-1 leading-relaxed wrap-anywhere whitespace-pre-wrap">
                            {proposal.summary}
                        </p>
                    </details>
                )}
            </div>
            {proposal.steps.length > 0 && (
                <ol className="divide-y divide-hairline border-t border-hairline">
                    {proposal.steps.map((step, index) => (
                        <li
                            className="flex min-h-12 items-start gap-3 px-4 py-2.5 text-sm"
                            key={index}
                        >
                            <span aria-hidden="true" className="tabular-nums text-muted-foreground">
                                {index + 1}
                            </span>
                            <span className="min-w-0 leading-relaxed wrap-anywhere">{step}</span>
                        </li>
                    ))}
                </ol>
            )}
            {waiting && !plan && options.length > 0 && (
                <div
                    role="group"
                    aria-label="Suggested answers"
                    className="divide-y divide-hairline border-t border-hairline"
                >
                    {options.map((option, index) => (
                        <Button
                            variant="utility"
                            aria-pressed={text === option}
                            disabled={busy}
                            key={`${index}:${option}`}
                            onClick={() => setText(option)}
                            className="min-h-12 w-full justify-start gap-3 rounded-none px-4 py-2.5 text-left text-sm whitespace-normal text-foreground aria-pressed:text-accent-foreground"
                        >
                            <span
                                aria-hidden="true"
                                className="flex size-4 shrink-0 items-center justify-center rounded-full border border-input"
                            >
                                {text === option && <Check className="size-3" />}
                            </span>
                            <span className="min-w-0 wrap-anywhere">{option}</span>
                        </Button>
                    ))}
                </div>
            )}
            {waiting && (
                <div className="border-t border-hairline p-4">
                    {plan && !revising ? (
                        <div className="space-y-3">
                            <p className="text-xs leading-relaxed text-muted-foreground">
                                Review the plan. Building starts when you approve.
                            </p>
                            <div className="flex flex-wrap items-center gap-2">
                                <Button
                                    variant="utility"
                                    disabled={busy}
                                    onClick={() => respond(runId, "dismiss")}
                                >
                                    Dismiss
                                </Button>
                                <div className="ml-auto flex flex-wrap gap-2">
                                    <Button
                                        variant="secondary"
                                        disabled={busy}
                                        onClick={() => setRevising(true)}
                                    >
                                        Revise plan
                                    </Button>
                                    <Button
                                        disabled={busy}
                                        onClick={() => respond(runId, "approve")}
                                    >
                                        {busy ? "Saving…" : "Approve and build"}
                                    </Button>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <form
                            className="space-y-3"
                            onSubmit={(event) => {
                                event.preventDefault();
                                if (text.trim())
                                    void respond(runId, plan ? "revise" : "answer", text.trim());
                            }}
                        >
                            <label
                                className="block text-xs text-muted-foreground"
                                htmlFor={fieldId}
                            >
                                {plan
                                    ? "What should change?"
                                    : options.length > 0
                                      ? "Or write something else"
                                      : "Your answer"}
                            </label>
                            <Input
                                id={fieldId}
                                value={text}
                                onChange={(event) => setText(event.target.value)}
                                maxLength={4000}
                                disabled={busy}
                                placeholder={plan ? "Describe your changes…" : "Your answer"}
                            />
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <Button
                                    type="button"
                                    variant="utility"
                                    disabled={busy}
                                    onClick={() => {
                                        if (plan) setRevising(false);
                                        else void respond(runId, "dismiss");
                                    }}
                                >
                                    {plan ? "Back to plan" : "Dismiss"}
                                </Button>
                                <Button type="submit" disabled={busy || !text.trim()}>
                                    {busy ? "Saving…" : plan ? "Update plan" : "Continue"}
                                </Button>
                            </div>
                        </form>
                    )}
                    <div className="[&>[data-error-box]]:mt-3">
                        <ErrorBox message={error ?? ""} />
                    </div>
                </div>
            )}
        </section>
    );
}
