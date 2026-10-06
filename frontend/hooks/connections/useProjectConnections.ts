"use client";

import { patchSkill } from "@/hooks/skills/useSkillLibrary";
import { connectionService } from "@/services/service.connections";
import { useCallback, useState } from "react";
import useSWR from "swr";

/**
 * The connections a project can use. Nothing is fetched until a caller asks (the "/" menu, or the Connectors tab
 * opening); a switch shows at once and rolls back if the save fails.
 */
export function useProjectConnections(projectId: string) {
    const [wanted, setWanted] = useState(false);
    // Stable, so the effects that call it run once, not on every render.
    const ensureLoaded = useCallback(() => setWanted(true), []);
    const { data, error, mutate } = useSWR(
        wanted ? (["/projects", projectId, "mcp-servers"] as const) : null,
        ([, id]) => connectionService.forProject(id),
    );
    return {
        connections: data ?? null,
        failed: Boolean(error),
        retry: () => mutate(),
        ensureLoaded,
        setEnabled: (name: string, enabled: boolean) =>
            patchSkill(mutate, name, { enabled }, () =>
                connectionService.setForProject(projectId, name, enabled),
            ),
    };
}
