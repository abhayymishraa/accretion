import type { DatabaseFinding } from "@/types/supabase.type";

export interface VercelAccount {
    configured: boolean;
    connected: boolean;
}

type PublishStatus = "none" | "uploading" | "building" | "live" | "database" | "failed";

export interface Publish {
    status: PublishStatus;
    url: string | null;
    published_at: string | null;
    /** False when the app changed after the live copy was published. */
    current: boolean;
    message: string | null;
    /** Vercel's page for this app: where a database is added, and the project overview. */
    dashboard_url: string | null;
    logs_url: string | null;
    /** The end of a failed build's log, values hidden. */
    log: string[];
    /** What the last publish's security checks found; a warning each, never a stop. */
    findings: DatabaseFinding[];
    database: "postgres" | "mongo";
}
