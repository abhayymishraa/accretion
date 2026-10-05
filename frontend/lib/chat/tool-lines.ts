import { presentTool } from "@/lib/tool-presentation";
import type { TimelineEntry } from "@/lib/chat/run-timeline";
import type { ActivityItem, ToolCall } from "@/types/chat.type";

// One row of the run timeline, in the words Codex uses: "Read x", "Ran y", "Edited z +3 -1".
export type LineKind =
    "read" | "view" | "edit" | "create" | "run" | "search" | "list" | "guide" | "other";

/** [sign, line number, text]; the number is the new file's for " " and "+", the old file's for "-". */
export type DiffLine = [" " | "+" | "-", number, string];
export type FileDiff = {
    path: string;
    created: boolean;
    added: number;
    removed: number;
    hunks: DiffLine[][];
    truncated: boolean;
};
export type ToolLine = {
    key: string;
    kind: LineKind;
    tool: ToolCall;
    text: string;
    path?: string;
    diff?: FileDiff;
    screenshots?: string[];
};
export type TimelineBlock =
    | { kind: "section"; key: string; lines: ToolLine[] }
    | { kind: "note"; key: string; item: ActivityItem }
    | { kind: "screenshots"; key: string; runId: string; ids: string[] };

// Stage messages the runner emits before each tool (agent/run/runner.py run_call). The row says it already.
const TOOL_STAGES = new Set([
    "Inspecting existing files",
    "Loading relevant guidance",
    "Editing project files",
    "Running a workspace command",
    "Reclaiming conversation context",
    // The build check's own row says this (RunTimeline BuildCheck).
    "Checking the production build",
    "Checking production build and browser",
]);

const TOKEN = /"([^"]*)"|'([^']*)'|(\S+)/g;
// The image files read_files hands over as pictures (agent/tools/tools.py IMAGE_SUFFIXES).
const IMAGE = /\.(?:png|jpe?g|gif|webp)$/i;

function words(command: string) {
    return [...command.matchAll(TOKEN)].map((match) => match[1] ?? match[2] ?? match[3]);
}

/** Recognise searches, listings and plain reads so they read like Codex rows; anything else "Ran". */
function classifyCommand(command: string): { kind: LineKind; text: string; path?: string } {
    const step =
        command
            .split(/&&|;/)
            .map((part) => part.trim())
            .find((part) => part && !/^cd\s/.test(part)) ?? command;
    const [program = "", ...rest] = words(step.split("|")[0].trim());
    const args = rest.filter((arg) => !arg.startsWith("-"));
    if (/^(?:rg|grep|egrep|ag)$/.test(program) && args[0]) {
        const where = args.length > 1 ? ` in ${args.at(-1)}` : "";
        return { kind: "search", text: `for ${args[0]}${where}` };
    }
    if (/^(?:ls|find|tree)$/.test(program)) {
        const dir = args[0] && args[0] !== "." ? args[0] : "the project";
        return { kind: "list", text: `in ${dir}` };
    }
    const reads =
        /^(?:cat|head|tail|nl)$/.test(program) || (program === "sed" && rest.includes("-n"));
    if (reads && args.length && !step.includes("|")) {
        const path = args.at(-1)!;
        return { kind: "read", text: path, path };
    }
    return { kind: "run", text: command };
}

function screenshotsOf(tool: ToolCall): string[] {
    const details = tool.details as { screenshots?: unknown } | undefined;
    return Array.isArray(details?.screenshots)
        ? details.screenshots.filter((id): id is string => typeof id === "string")
        : [];
}

function diffsOf(tool: ToolCall): FileDiff[] {
    const details = tool.details as { diffs?: unknown } | undefined;
    return Array.isArray(details?.diffs)
        ? details.diffs.filter(
              (item): item is FileDiff =>
                  typeof item === "object" &&
                  item !== null &&
                  typeof item.path === "string" &&
                  Array.isArray(item.hunks),
          )
        : [];
}

