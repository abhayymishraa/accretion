import { apiClient } from "@/lib/http/client";
import type { AppServices } from "@/types/appServices.type";

export const appServicesService = {
    get: async (projectId: string): Promise<AppServices> =>
        (
            await apiClient.get<AppServices>(
                `/projects/${encodeURIComponent(projectId)}/app-services`,
            )
        ).data,
};
