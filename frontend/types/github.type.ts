/** The user's GitHub connection. No token ever reaches the browser. */
export interface GithubAccount {
    // Whether this server has a GitHub app set up at all.
    configured: boolean;
    connected: boolean;
    login: string | null;
    // Whether Accretion's GitHub app can reach the user's repositories.
    installed: boolean;
}

export interface GithubRepo {
    id: number;
    full_name: string;
    private: boolean;
    updated_at: string | null;
}

export type RepoStatus =
    | "synced"
    | "pushing"
    | "pulling"
    | "conflict"
    | "blocked"
    | "approval"
    | "reconnect"
    | "gone"
    | "error";

/** The repository a project saves to, and where the two sides last agreed. */
export interface ProjectRepo {
    linked: boolean;
    owner: string | null;
    name: string | null;
    url: string | null;
    branch: string | null;
    default_branch: string | null;
    status: RepoStatus | null;
    // The one plain status line.
    message: string | null;
    // File paths or a pull request address. Never a value.
    detail: { files?: string[]; pull_url?: string };
}

export interface RepoBranch {
    name: string;
    current: boolean;
}
