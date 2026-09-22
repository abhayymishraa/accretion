"use client";

// Interaction patterns adapted from Beautiful UI, MIT © 2026 Shane Levine.
// See ../ember/BEAUTIFUL-UI-LICENSE. All progress comes from recorded run events.

export function CodeListing({ value, language = "output" }: { value: string; language?: string }) {
    return (
        <div className="transcript-code my-2.5 min-w-0 max-w-full overflow-hidden rounded-[8px] border border-hairline bg-surface-3 whitespace-normal">
            <div className="transcript-codeHeader border-b border-hairline px-3 py-[7px] font-mono text-[10.5px] tracking-[0.04em] text-muted-foreground">
                {language}
            </div>
            <pre
                tabIndex={0}
                aria-label={`${language} listing`}
                className="m-0 max-h-72 overflow-auto py-2 font-mono text-[11.5px] leading-[1.75] whitespace-pre focus-visible:outline-2 focus-visible:outline-solid focus-visible:outline-ring focus-visible:-outline-offset-2"
            >
                <code>
                    {value.split("\n").map((line, index) => (
                        <span
                            className="transcript-codeLine flex min-w-max [&>span:last-child]:pr-3 [&[data-diff=add]]:bg-emerald-500/12 [&[data-diff=remove]]:bg-red-500/12"
                            data-diff={
                                language === "diff"
                                    ? line.startsWith("+")
                                        ? "add"
                                        : line.startsWith("-")
                                          ? "remove"
                                          : undefined
                                    : undefined
                            }
                            key={index}
                        >
                            <span
                                aria-hidden="true"
                                className="transcript-lineNumber w-10 shrink-0 pr-3 text-right tabular-nums text-muted-foreground opacity-60 select-none"
                            >
                                {index + 1}
                            </span>
                            <span>{line || " "}</span>
                        </span>
                    ))}
                </code>
            </pre>
        </div>
    );
}
