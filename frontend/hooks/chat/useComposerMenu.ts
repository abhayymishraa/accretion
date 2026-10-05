"use client";

import { PROMPTS, type PromptCategory } from "@/lib/chat/prompts";
import type { ProjectSkill } from "@/types/skill.type";
import { type RefObject, useLayoutEffect, useRef, useState } from "react";

/**
 * A trigger is a "@" or "/" that starts a word: it sits at the beginning of the
 * prompt or right after whitespace, and nothing but non-space follows it up to
 * the caret. That keeps "app/page.tsx" from opening the command list while
 * "@app/page.tsx" still filters files.
 */
const TRIGGER = /(?:^|\s)([@/])(\S*)$/;
const MAX_CHOICES = 8;

export type MenuKind = "files" | "commands";

export interface MenuChoice {
    id: string;
    label: string;
    detail?: string;
    insert: string;
    // Where the query matched inside the label, for highlighting.
    match?: [number, number];
    // The menu's section headings; a heading shows where these change.
    group?: string;
    subgroup?: string;
    skill?: ProjectSkill;
    category?: PromptCategory;
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
// ignores such mentions too (agent/context/context.py mentions).
const hidden = (path: string) => path.split("/").some((part) => part.startsWith("."));

/** Every file and folder the user can mention: folders end in "/", hidden paths are left out. */
export function mentionTargets(files: string[]): string[] {
    const targets = new Set<string>();
    for (const path of files) {
        if (hidden(path)) continue;
        targets.add(path);
        for (let cut = path.indexOf("/"); cut > 0; cut = path.indexOf("/", cut + 1))
            targets.add(path.slice(0, cut + 1));
    }
    return [...targets];
}

const MENTION = /(^|\s)([@/])([^\s@]+)/g;
const TRAILING = /[.,;:!?)\]}'"]+$/;
export const SKILL_NAME = /^[a-z0-9][a-z0-9-]*/;
// Put before a picked skill so the composer has room to draw its icon where the "/" is. It is
// whitespace to both parsers, and sending removes it.
export const ICON_ROOM = "\u2003";
// The room before each picked skill, which always follows a space or the start. An em space typed
// between words is left alone.
const PICK_ROOMS = new RegExp(`(^|\\s)${ICON_ROOM}`, "g");

/** The prompt as it is sent: trimmed, without the room the composer drew picked skills in. */
export const sendable = (text: string) => text.replace(PICK_ROOMS, "$1").trim();

type PromptPart = string | { path: string } | { skill: string };

/**
 * The prompt cut around "@path" mentions of real project files and folders, and "/name" picks of
 * enabled skills, by the backend's rules (agent/context/context.py mentions, agent/tools/skills.py
 * picked), so the composer can highlight them.
 */
export function splitMentions(
    text: string,
    targets: Set<string>,
    skills: Set<string>,
): PromptPart[] {
    const parts: PromptPart[] = [];
    let last = 0;
    for (const match of text.matchAll(MENTION)) {
        const [, space, sigil, rest] = match;
        const name =
            sigil === "@" ? rest.replace(TRAILING, "") : (SKILL_NAME.exec(rest)?.[0] ?? "");
        if (!(sigil === "@" ? targets : skills).has(name)) continue;
        const at = match.index + space.length;
        parts.push(text.slice(last, at), sigil === "@" ? { path: name } : { skill: name });
        last = at + 1 + name.length;
    }
    parts.push(text.slice(last));
    return parts;
}

/**
 * Files and folders ranked like an editor's quick open: names starting with the query, then names
 * containing it, then paths containing it; shorter paths first within each rank.
 */
function fileChoices(query: string, targets: string[]): MenuChoice[] {
    const needle = query.toLowerCase();
    const ranked: { rank: number; path: string; at: number }[] = [];
    for (const path of targets) {
        const name = path.slice(path.lastIndexOf("/", path.length - 2) + 1).toLowerCase();
        const at = name.indexOf(needle);
        const rank = at === 0 ? 0 : at > 0 ? 1 : path.toLowerCase().includes(needle) ? 2 : -1;
        if (rank >= 0) ranked.push({ rank, path, at });
    }
    ranked.sort(
        (a, b) => a.rank - b.rank || a.path.length - b.path.length || a.path.localeCompare(b.path),
    );
    return ranked.slice(0, MAX_CHOICES).map(({ path, at }) => {
        const cut = path.lastIndexOf("/", path.length - 2) + 1;
        return {
            id: path,
            label: path.slice(cut),
            detail: path.slice(0, cut),
            insert: `@${path} `,
            match: needle && at >= 0 ? [at, at + needle.length] : undefined,
        };
    });
}

