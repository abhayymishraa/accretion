import apiClient from "@/lib/http/client";
import type { HistoryPage, RunEvent } from "@/types/chat.type";

export const historyService = {
    async page(chatId: string, signal: AbortSignal, before?: string) {
        return (
            await apiClient.get<HistoryPage>(`/projects/${chatId}/messages`, {
                params: { limit: 50, before },
                signal,
            })
        ).data;
    },
    // Every page of a run's steps: one page stops at the server's page size, which a long run passes.
    async details(runId: string, signal: AbortSignal) {
        const events: RunEvent[] = [];
        let after = 0;
        for (;;) {
            const page = (
                await apiClient.get<{
                    events: RunEvent[];
                    next_sequence: number;
                    has_more: boolean;
                }>(`/runs/${runId}/events`, { params: { after_sequence: after }, signal })
            ).data;
            events.push(...page.events);
            if (!page.has_more) return { events };
            after = page.next_sequence;
        }
    },
};
