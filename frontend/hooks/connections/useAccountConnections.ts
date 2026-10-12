"use client";

import { connectionService } from "@/services/service.connections";
import type { ProjectConnection } from "@/types/connection.type";
import { useState } from "react";
import useSWR from "swr";

/**
 * The services a new project starts with: the account's servers, in the shape the composer reads.
 * Fetched the first time the "/" menu opens, under the Connections page's key, so either fills the
 * other's cache.
 */
export function useAccountConnections() {
    const [wanted, setWanted] = useState(false);
    const { data } = useSWR(wanted ? ["/mcp-servers"] : null, () => connectionService.list());
    const connections: ProjectConnection[] | null = data
        ? data.map((server) => ({
              name: server.name,
              title: server.title,
              description: server.description,
              enabled: server.enabled,
              account_enabled: server.enabled,
              connected: server.connected,
              tool_count: server.tools.filter((tool) => tool.approved).length,
              icon: server.icon,
          }))
        : null;
    return { connections, ensureLoaded: () => setWanted(true) };
}
