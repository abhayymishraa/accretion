export interface SupabaseOrganization {
    id: string;
    name: string;
}

/** The user's Supabase sign-in. No token ever reaches the browser. */
export interface SupabaseAccount {
    configured: boolean;
    connected: boolean;
    organizations: SupabaseOrganization[];
}

export interface SupabaseProject {
    ref: string;
    name: string;
    region: string;
    status: string;
}

export interface SupabaseRegion {
    id: string;
    name: string;
}

/** A check Supabase runs on the database, such as a table anyone can read. */
export interface DatabaseFinding {
    title: string;
    detail: string;
    remediation: string;
    level: string;
}

export type DatabaseStatus = "creating" | "moving" | "ready" | "reconnect" | "error";

/** The Supabase project an app uses, if any. */
export interface ProjectDatabase {
    // False for an app whose database Supabase cannot hold.
    offered: boolean;
    linked: boolean;
    ref: string | null;
    name: string | null;
    region: string | null;
    status: DatabaseStatus | null;
    message: string | null;
    dashboard_url: string | null;
    findings: DatabaseFinding[];
}

export type LinkDatabase =
    | { mode: "create"; organization_id: string; name: string; region: string }
    | { mode: "existing"; ref: string };
