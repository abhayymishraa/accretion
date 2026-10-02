"use client";

import { modelService } from "@/services/service.models";
import type { ModelOption } from "@/types/models.type";
import axios from "axios";
import { useEffect, useState } from "react";

// The offered models change only with a deploy, so one request serves every page until a reload.
// A rejected pick (attempt > 0) asks again.
let listed: Promise<ModelOption[]> | null = null;

// The picker's options and the current choice (spec 4.2). "auto" is always offered.
export function useModelChoice(remembered: string | undefined) {
    const [models, setModels] = useState<ModelOption[] | null>(null);
    const [picked, setPicked] = useState<string | null>(null);
    const [attempt, setAttempt] = useState(0);
    useEffect(() => {
        let disposed = false;
        if (!listed || attempt > 0) listed = modelService.list();
        const request = listed;
        request
            .then((list) => {
                if (!disposed) setModels(list);
            })
            .catch(() => {
                if (listed === request) listed = null;
                // Without the list the picker offers Auto only; the server still validates a pick.
            });
        return () => {
            disposed = true;
        };
    }, [attempt]);
    // Until the list has loaded, keep the remembered pick rather than silently sending Auto,
    // which would also overwrite the user's saved default. A pick no longer offered falls back.
    const wanted = picked ?? remembered ?? "auto";
    const choice =
        wanted === "auto" || models === null || models.some((m) => m.id === wanted)
            ? wanted
            : "auto";
    // Admission refuses a model that became unusable after the list loaded (422 on model_choice):
    // fall back to Auto and reload the list, so the next send works without a page reload.
    const rejected = (error: unknown) => {
        if (
            axios.isAxiosError(error) &&
            error.response?.status === 422 &&
            JSON.stringify(error.response.data).includes("model_choice")
        ) {
            setPicked("auto");
            setAttempt((value) => value + 1);
        }
    };
    return { models: models ?? [], choice, setChoice: setPicked, rejected };
}
