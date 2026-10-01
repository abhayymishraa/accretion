export interface ChatResponse {
    status: "running";
    run_id: string;
    chat_id: string;
}

export interface Project {
    id: string;
    user_id: number;
    // Null until the first request is named (agent/run/title.py); show projectName() instead.
    title: string | null;
    app_url: string | null;
    // Null until the first build saves; such a project is listed as a draft.
    latest_saved_revision_id: string | null;
    created_at: string;
    updated_at?: string;
}
