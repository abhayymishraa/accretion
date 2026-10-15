import { apiClient } from "@/lib/http/client";
import type { Publish, VercelAccount } from "@/types/vercel.type";

const publishPath = (projectId: string) => `/projects/${encodeURIComponent(projectId)}/publish`;

export const vercelService = {
    account: async (): Promise<VercelAccount> =>
        (await apiClient.get<VercelAccount>("/vercel/account")).data,

    beginConnect: async (): Promise<string> =>
        (await apiClient.post<{ url: string }>("/vercel/connect")).data.url,

    finishConnect: async (code: string, state: string): Promise<VercelAccount> =>
        (await apiClient.post<VercelAccount>("/vercel/connect/complete", { code, state })).data,

    publish: async (projectId: string): Promise<Publish> =>
        (await apiClient.get<Publish>(publishPath(projectId))).data,

    start: async (projectId: string): Promise<Publish> =>
        (await apiClient.post<Publish>(publishPath(projectId))).data,

    unpublish: async (projectId: string): Promise<void> => {
        await apiClient.delete(publishPath(projectId));
    },
};
