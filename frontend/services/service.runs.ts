import apiClient from "@/lib/http/client";
import type { DecisionAction } from "@/types/chat.type";
export const runService = {
    async start(chatId: string, prompt: string, mode: "auto" | "plan" = "auto") {
        return (
            await apiClient.post<{ run_id: string; tokens_remaining: number }>(
                `/projects/${chatId}/runs`,
                { prompt, mode },
            )
        ).data;
    },
    async cancel(runId: string) {
        await apiClient.post(`/runs/${runId}/cancel`);
    },
    async respond(runId: string, action: DecisionAction, text = "") {
        await apiClient.post(`/runs/${runId}/respond`, { action, text });
    },
};
