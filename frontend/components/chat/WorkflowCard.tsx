"use client";

import { ArrowRight, Check, CircleHelp, ListChecks } from "lucide-react";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
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
    const Icon = question ? CircleHelp : ListChecks;
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
            className="my-3 min-w-0 overflow-hidden rounded-xl border border-border bg-card text-sm"
            aria-labelledby={headingId}
            aria-busy={busy}
        >
            <div className={question ? "space-y-2 p-3" : "space-y-4 p-4 sm:p-5"}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3
                        id={headingId}
                        className="flex items-center gap-2 text-xs font-medium text-muted-foreground"
                    >
                        <Icon aria-hidden="true" className="size-4 text-accent-foreground" />
                        {heading}
                    </h3>
                    {status && !(question && pending) && (
                        <span className="rounded-md bg-secondary px-2 py-1 text-[11px] text-muted-foreground">
                            {status}
                        </span>
                    )}
                </div>
                {question && proposal.question && (
                    <p className="whitespace-pre-wrap wrap-anywhere font-medium leading-snug">
                        {proposal.question}
                    </p>
                )}
                {question && proposal.question ? (
                    <details className="text-xs text-muted-foreground">
                        <summary className="cursor-pointer rounded-sm py-1 focus-visible:outline-2 focus-visible:outline-ring">
                            Why this question?
                        </summary>
                        <p className="mt-1 whitespace-pre-wrap wrap-anywhere leading-relaxed">
                            {proposal.summary}
                        </p>
                    </details>
                ) : (
                    <p className="whitespace-pre-wrap wrap-anywhere leading-relaxed">
                        {proposal.summary}
                    </p>
                )}
                {proposal.steps.length > 0 && (
                    <ol className="space-y-3 border-t border-border pt-4">
                        {proposal.steps.map((step, index) => (
                            <li className="flex gap-3" key={index}>
                                <span
                                    aria-hidden="true"
                                    className="flex size-6 shrink-0 items-center justify-center rounded-md border border-border font-mono text-[11px] text-muted-foreground"
                                >
                                    {String(index + 1).padStart(2, "0")}
                                </span>
                                <span className="min-w-0 wrap-anywhere leading-relaxed">
                                    {step}
                                </span>
                            </li>
                        ))}
                    </ol>
                )}
            </div>
            {waiting && (
                <div
                    className={
                        question
                            ? "border-t border-border p-3"
                            : "border-t border-border bg-secondary/25 p-4 sm:p-5"
                    }
                >
                    {plan && !revising ? (
                        <div className="space-y-4">
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
                                        <ArrowRight aria-hidden="true" className="size-4" />
                                    </Button>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <form
                            className={question ? "space-y-3" : "space-y-4"}
                            onSubmit={(event) => {
                                event.preventDefault();
                                if (text.trim())
                                    void respond(runId, plan ? "revise" : "answer", text.trim());
                            }}
                        >
                            {!plan && Boolean(proposal.options?.length) && (
                                <div
                                    role="group"
                                    aria-label="Suggested answers"
                                    className="flex flex-wrap gap-2"
                                >
                                    {proposal.options?.map((option, index) => (
                                        <Button
                                            type="button"
                                            variant="secondary"
                                            className="h-auto min-h-11 max-w-full justify-start gap-2 whitespace-normal rounded-lg px-3 py-2 text-left aria-pressed:border-primary aria-pressed:bg-accent aria-pressed:text-accent-foreground"
                                            aria-pressed={text === option}
                                            disabled={busy}
                                            key={`${index}:${option}`}
                                            onClick={() => setText(option)}
                                        >
                                            <span
                                                aria-hidden="true"
                                                className="flex size-4 shrink-0 items-center justify-center rounded-full border border-current/40"
                                            >
                                                {text === option && <Check className="size-3" />}
                                            </span>
                                            <span className="min-w-0 wrap-anywhere">{option}</span>
                                        </Button>
                                    ))}
                                </div>
                            )}
                            <div className="space-y-2">
                                <label
                                    className={
                                        plan ? "block text-xs text-muted-foreground" : "sr-only"
                                    }
                                    htmlFor={fieldId}
                                >
                                    {plan ? "What should change?" : "Your answer"}
                                </label>
                                <Input
                                    id={fieldId}
                                    value={text}
                                    onChange={(event) => setText(event.target.value)}
                                    maxLength={4000}
                                    disabled={busy}
                                    placeholder={
                                        plan ? "Describe your changes…" : "Or write something else…"
                                    }
                                />
                            </div>
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
                                    <ArrowRight aria-hidden="true" className="size-4" />
                                </Button>
                            </div>
                        </form>
                    )}
                    {error && (
                        <p role="alert" className="mt-3 wrap-anywhere text-destructive">
                            {error}
                        </p>
                    )}
                </div>
            )}
        </section>
    );
}
