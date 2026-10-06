export type ConnectionAuth = "none" | "header" | "oauth";

export interface CatalogConnection {
    id: string;
    title: string;
    description: string;
    url: string;
    auth: ConnectionAuth;
    maker: string;
    docs_url: string;
}

export interface ConnectionTool {
    name: string;
    description: string;
    read_only: boolean;
    approved: boolean;
    // The server changed it after the user approved it; it stays off until approved again.
    changed: boolean;
}

export interface Connection {
    id: string;
    name: string;
    title: string;
    description: string;
    url: string;
    auth: ConnectionAuth;
    key_hint: string | null;
    // Has what it needs to sign in.
    connected: boolean;
    enabled: boolean;
    tools: ConnectionTool[];
    // A data URI: the logo the user uploaded, or the one the server names for itself.
    icon: string | null;
}

export interface ProjectConnection {
    name: string;
    title: string;
    description: string;
    enabled: boolean;
    account_enabled: boolean;
    connected: boolean;
    tool_count: number;
    icon: string | null;
}
