export interface ChatResponse {
    status: "running";
    run_id: string;
    chat_id: string;
}

export interface Project {
    id: string;
    user_id: number;
    title: string;
    app_url: string | null;
    created_at: string;
    updated_at?: string;
}
