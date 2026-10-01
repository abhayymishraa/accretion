import { apiClient } from "@/lib/http/client";
import { ChatResponse, Project } from "@/types/project.type";

type ProjectDeletion = {
    deleted: true;
    storage_cleanup: "completed" | "queued";
    sandbox_cleanup: "completed" | "queued";
};

/**
 * Chat API Service
 */
export const projectService = {
    deleteProject: async (id: string): Promise<ProjectDeletion> => {
        const response = await apiClient.delete<ProjectDeletion>(
            `/projects/${encodeURIComponent(id)}`,
        );
        return response.data;
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

    /**
     * Get list of user's projects
     */
    listProjects: async (): Promise<{ projects: Project[] }> => {
        const response = await apiClient.get<{ projects: Project[] }>("/projects");
        return response.data;
    },
};
