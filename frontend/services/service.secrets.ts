import { apiClient } from "@/lib/http/client";
import type { ProjectSecrets } from "@/types/secret.type";

const secretsPath = (projectId: string) => `/projects/${encodeURIComponent(projectId)}/secrets`;
const keyPath = (projectId: string, name: string) =>
    `${secretsPath(projectId)}/${encodeURIComponent(name)}`;

export const secretService = {
    list: async (projectId: string): Promise<ProjectSecrets> =>
        (await apiClient.get<ProjectSecrets>(secretsPath(projectId))).data,

    save: async (projectId: string, name: string, value: string): Promise<ProjectSecrets> =>
        (await apiClient.put<ProjectSecrets>(keyPath(projectId, name), { value })).data,

    remove: async (projectId: string, name: string): Promise<ProjectSecrets> =>
        (await apiClient.delete<ProjectSecrets>(keyPath(projectId, name))).data,
};
