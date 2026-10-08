import type { ToolCall } from "@/types/chat.type";

const labels: Record<string, string> = {
    read_skill: "Loaded skill",
    read_files: "Read files",
    write_files: "Edit files",
    edit_file: "Edit file",
    edit_files: "Edit files",
    execute_command: "Run command",
    run_command: "Run command",
    search_project_history: "Search project history",
    list_files: "List files",
    // The timeline puts "Used" before these, so they name the thing, not the action.
    tool_search: "a service tool search",
    call_mcp_tool: "a connected service",
};

// A connected service's tool runs as mcp__<service>__<tool>.
const SERVICE_TOOL = /^mcp__(.+?)__(.+)$/;

function toolLabel(name: string) {
    const service = SERVICE_TOOL.exec(name);
    if (service) return `${service[1]} · ${service[2].replaceAll("_", " ")}`;
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
    } else if (exitCode !== undefined) {
        summary = `Exited with code ${exitCode}`;
    } else if (tool.status === "running") {
        summary = "Waiting for result…";
    } else {
        summary = tool.output ? "Result available" : "No output recorded";
    }
    return {
        targetFiles,
        truncatedFields,
        command: text("command"),
        pageSummary: text("page_summary"),
        pageProblems: strings(record?.page_problems),
        browserRestarted: text("browser_restarted"),
        inputOmitted: record?.input_omitted === true,
        // call_mcp_tool names the service tool it ran in its public fields; label it like a direct call.
        title: skillName
            ? `Read skill · ${skillName}`
            : toolLabel(
                  text("tool_name") ? `mcp__${text("service")}__${text("tool_name")}` : tool.name,
              ),
        summary,
        skill: skillName,
        service: text("service"),
        toolName: text("tool_name"),
        files,
        references,
        stdout,
        stderr,
        error,
        exitCode,
        changed: Boolean(record?.changed_files),
    };
}
