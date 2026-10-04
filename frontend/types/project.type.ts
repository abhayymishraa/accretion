import type { RunStatus } from "./chat.type";

export interface ChatResponse {
    status: RunStatus;
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
    // Null until a succeeded run takes a screenshot; the card then shows a banner instead.
    cover_updated_at: string | null;
    created_at: string;
    updated_at?: string;
}
