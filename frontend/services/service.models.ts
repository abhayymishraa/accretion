import apiClient from "@/lib/http/client";
import type { ModelOption } from "@/types/models.type";

export const modelService = {
    async list(): Promise<ModelOption[]> {
        return (await apiClient.get<{ models: ModelOption[] }>("/models")).data.models;
    },
};
