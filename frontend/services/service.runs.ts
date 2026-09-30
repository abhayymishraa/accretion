import apiClient from "@/lib/http/client";
import type { DecisionAction } from "@/types/chat.type";
export const runService = {
    async start(
        chatId: string,
        prompt: string,
        mode: "auto" | "plan" = "auto",
        modelChoice = "auto",
    ) {
        return (
            await apiClient.post<{ run_id: string }>(`/projects/${chatId}/runs`, {
                prompt,
                mode,
                model_choice: modelChoice,
            })
        ).data;
    },
    // Spec 5 steering: an update for a build that is still running.
    async steer(runId: string, text: string) {
        await apiClient.post(`/runs/${runId}/steer`, { text });
    },
    async cancel(runId: string) {
        await apiClient.post(`/runs/${runId}/cancel`);
    },
    async respond(runId: string, action: DecisionAction, text = "") {
        await apiClient.post(`/runs/${runId}/respond`, { action, text });
    },
    // A browser check's screenshot; the route needs the session header, so it cannot be an <img src>.
    async screenshot(runId: string, screenshotId: string, signal: AbortSignal) {
        return (
            await apiClient.get<Blob>(`/runs/${runId}/screenshots/${screenshotId}`, {
                responseType: "blob",
                signal,
            })
        ).data;
    },
};
