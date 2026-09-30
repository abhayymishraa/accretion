import type { ActivityItem, ToolCall } from "@/types/chat.type";

export type TimelineEntry =
    | { kind: "stage"; order: number; item: ActivityItem }
    | { kind: "tool"; order: number; item: ToolCall };

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
