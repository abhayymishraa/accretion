"use client";

import { type RefObject, useLayoutEffect, useRef, useState } from "react";

/**
 * A trigger is a "@" or "/" that starts a word: it sits at the beginning of the
 * prompt or right after whitespace, and nothing but non-space follows it up to
 * the caret. That keeps "app/page.tsx" from opening the command list while
 * "@app/page.tsx" still filters files.
 */
const TRIGGER = /(?:^|\s)([@/])(\S*)$/;
const MAX_CHOICES = 8;

const promptCommands = [
    { name: "Improve layout", prompt: "Improve the layout and spacing of this app. " },
    { name: "Check accessibility", prompt: "Review and improve the accessibility of this app. " },
    { name: "Fix an issue", prompt: "Fix this issue in my app: " },
    { name: "Explain the code", prompt: "Explain how the current app works. " },
];

export type MenuKind = "files" | "commands";

export interface MenuChoice {
    id: string;
    label: string;
    detail?: string;
    insert: string;
    // Where the query matched inside the label, for highlighting.
    match?: [number, number];
}

interface Trigger {
    kind: MenuKind;
    start: number;
    query: string;
}

function detect(value: string, caret: number): Trigger | null {
    const match = TRIGGER.exec(value.slice(0, caret));
    if (!match) return null;
    const [, sigil, query] = match;
    return {
        kind: sigil === "@" ? "files" : "commands",
        start: caret - sigil.length - query.length,
        query,
    };
}

// A path with a dot-folder or dot-file in it (.accretion/, .env): never offered; the backend
// ignores such mentions too (agent/context/context.py mentioned_files).
const hidden = (path: string) => path.split("/").some((part) => part.startsWith("."));

/**
 * Files ranked like an editor's quick open: names starting with the query, then names containing
 * it, then paths containing it; shorter paths first within each rank.
 */
function fileChoices(query: string, files: string[]): MenuChoice[] {
    const needle = query.toLowerCase();
    const ranked: { rank: number; path: string; at: number }[] = [];
    for (const path of files) {
        if (hidden(path)) continue;
        const name = path.slice(path.lastIndexOf("/") + 1).toLowerCase();
        const at = name.indexOf(needle);
        const rank = at === 0 ? 0 : at > 0 ? 1 : path.toLowerCase().includes(needle) ? 2 : -1;
        if (rank >= 0) ranked.push({ rank, path, at });
    }
    ranked.sort(
        (a, b) => a.rank - b.rank || a.path.length - b.path.length || a.path.localeCompare(b.path),
    );
    return ranked.slice(0, MAX_CHOICES).map(({ path, at }) => {
        const cut = path.lastIndexOf("/") + 1;
        return {
            id: path,
            label: path.slice(cut),
            detail: path.slice(0, cut),
            insert: `@${path} `,
            match: needle && at >= 0 ? [at, at + needle.length] : undefined,
        };
    });
}

function buildChoices(kind: MenuKind, query: string, files: string[]): MenuChoice[] {
    if (kind === "files") return fileChoices(query, files);
    const needle = query.toLowerCase();
    return promptCommands
        .filter((command) => command.name.toLowerCase().includes(needle))
        .slice(0, MAX_CHOICES)
        .map((command) => ({ id: command.name, label: command.name, insert: command.prompt }));
}

export function useComposerMenu({
    textarea,
    value,
    onChange,
    files,
    disabled,
}: {
    // Owned by the composer so the element keeps a plain ref in its own render.
    textarea: RefObject<HTMLTextAreaElement | null>;
    value: string;
    onChange: (next: string) => void;
    files: string[];
    disabled: boolean;
}) {
    const pendingCaret = useRef<number | null>(null);
    const [trigger, setTrigger] = useState<Trigger | null>(null);
    const [dismissedKey, setDismissedKey] = useState<string | null>(null);
    const [activeIndex, setActiveIndex] = useState(0);

    const choices = trigger ? buildChoices(trigger.kind, trigger.query, files) : [];
    // Escape suppresses one trigger run, keyed by kind and position, so deleting it
    // and starting a fresh mention in the same column opens the menu again.
    const triggerKey = trigger ? `${trigger.kind}:${trigger.start}` : null;
    const open =
        !disabled && triggerKey !== null && triggerKey !== dismissedKey && choices.length > 0;
    // Clamped rather than reset in an effect, so a shrinking list cannot point past its end.
    const active = Math.min(activeIndex, choices.length - 1);

    // Restores the caret after an accepted completion rewrites the value mid-prompt.
    useLayoutEffect(() => {
        const caret = pendingCaret.current;
        if (caret === null) return;
        pendingCaret.current = null;
        textarea.current?.focus();
        textarea.current?.setSelectionRange(caret, caret);
    });

    /** Reads the caret straight off the element so callers stay one-liners. */
    function syncFromEvent(element: HTMLTextAreaElement) {
        const next = detect(element.value, element.selectionStart);
        // Only a new query resets the highlight: the key-up after ArrowDown re-syncs the same one.
        if (next?.start !== trigger?.start || next?.query !== trigger?.query) setActiveIndex(0);
        setTrigger(next);
        if (!next) setDismissedKey(null);
    }

    /** Escape: suppress this run but keep the typed text. */
    function dismiss() {
        setDismissedKey(triggerKey);
    }

    /** Blur: just close, so returning to the field can reopen it. */
    function close() {
        setTrigger(null);
    }

    function accept(choice: MenuChoice) {
        if (!trigger) return;
        const caret = textarea.current?.selectionStart ?? value.length;
        const head = value.slice(0, trigger.start) + choice.insert;
        onChange(head + value.slice(caret));
        pendingCaret.current = head.length;
        setTrigger(null);
        setDismissedKey(null);
    }

    /** Inserts a bare sigil at the caret; detection then opens the menu on its own. */
    function openKind(kind: MenuKind) {
        const caret = textarea.current?.selectionStart ?? value.length;
        const prefix = value.slice(0, caret);
        const spacer = prefix && !/\s$/.test(prefix) ? " " : "";
        const head = `${prefix}${spacer}${kind === "files" ? "@" : "/"}`;
        onChange(head + value.slice(caret));
        pendingCaret.current = head.length;
        setTrigger({ kind, start: head.length - 1, query: "" });
        setDismissedKey(null);
        setActiveIndex(0);
    }

    /** Returns true when the menu consumed the key, so the composer will not send. */
    function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
        if (!open) return false;
        if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            const step = event.key === "ArrowDown" ? 1 : choices.length - 1;
            setActiveIndex(
                (index) => (Math.min(index, choices.length - 1) + step) % choices.length,
            );
            return true;
        }
        if (event.key === "Enter" || event.key === "Tab") {
            event.preventDefault();
            accept(choices[active]);
            return true;
        }
        if (event.key === "Escape") {
            event.preventDefault();
            dismiss();
            return true;
        }
        return false;
    }

    return {
        open,
        kind: trigger?.kind ?? null,
        choices,
        activeIndex: active,
        setActiveIndex,
        syncFromEvent,
        handleKeyDown,
        accept,
        close,
        openKind,
    };
}
