import { apiClient } from "@/lib/http/client";
import type { GithubAccount, GithubRepo, ProjectRepo, RepoBranch } from "@/types/github.type";

const repoPath = (projectId: string) => `/projects/${encodeURIComponent(projectId)}/repo`;

export const githubService = {
    account: async (): Promise<GithubAccount> =>
        (await apiClient.get<GithubAccount>("/github/account")).data,

    beginConnect: async (): Promise<string> =>
        (await apiClient.post<{ url: string }>("/github/connect")).data.url,

    finishConnect: async (params: {
        code: string;
        state: string;
        installation_id?: number;
    }): Promise<GithubAccount> =>
        (await apiClient.post<GithubAccount>("/github/connect/complete", params)).data,

    disconnect: async (): Promise<void> => {
        await apiClient.delete("/github/account");
    },

    repos: async (): Promise<GithubRepo[]> =>
        (await apiClient.get<{ repos: GithubRepo[] }>("/github/repos")).data.repos,

    importRepo: async (repoId: number): Promise<string> =>
        (await apiClient.post<{ project_id: string }>("/github/imports", { repo_id: repoId })).data
            .project_id,

    repo: async (projectId: string): Promise<ProjectRepo> =>
        (await apiClient.get<ProjectRepo>(repoPath(projectId))).data,

    createRepo: async (projectId: string, name?: string): Promise<ProjectRepo> =>
        (await apiClient.post<ProjectRepo>(repoPath(projectId), { name: name || undefined })).data,

    unlink: async (projectId: string): Promise<void> => {
        await apiClient.delete(repoPath(projectId));
    },

    sync: async (projectId: string): Promise<ProjectRepo> =>
        (await apiClient.post<ProjectRepo>(`${repoPath(projectId)}/sync`)).data,

    approveWorkflows: async (projectId: string): Promise<ProjectRepo> =>
        (await apiClient.post<ProjectRepo>(`${repoPath(projectId)}/workflows/approve`)).data,

    branches: async (projectId: string): Promise<RepoBranch[]> =>
        (await apiClient.get<{ branches: RepoBranch[] }>(`${repoPath(projectId)}/branches`)).data
            .branches,

    createBranch: async (projectId: string, name: string): Promise<ProjectRepo> =>
        (await apiClient.post<ProjectRepo>(`${repoPath(projectId)}/branches`, { name })).data,

    switchBranch: async (projectId: string, name: string): Promise<ProjectRepo> =>
        (await apiClient.put<ProjectRepo>(`${repoPath(projectId)}/branch`, { name })).data,

    openPull: async (projectId: string): Promise<string> =>
        (await apiClient.post<{ url: string }>(`${repoPath(projectId)}/pulls`, {})).data.url,
};
