import type { ToolCall } from "@/types/chat.type";

const labels: Record<string, string> = {
    read_skill: "Read skill",
    read_files: "Read files",
    write_files: "Edit files",
    edit_file: "Edit file",
    edit_files: "Edit files",
    execute_command: "Run command",
    inspect_preview: "Inspect preview",
    run_command: "Run command",
    search_project_history: "Search project history",
    list_files: "List files",
};

export function toolLabel(name: string) {
    return labels[name] || name.replaceAll("_", " ");
}

/** Present only fields in the recorded public result; never infer edits or commands. */
export function presentTool(tool: ToolCall) {
    let parsed: unknown;
    const details = tool.details;
    if (details && typeof details === "object" && "version" in details && details.version === 1) {
        parsed = details;
    } else {
        // Old runs and unsupported future versions retain their safe output fallback.
        try {
            parsed = tool.output ? JSON.parse(tool.output) : undefined;
        } catch {
            /* Truncated or plain-text output. */
        }
    }
    const record =
        parsed && typeof parsed === "object" && !Array.isArray(parsed)
            ? (parsed as Record<string, unknown>)
            : undefined;
    const strings = (value: unknown): string[] =>
        Array.isArray(value)
            ? value.filter((item): item is string => typeof item === "string")
            : [];
    const text = (key: string) =>
        typeof record?.[key] === "string" ? (record[key] as string) : "";
    const skillName = tool.name === "read_skill" ? text("name") : "";
    const files = [...new Set(strings(record?.changed_files ?? record?.files ?? record?.paths))];
    const fileCount = typeof record?.file_count === "number" ? record.file_count : files.length;
    const targetFiles = Array.isArray(record?.paths);
    const truncatedFields = strings(record?.truncated_fields);
    const references = strings(record?.message_ids);
    const stdout = text("stdout");
    const stderr = text("stderr");
    let error = text("error");
    if (!error && tool.status === "error") {
        if (stderr) error = stderr;
        else if (typeof parsed === "string") error = parsed;
        else if (parsed === undefined) error = tool.output || "";
    }
    const exitCode = typeof record?.exit_code === "number" ? record.exit_code : undefined;
    const interrupted =
        tool.status === "error" && tool.output === "Run ended before this operation completed.";
    let summary: string;
    if (interrupted) {
        summary = "The run ended before this tool returned a result.";
    } else if (tool.status === "error") {
        summary =
            error.trim().split("\n").find(Boolean)?.slice(0, 220) ||
            "This operation did not complete successfully.";
    } else if (fileCount) {
        const action = targetFiles ? "targeted" : record?.changed_files ? "updated" : "read";
        summary = `${fileCount} ${fileCount === 1 ? "file" : "files"} ${action}`;
    } else if (skillName) {
        summary = text("resource") || skillName;
    } else if (record?.message_ids !== undefined) {
        summary = `${references.length} matching ${references.length === 1 ? "message" : "messages"}`;
    } else if (tool.name === "inspect_preview" && record?.checked === true) {
        summary = `${strings(record.viewports).join(" and ")} preview inspected`;
    } else if (exitCode !== undefined) {
        summary = `Exited with code ${exitCode}`;
    } else if (tool.status === "running") {
        summary = "Waiting for result…";
    } else {
        summary = tool.output ? "Result available" : "No output recorded";
    }
    return {
        fileCount,
        targetFiles,
        truncatedFields,
        command: text("command"),
        inputOmitted: record?.input_omitted === true,
        title: skillName ? `Read skill · ${skillName}` : toolLabel(tool.name),
        summary,
        files,
        references,
        stdout,
        stderr,
        error,
        exitCode,
        interrupted,
        changed: Boolean(record?.changed_files),
        parsed,
    };
}

export type TouchedFile = {
    path: string;
    changed: boolean;
    title: string;
    summary: string;
    durationMs?: number;
};

/** One entry per distinct path across a run; the last tool to touch it wins. */
export function touchedFiles(calls: ToolCall[]): TouchedFile[] {
    const index = new Map<string, TouchedFile>();
    for (const tool of calls) {
        const { files, changed, title, summary } = presentTool(tool);
        for (const path of files)
            index.set(path, { path, changed, title, summary, durationMs: tool.duration_ms });
    }
    return [...index.values()];
}
