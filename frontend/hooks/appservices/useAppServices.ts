"use client";

import { appServicesService } from "@/services/service.appServices";
import useSWR from "swr";

/** The App services tab: the app's sign-in methods. */
export function useAppServices(projectId: string) {
    const { data, error, mutate } = useSWR(
        ["/projects", projectId, "app-services"] as const,
        ([, id]) => appServicesService.get(id),
    );
    return {
        services: data ?? null,
        failed: Boolean(error),
        retry: () => mutate(),
    };
}
