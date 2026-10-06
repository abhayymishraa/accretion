import type { CatalogConnection, Connection, ConnectionAuth } from "@/types/connection.type";

/** One service on the page: a catalog entry, the user's server for it, or both. */
export interface ServiceEntry {
    /** The page's address: the catalog id, or the server id for a service added by address. */
    key: string;
    /** Which logo to show: the catalog id, or the server's name. */
    logo: string;
    title: string;
    description: string;
    url: string;
    auth: ConnectionAuth;
    catalog: CatalogConnection | null;
    server: Connection | null;
}

export type Badge = { tone: "ok" | "wait" | "warn"; text: string } | null;

/** Every catalog service, joined to the user's server for it, then the servers added by address. */
export function serviceEntries(catalog: CatalogConnection[], servers: Connection[]) {
    const byName = new Map(servers.map((server) => [server.name, server]));
    const listed = new Set(catalog.map((entry) => entry.id));
    const entries: ServiceEntry[] = catalog.map((entry) => ({
        key: entry.id,
        logo: entry.id,
        title: entry.title,
        description: entry.description,
        url: entry.url,
        auth: entry.auth,
        catalog: entry,
        server: byName.get(entry.id) ?? null,
    }));
    for (const server of servers)
        if (!listed.has(server.name))
            entries.push({
                key: server.id,
                logo: server.name,
                title: server.title,
                description: server.description,
                url: server.url,
                auth: server.auth,
                catalog: null,
                server,
            });
    return entries;
}

/** The entry a detail page shows: by catalog id, server id, or server name (the workspace tab links by name). */
export function findEntry(entries: ServiceEntry[], key: string) {
    const id = decodeURIComponent(key);
    return (
        entries.find(
            (entry) => entry.key === id || entry.server?.id === id || entry.server?.name === id,
        ) ?? null
    );
}

/** The state a card and a detail page show: none until the service is added. */
export function badge(entry: ServiceEntry): Badge {
    const { server } = entry;
    if (!server) return null;
    if (!server.connected)
        return { tone: "wait", text: server.auth === "header" ? "Needs a key" : "Needs sign-in" };
    if (server.tools.some((tool) => tool.changed)) return { tone: "warn", text: "Check tools" };
    return { tone: "ok", text: "Connected" };
}