/** A tool call becomes one row per file it touched, or one row for everything else. */
export function toolLines(tool: ToolCall): ToolLine[] {
    const result = presentTool(tool);
    const key = tool.event_id || tool.id || tool.name;
    const line = (kind: LineKind, text: string, extra: Partial<ToolLine> = {}, index = 0) => ({
        key: `${key}:${index}`,
        kind,
        tool,
        text,
        ...extra,
    });
    const failed = tool.status === "error";
    if (tool.name === "read_files" && result.files.length && !failed) {
        // An image read is "Viewed an image"; the call's stored images go on the first one.
        let screenshots = screenshotsOf(tool);
        return result.files.map((path, index) => {
            if (!IMAGE.test(path)) return line("read", path, { path }, index);
            const shown = screenshots;
            screenshots = [];
            return line("view", path, { path, screenshots: shown }, index);
        });
    }
    if (["write_files", "edit_file", "edit_files"].includes(tool.name) && !failed) {
        const diffs = diffsOf(tool);
        if (diffs.length)
            return diffs.map((diff, index) =>
                line(diff.created ? "create" : "edit", diff.path, { path: diff.path, diff }, index),
            );
        if (result.files.length)
            return result.files.map((path, index) => line("edit", path, { path }, index));
    }
    if (tool.name === "execute_command" || tool.name === "run_command") {
        if (!result.command) return [line("run", "a command")];
        const shape = classifyCommand(result.command);
        const screenshots = screenshotsOf(tool);
        // A failure, or a browser check that took screenshots, stays a "Ran" row with its output a click away.
        return [
            failed || (result.exitCode ?? 0) !== 0 || screenshots.length
                ? line("run", result.command, { screenshots })
                : line(shape.kind, shape.text, { path: shape.path }),
        ];
    }
    if (tool.name === "read_skill") return [line("guide", result.summary)];
    return [line("other", result.title)];
}

/**
 * Consecutive tool rows share a section, the way Codex folds "Read files, ran commands".
 * A stage the rows do not already describe, a compaction, or a command's screenshots close it.
 */
export function timelineBlocks(entries: TimelineEntry[]): TimelineBlock[] {
    const blocks: TimelineBlock[] = [];
    for (const entry of entries) {
        if (entry.kind === "stage") {
            if (entry.item.kind === "stage" && TOOL_STAGES.has(entry.item.message ?? "")) continue;
            blocks.push({ kind: "note", key: entry.item.id, item: entry.item });
            continue;
        }
        if (entry.kind !== "tool") continue;
        const lines = toolLines(entry.item);
        const previous = blocks.at(-1);
        if (previous?.kind === "section") previous.lines.push(...lines);
        else blocks.push({ kind: "section", key: lines[0].key, lines });
        // Screenshots follow their command outside the section, so a folded section still shows them.
        const ids = lines.flatMap((line) => line.screenshots ?? []);
        if (ids.length && entry.item.run_id)
            blocks.push({
                kind: "screenshots",
                key: `${lines[0].key}:shots`,
                runId: entry.item.run_id,
                ids,
            });
    }
    return blocks;
}

const PHRASES: Record<LineKind, [string, string]> = {
    read: ["read a file", "read files"],
    view: ["viewed an image", "viewed images"],
    edit: ["edited a file", "edited files"],
    create: ["created a file", "created files"],
    run: ["ran a command", "ran commands"],
    search: ["searched the code", "searched the code"],
    list: ["listed files", "listed files"],
    guide: ["loaded a skill", "loaded skills"],
    other: ["used a tool", "used tools"],
};

/** "Edited files, read files, ran commands": each kind once, in the order it first happened. */
export function sectionTitle(lines: ToolLine[]) {
    const counts = new Map<LineKind, number>();
    for (const line of lines) counts.set(line.kind, (counts.get(line.kind) ?? 0) + 1);
    const text = [...counts].map(([kind, count]) => PHRASES[kind][count === 1 ? 0 : 1]).join(", ");
    return text.charAt(0).toUpperCase() + text.slice(1);
}

export function basename(path: string) {
    return path.slice(path.lastIndexOf("/") + 1) || path;
}

/** "45s", "8m", "1h 3m": Codex's "Worked for" reading. */
export function workedFor(start: string, end?: string) {
    const seconds = Math.max(
        0,
        Math.round(((end ? Date.parse(end) : Date.now()) - Date.parse(start)) / 1000),
    );
    if (!Number.isFinite(seconds)) return "";
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.round(seconds / 60);
    return minutes < 60 ? `${minutes}m` : `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

export type EditedFile = { path: string; added: number; removed: number; counted: boolean };

/** Every file the run changed, with its line counts summed over the run. Runs from before diffs were
 * recorded list their files without counts. */
export function editedFiles(calls: ToolCall[]): EditedFile[] {
    const files = new Map<string, EditedFile>();
    for (const tool of calls) {
        for (const line of toolLines(tool)) {
            if ((line.kind !== "edit" && line.kind !== "create") || !line.path) continue;
            const file = files.get(line.path) ?? {
                path: line.path,
                added: 0,
                removed: 0,
                counted: false,
            };
            if (line.diff) {
                file.added += line.diff.added;
                file.removed += line.diff.removed;
                file.counted = true;
            }
            files.set(line.path, file);
        }
    }
    return [...files.values()];
}
