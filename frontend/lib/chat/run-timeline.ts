import type { ActivityItem, ToolCall } from "@/types/chat.type";

export type TimelineEntry =
    | { kind: "stage"; order: number; item: ActivityItem }
    | { kind: "tool"; order: number; item: ToolCall }
    | { kind: "group"; order: number; name: string; items: ToolCall[] };

/**
 * Event ids are `<runId>:<n>` (agent/service.py). The counter defines order, so
 * the numeric suffix is parsed rather than compared as a string: ":10" sorts
 * before ":2" lexically. Runs that predate event ids keep their old grouping,
 * stages ahead of tools, instead of being interleaved at random.
 */
function eventOrder(id: string | undefined, fallback: number): number {
    const suffix = id?.slice(id.lastIndexOf(":") + 1);
    const order = Number(suffix);
    return Number.isFinite(order) ? order : fallback;
}

/** Stages and tool calls as one chronological list, the order they happened. */
export function timelineEntries(activity: ActivityItem[], calls: ToolCall[]): TimelineEntry[] {
    const entries: TimelineEntry[] = [
        ...activity.map((item) => ({
            kind: "stage" as const,
            order: eventOrder(item.id, Number.MIN_SAFE_INTEGER),
            item,
        })),
        ...calls.map((item) => ({
            kind: "tool" as const,
            order: eventOrder(item.event_id, Number.MAX_SAFE_INTEGER),
            item,
        })),
    ];
    // Sort is stable, so equal orders keep insertion order.
    return entries.sort((a, b) => a.order - b.order);
}

/**
 * Collapse consecutive calls of the same tool into one row. Only successful
 * runs group: a failure or an in-flight call always keeps its own row, because
 * hiding either one inside a collapsed group is how a problem goes unnoticed.
 */
export function groupTimeline(entries: TimelineEntry[]): TimelineEntry[] {
    const grouped: TimelineEntry[] = [];
    for (const entry of entries) {
        const previous = grouped.at(-1);
        const groupable = entry.kind === "tool" && entry.item.status === "success";
        if (!groupable) {
            grouped.push(entry);
            continue;
        }
        if (previous?.kind === "group" && previous.name === entry.item.name) {
            previous.items.push(entry.item);
            continue;
        }
        if (previous?.kind === "tool" && previous.item.name === entry.item.name) {
            grouped[grouped.length - 1] = {
                kind: "group",
                order: previous.order,
                name: entry.item.name,
                items: [previous.item, entry.item],
            };
            continue;
        }
        grouped.push(entry);
    }
    return grouped;
}
