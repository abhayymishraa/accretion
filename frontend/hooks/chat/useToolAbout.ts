"use client";

import { connectionService } from "@/services/service.connections";
import { skillService } from "@/services/service.skills";
import useSWR from "swr";

/**
 * What an opened skill or service row says about itself, looked up by name in the lists the skills menu and the
 * connectors page load, under their keys: once either has loaded, opening a row costs no request. Run events
 * store only the names, so a renamed or removed skill or service shows its name alone.
 */
export function useToolAbout(projectId: string, skill: string, service: string, toolName: string) {
    const skills = useSWR(
        projectId && skill ? (["/projects", projectId, "skills"] as const) : null,
        ([, id]) => skillService.forProject(id),
    );
    const servers = useSWR(service ? ["/mcp-servers"] : null, () => connectionService.list());
    const server = servers.data?.find((item) => item.name === service);
    return {
        skill: skills.data?.find((item) => item.name === skill),
        server,
        tool: server?.tools.find((item) => item.name === toolName),
        loading: skill ? skills.isLoading : servers.isLoading,
        failed: Boolean(skill ? skills.error : servers.error),
    };
}
