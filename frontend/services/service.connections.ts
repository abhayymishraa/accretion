import { apiClient } from "@/lib/http/client";
import type { CatalogConnection, Connection, ProjectConnection } from "@/types/connection.type";

const serverPath = (id: string) => `/mcp-servers/${encodeURIComponent(id)}`;

export const connectionService = {
    catalog: async (): Promise<CatalogConnection[]> =>
        (await apiClient.get<{ servers: CatalogConnection[] }>("/mcp-catalog")).data.servers,

    list: async (): Promise<Connection[]> =>
        (await apiClient.get<{ servers: Connection[] }>("/mcp-servers")).data.servers,

    add: async (
        source: { catalog_id: string } | { url: string; title?: string },
    ): Promise<Connection> => (await apiClient.post<Connection>("/mcp-servers", source)).data,

    saveKey: async (id: string, value: string, headerName?: string): Promise<Connection> =>
        (
            await apiClient.put<Connection>(`${serverPath(id)}/key`, {
                value,
                header_name: headerName,
            })
        ).data,

    clearKey: async (id: string): Promise<Connection> =>
        (await apiClient.delete<Connection>(`${serverPath(id)}/key`)).data,

    saveIcon: async (id: string, dataUri: string): Promise<Connection> =>
        (await apiClient.put<Connection>(`${serverPath(id)}/icon`, { data_uri: dataUri })).data,

    beginSignIn: async (id: string): Promise<string> =>
        (await apiClient.post<{ authorization_url: string }>(`${serverPath(id)}/sign-in`)).data
            .authorization_url,

    finishSignIn: async (state: string, code: string, iss: string | null): Promise<Connection> =>
        (
            await apiClient.post<Connection>("/mcp-servers/sign-in/complete", {
                state,
                code,
                iss: iss ?? undefined,
            })
        ).data,

    refreshTools: async (id: string): Promise<Connection> =>
        (await apiClient.post<Connection>(`${serverPath(id)}/tools/refresh`)).data,

    approveTools: async (id: string, approved: string[]): Promise<Connection> =>
        (await apiClient.put<Connection>(`${serverPath(id)}/tools`, { approved })).data,

    setEnabled: async (id: string, enabled: boolean): Promise<Connection> =>
        (await apiClient.patch<Connection>(serverPath(id), { enabled })).data,

    remove: async (id: string): Promise<void> => {
        await apiClient.delete(serverPath(id));
    },

    forProject: async (projectId: string): Promise<ProjectConnection[]> =>
        (
            await apiClient.get<{ servers: ProjectConnection[] }>(
                `/projects/${encodeURIComponent(projectId)}/mcp-servers`,
            )
        ).data.servers,

    setForProject: async (projectId: string, name: string, enabled: boolean): Promise<void> => {
        await apiClient.put(
            `/projects/${encodeURIComponent(projectId)}/mcp-servers/${encodeURIComponent(name)}`,
            { enabled },
        );
    },
};
