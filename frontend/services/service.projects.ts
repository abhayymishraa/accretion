import { apiClient } from "@/lib/http/client";
import { ChatResponse, Project } from "@/types/project.type";

/**
 * Chat API Service
 */
export const projectService = {
    deleteProject: async (id: string): Promise<void> => {
        await apiClient.delete(`/projects/${encodeURIComponent(id)}`);
    },
    /**
     * Create or start a new chat
     */
    createChat: async (prompt: string, modelChoice = "auto"): Promise<ChatResponse> => {
        const response = await apiClient.post<ChatResponse>("/projects", {
            prompt,
            model_choice: modelChoice,
        });
        return response.data;
    },

    renameProject: async (id: string, title: string): Promise<{ title: string }> => {
        const response = await apiClient.patch<{ title: string }>(
            `/projects/${encodeURIComponent(id)}`,
            { title },
        );
        return response.data;
    },

    // The card image; the route needs the session header, so it cannot be an <img src>. Each cover
    // has its own id, so the browser keeps each one.
    cover: async (id: string, coverId: string): Promise<Blob> => {
        const response = await apiClient.get<Blob>(
            `/projects/${encodeURIComponent(id)}/covers/${encodeURIComponent(coverId)}`,
            { responseType: "blob" },
        );
        return response.data;
    },

    /**
     * Get list of user's projects
     */
    listProjects: async (): Promise<{ projects: Project[] }> => {
        const response = await apiClient.get<{ projects: Project[] }>("/projects");
        return response.data;
    },
};
