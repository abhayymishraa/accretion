import { apiClient } from "@/lib/http/client";
import type {
    LinkDatabase,
    ProjectDatabase,
    SupabaseAccount,
    SupabaseProject,
    SupabaseRegion,
} from "@/types/supabase.type";

const databasePath = (projectId: string) => `/projects/${encodeURIComponent(projectId)}/database`;

export const supabaseService = {
    account: async (): Promise<SupabaseAccount> =>
        (await apiClient.get<SupabaseAccount>("/supabase/account")).data,

    beginConnect: async (): Promise<string> =>
        (await apiClient.post<{ url: string }>("/supabase/connect")).data.url,

    finishConnect: async (code: string, state: string): Promise<SupabaseAccount> =>
        (await apiClient.post<SupabaseAccount>("/supabase/connect/complete", { code, state })).data,

    disconnect: async (): Promise<void> => {
        await apiClient.delete("/supabase/account");
    },

    projects: async (organizationId: string): Promise<SupabaseProject[]> =>
        (
            await apiClient.get<{ projects: SupabaseProject[] }>("/supabase/projects", {
                params: { organization_id: organizationId },
            })
        ).data.projects,

    regions: async (): Promise<SupabaseRegion[]> =>
        (await apiClient.get<{ regions: SupabaseRegion[] }>("/supabase/regions")).data.regions,

    database: async (projectId: string): Promise<ProjectDatabase> =>
        (await apiClient.get<ProjectDatabase>(databasePath(projectId))).data,

    link: async (projectId: string, body: LinkDatabase): Promise<ProjectDatabase> =>
        (await apiClient.post<ProjectDatabase>(databasePath(projectId), body)).data,

    unlink: async (projectId: string): Promise<void> => {
        await apiClient.delete(databasePath(projectId));
    },
};
