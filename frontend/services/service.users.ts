import { apiClient } from "@/lib/http/client";
import type {
    AccountPage,
    AccountRow,
    AccountRun,
    AccountStatus,
    DemoAccount,
    DemoLink,
} from "@/types/auth.type";

/** Admin-only account operations. */
export const usersService = {
    list: async (status: AccountStatus, search: string, page: number): Promise<AccountPage> =>
        (await apiClient.get<AccountPage>("/users", { params: { status, search, page } })).data,
    approve: async (userId: number): Promise<AccountRow> =>
        (await apiClient.post<AccountRow>(`/users/${userId}/approval`)).data,
    listDemo: async (): Promise<DemoAccount[]> =>
        (await apiClient.get<DemoAccount[]>("/users/demo")).data,
    createDemo: async (name: string): Promise<DemoLink> =>
        (await apiClient.post<DemoLink>("/users/demo", { name })).data,
    replaceDemoLink: async (userId: number): Promise<DemoLink> =>
        (await apiClient.post<DemoLink>(`/users/${userId}/demo-link`)).data,
    revokeDemoLink: async (userId: number): Promise<void> => {
        await apiClient.delete(`/users/${userId}/demo-link`);
    },
    runs: async (userId: number): Promise<AccountRun[]> =>
        (await apiClient.get<AccountRun[]>(`/users/${userId}/runs`)).data,
};
