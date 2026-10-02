import { apiClient } from "@/lib/http/client";
import type { AccountPage, AccountRow, AccountStatus } from "@/types/auth.type";

/** Admin-only account operations. */
export const usersService = {
    list: async (status: AccountStatus, search: string, page: number): Promise<AccountPage> =>
        (await apiClient.get<AccountPage>("/users", { params: { status, search, page } })).data,
    approve: async (userId: number): Promise<AccountRow> =>
        (await apiClient.post<AccountRow>(`/users/${userId}/approval`)).data,
};
