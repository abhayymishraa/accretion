"use client";

import { Bold, Code, Italic, List } from "lucide-react";
import { type ComponentProps, useRef } from "react";

const TOOL =
    "grid size-8 cursor-pointer place-items-center text-muted-foreground pointer-coarse:size-11 pointer-fine:hover:bg-surface-1 pointer-fine:hover:text-foreground";
const HEADING = /^#{1,6} /;

type Edit = { value: string; start: number; end: number };

/** Wraps the selection (or a placeholder word) in a Markdown marker, keeping it selected. */
const wrap =
    (marker: string) =>
    (value: string, start: number, end: number): Edit => {
        const picked = value.slice(start, end) || "text";
        const before = value.slice(0, start) + marker;
        return {
            value: before + picked + marker + value.slice(end),
            start: before.length,
            end: before.length + picked.length,
        };
    };

/** Rewrites every line the selection touches. */
function eachLine(
    value: string,
    start: number,
    end: number,
    change: (lines: string[]) => string[],
): Edit {
    const from = value.lastIndexOf("\n", start - 1) + 1;
    const stop = value.indexOf("\n", end);
    const to = stop === -1 ? value.length : stop;
    const block = change(value.slice(from, to).split("\n")).join("\n");
    return {
        value: value.slice(0, from) + block + value.slice(to),
        start: from,
        end: from + block.length,
    };
}

const toggleList = (value: string, start: number, end: number) =>
    eachLine(value, start, end, (lines) =>
        lines.every((line) => line.startsWith("- "))
            ? lines.map((line) => line.slice(2))
            : lines.map((line) => `- ${line}`),
    );

const TOOLS = [
    { label: "Bold", icon: Bold, make: wrap("**") },
    { label: "Italic", icon: Italic, make: wrap("_") },
    { label: "Code", icon: Code, make: wrap("`") },
    { label: "Bulleted list", icon: List, make: toggleList },
];

/**
 * The instructions box with a formatting bar. It writes plain Markdown, the format a SKILL.md body
 * is in, so what is saved is exactly what the builder reads.
 */
export function MarkdownField({
    value,
    onChange,
    ...textarea
}: Omit<ComponentProps<"textarea">, "value" | "onChange"> & {
    value: string;
    onChange: (value: string) => void;
}) {
    const field = useRef<HTMLTextAreaElement>(null);

    function apply(make: (value: string, start: number, end: number) => Edit) {
        const element = field.current;
        if (!element) return;
        const edit = make(value, element.selectionStart, element.selectionEnd);
        onChange(edit.value);
        // After React writes the new value, put the selection back on what was formatted.
        requestAnimationFrame(() => {
            element.focus();
            element.setSelectionRange(edit.start, edit.end);
        });
    }

    return (
        <div>
            <textarea
                ref={field}
                value={value}
                onChange={(event) => onChange(event.target.value)}
                {...textarea}
            />
            <div
                role="toolbar"
                aria-label="Formatting"
                className="flex items-center gap-px border border-t-0 border-border bg-surface-2"
            >
                {TOOLS.map(({ label, icon: Icon, make }) => (
                    <button
                        key={label}
                        type="button"
                        title={label}
                        aria-label={label}
                        // Keeps the selection in the text box while the button is pressed.
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={() => apply(make)}
                        className={TOOL}
                    >
                        <Icon size={15} aria-hidden="true" />
                    </button>
                ))}
                <label className="ml-auto">
                    <span className="sr-only">Text style of the current line</span>
                    <select
                        defaultValue=""
                        onChange={(event) => {
                            const level = Number(event.target.value);
                            event.target.value = "";
                            apply((v, s, e) =>
                                eachLine(v, s, e, (lines) =>
                                    lines.map(
                                        (line) =>
                                            (level ? `${"#".repeat(level)} ` : "") +
                                            line.replace(HEADING, ""),
                                    ),
                                ),
                            );
                        }}
                        className="h-8 cursor-pointer border-0 bg-transparent px-2 font-mono text-[12px] text-muted-foreground outline-none pointer-coarse:h-11"
                    >
                        <option value="" disabled>
                            Text style
                        </option>
                        <option value="0">Text</option>
                        <option value="1">Heading 1</option>
                        <option value="2">Heading 2</option>
                        <option value="3">Heading 3</option>
                    </select>
                </label>
            </div>
        </div>
    );
}