const SOURCE_ORDER = { project: 0, library: 1, builtin: 2 } as const;

function buildChoices(
    kind: MenuKind,
    query: string,
    files: string[],
    skills: ProjectSkill[],
): MenuChoice[] {
    if (kind === "files") return fileChoices(query, mentionTargets(files));
    const needle = query.toLowerCase();
    // Prompts come after the skills, one subheading per category, as bolt.new lists them.
    const prompts = PROMPTS.filter((prompt) => prompt.name.toLowerCase().includes(needle)).map(
        (prompt) => ({
            id: `prompt:${prompt.name}`,
            label: prompt.name,
            insert: `${prompt.prompt} `,
            group: "Prompts",
            subgroup: prompt.category,
            category: prompt.category,
        }),
    );
    // Every enabled skill, not a top few: the list scrolls. The user's own come first, the project's
    // before the library's; built-ins keep the category order the API sends.
    const picks = skills
        .filter((skill) => skill.enabled && skill.name.includes(needle))
        .sort((a, b) => SOURCE_ORDER[a.source] - SOURCE_ORDER[b.source])
        .map((skill) => {
            const at = skill.name.indexOf(needle);
            return {
                id: `skill:${skill.name}`,
                label: skill.name,
                detail: skill.description,
                insert: `${ICON_ROOM}/${skill.name} `,
                match: needle ? ([at, at + needle.length] as [number, number]) : undefined,
                group: skill.category ?? "Your skills",
                subgroup:
                    skill.subcategory ??
                    (skill.source === "project" ? "In this project" : "From your library"),
                skill,
            };
        });
    return [...picks, ...prompts];
}

export function useComposerMenu({
    textarea,
    value,
    onChange,
    files,
    skills,
    disabled,
}: {
    // Owned by the composer so the element keeps a plain ref in its own render.
    textarea: RefObject<HTMLTextAreaElement | null>;
    value: string;
    onChange: (next: string) => void;
    files: string[];
    // Null until the "/" menu has opened once and fetched them.
    skills: ProjectSkill[] | null;
    disabled: boolean;
}) {
    const pendingCaret = useRef<number | null>(null);
    const [trigger, setTrigger] = useState<Trigger | null>(null);
    const [dismissedKey, setDismissedKey] = useState<string | null>(null);
    const [activeIndex, setActiveIndex] = useState(0);

    const choices = trigger ? buildChoices(trigger.kind, trigger.query, files, skills ?? []) : [];
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
        // A pick made again after backspacing over one reuses the room it left.
        const before = value.slice(0, trigger.start);
        const head =
            (choice.insert.startsWith(ICON_ROOM) && before.endsWith(ICON_ROOM)
                ? before.slice(0, -1)
                : before) + choice.insert;
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

    /** The prompt textarea's wiring: a combobox over the menu, and Enter sends when canSend. */
    function fieldProps(listId: string, canSend: boolean) {
        return {
            role: "combobox" as const,
            "aria-autocomplete": "list" as const,
            "aria-expanded": open,
            "aria-controls": open ? listId : undefined,
            "aria-activedescendant": open ? `${listId}-${active}` : undefined,
            onChange: (event: React.ChangeEvent<HTMLTextAreaElement>) => {
                onChange(event.target.value);
                syncFromEvent(event.currentTarget);
            },
            onClick: (event: React.MouseEvent<HTMLTextAreaElement>) =>
                syncFromEvent(event.currentTarget),
            onBlur: close,
            onKeyUp: (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
                if (event.key.startsWith("Arrow") || event.key === "Home")
                    syncFromEvent(event.currentTarget);
            },
            onKeyDown: (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
                // While an input method composes (Japanese, Chinese, Korean), its keys are its own.
                if (event.nativeEvent.isComposing) return;
                if (handleKeyDown(event)) return;
                if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    if (canSend) event.currentTarget.form?.requestSubmit();
                }
            },
        };
    }

    return {
        open,
        kind: trigger?.kind ?? null,
        choices,
        activeIndex: active,
        setActiveIndex,
        fieldProps,
        accept,
        close,
        openKind,
    };
}
