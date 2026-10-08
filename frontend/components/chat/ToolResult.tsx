"use client";

// Interaction patterns adapted from Beautiful UI, MIT © 2026 Shane Levine.
// See ../ember/BEAUTIFUL-UI-LICENSE. All progress comes from recorded run events.
import { presentTool } from "@/lib/tool-presentation";
import { FileTextIcon } from "@radix-ui/react-icons";

import { CodeListing } from "./CodeListing";

const LIST =
    "border-l-2 border-l-accent-foreground/45 pl-2.5 mt-1 mx-0 mb-2 [&_ul]:list-none [&_ul]:mt-[7px] [&_ul]:mx-0 [&_ul]:mb-0 [&_ul]:p-0 [&_li]:flex [&_li]:items-baseline [&_li]:gap-[7px] [&_li]:[font:11px/1.8_ui-monospace,_monospace] [&_li]:text-muted-foreground [&_li_svg]:shrink-0 [&_li_svg]:w-3 [&_li_span]:wrap-anywhere";

const CAPTION = "font-mono text-[11px] text-muted-foreground";

/** What a failed tool row shows when opened: the files it touched, its output, or its error. */
export function ToolResult({ result }: { result: ReturnType<typeof presentTool> }) {
    const hasTerminal = Boolean(result.stdout || result.stderr || result.exitCode !== undefined);
    return (
        <>
            {result.files.length > 0 && (
                <div className={LIST}>
                    <span className={CAPTION}>
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
                <div className={LIST}>
                    <span className={CAPTION}>Matched conversation messages</span>
                    <ul>
                        {result.references.map((id, index) => (
                            <li key={`${id}:${index}`}>
                                <span>{id}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            {result.inputOmitted && (
                <p className={CAPTION}>Command text omitted from public activity.</p>
            )}
            {result.truncatedFields.length > 0 && (
                <p className={CAPTION}>
                    Recorded excerpts only. Shortened fields: {result.truncatedFields.join(", ")}.
                </p>
            )}
            {hasTerminal && (
                <div className="pt-1">
                    {result.exitCode !== undefined && (
                        <span className={CAPTION}>Exit code {result.exitCode}</span>
                    )}
                    {result.stdout && <CodeListing value={result.stdout} language="stdout" />}
                    {result.stderr && <CodeListing value={result.stderr} language="stderr" />}
                </div>
            )}
            {result.error && !hasTerminal && <CodeListing value={result.error} language="error" />}
        </>
    );
}
