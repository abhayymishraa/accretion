"use client";

import { Button } from "@/components/ui/button";

// Interaction patterns adapted from Beautiful UI, MIT © 2026 Shane Levine.
// See ../ember/BEAUTIFUL-UI-LICENSE. All progress comes from recorded run events.
import { presentTool } from "@/lib/tool-presentation";
import type { ToolCall } from "@/types/chat.type";
import { CopyIcon, FileTextIcon, Link2Icon } from "@radix-ui/react-icons";
import { useState } from "react";
import { toast } from "sonner";

import { CodeListing } from "./CodeListing";
export function RecordedResult({
    output,
    label = "Recorded result",
}: {
    output: string;
    label?: string;
}) {
    const [open, setOpen] = useState(false);
    return (
        <details
            className="transcript-raw min-w-0 [&>summary]:cursor-pointer [&>summary]:min-h-9 [&>summary]:flex [&>summary]:items-center [&>summary]:text-[11px] [&>summary]:text-muted-foreground [&>summary]:underline [&>summary]:underline-offset-[3px]"
            open={open}
            onToggle={(event) => setOpen(event.currentTarget.open)}
        >
            <summary>{label}</summary>
            {open && <CodeListing value={output} language="json" />}
        </details>
    );
}

function ToolCopyActions({ tool, value }: { tool: ToolCall; value: unknown }) {
    const [status, setStatus] = useState("");
    const copy = async (text: string, success: string) => {
        setStatus("");
        try {
            await navigator.clipboard.writeText(text);
            toast.success(success, { id: "tool-copy" });
        } catch {
            setStatus("Copy failed. Select the visible text to copy it.");
        }
    };
    return (
        <div className="transcript-copyActions flex items-center flex-wrap gap-y-1 gap-x-3 mt-1.5">
            <Button
                type="button"
                variant="utility"
                onClick={() =>
                    void copy(
                        JSON.stringify(
                            {
                                run_id: tool.run_id,
                                call_id: tool.id,
                                event_id: tool.event_id,
                                tool: tool.name,
                                status: tool.status,
                                result: value,
                            },
                            null,
                            2,
                        ),
                        "Result copied",
                    )
                }
            >
                <CopyIcon aria-hidden="true" />
                Copy result
            </Button>
            {tool.run_id && tool.id && (
                <Button
                    type="button"
                    variant="utility"
                    onClick={() =>
                        void copy(`Run ${tool.run_id} / Tool ${tool.id}`, "Reference copied")
                    }
                >
                    <Link2Icon aria-hidden="true" />
                    Copy reference
                </Button>
            )}
            <span
                className="transcript-caption font-mono text-[11px] text-muted-foreground"
                role="status"
            >
                {status}
            </span>
        </div>
    );
}

export function ToolResult({
    tool,
    result,
}: {
    tool: ToolCall;
    result: ReturnType<typeof presentTool>;
}) {
    const hasTerminal = Boolean(result.stdout || result.stderr || result.exitCode !== undefined);
    return (
        <>
            {result.files.length > 0 && (
                <div className="transcript-context border-l-2 border-l-accent-foreground/45 pl-2.5 mt-1 mx-0 mb-2 [&_ul]:list-none [&_ul]:mt-[7px] [&_ul]:mx-0 [&_ul]:mb-0 [&_ul]:p-0 [&_li]:flex [&_li]:items-baseline [&_li]:gap-[7px] [&_li]:[font:11px/1.8_ui-monospace,_monospace] [&_li]:text-muted-foreground [&_li_svg]:shrink-0 [&_li_svg]:w-3 [&_li_span]:wrap-anywhere">
                    <span className="transcript-caption font-mono text-[11px] text-muted-foreground">
                        {result.targetFiles
                            ? "Target files"
                            : result.changed
                              ? "Updated files"
                              : "Files read"}
                    </span>
                    <ul>
                        {result.files.map((file) => (
                            <li key={file}>
                                <FileTextIcon aria-hidden="true" />
                                <span>{file}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            {result.references.length > 0 && (
                <div className="transcript-context border-l-2 border-l-accent-foreground/45 pl-2.5 mt-1 mx-0 mb-2 [&_ul]:list-none [&_ul]:mt-[7px] [&_ul]:mx-0 [&_ul]:mb-0 [&_ul]:p-0 [&_li]:flex [&_li]:items-baseline [&_li]:gap-[7px] [&_li]:[font:11px/1.8_ui-monospace,_monospace] [&_li]:text-muted-foreground [&_li_svg]:shrink-0 [&_li_svg]:w-3 [&_li_span]:wrap-anywhere">
                    <span className="transcript-caption font-mono text-[11px] text-muted-foreground">
                        Matched conversation messages
                    </span>
                    <ul>
                        {result.references.map((id, index) => (
                            <li key={`${id}:${index}`}>
                                <span>{id}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            {result.command && <CodeListing value={result.command} language="command" />}
            {result.inputOmitted && (
                <p className="transcript-caption font-mono text-[11px] text-muted-foreground">
                    Command text omitted from public activity.
                </p>
            )}
            {result.truncatedFields.length > 0 && (
                <p className="transcript-caption font-mono text-[11px] text-muted-foreground">
                    Recorded excerpts only. Shortened fields: {result.truncatedFields.join(", ")}.
                </p>
            )}
            {hasTerminal && (
                <div className="transcript-terminal pt-1">
                    {result.exitCode !== undefined && (
                        <span className="transcript-caption font-mono text-[11px] text-muted-foreground">
                            Exit code {result.exitCode}
                        </span>
                    )}
                    {result.stdout && <CodeListing value={result.stdout} language="stdout" />}
                    {result.stderr && <CodeListing value={result.stderr} language="stderr" />}
                </div>
            )}
            {result.error && !hasTerminal && <CodeListing value={result.error} language="error" />}
            {result.parsed !== undefined ? (
                <RecordedResult output={JSON.stringify(result.parsed, null, 2)} />
            ) : (
                tool.output && !result.error && <CodeListing value={tool.output} />
            )}
            {tool.status !== "running" && (result.parsed !== undefined || tool.output) && (
                <ToolCopyActions tool={tool} value={result.parsed ?? tool.output} />
            )}
            {!tool.output && result.parsed === undefined && (
                <p className="transcript-caption font-mono text-[11px] text-muted-foreground">
                    {tool.status === "running"
                        ? "Waiting for the tool result…"
                        : "No output was recorded."}
                </p>
            )}
        </>
    );
}
