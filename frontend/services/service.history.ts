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
    async details(runId: string, signal: AbortSignal) {
        return (await apiClient.get<{ events: RunEvent[] }>(`/runs/${runId}/events`, { signal }))
            .data;
    },
};
