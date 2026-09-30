export type RunStatus =
    | "running"
    | "succeeded"
    | "failed"
    | "cancelled"
    | "stopped"
    | "timed_out"
    | "interrupted"
    | "awaiting_input"
    | "answered";
export interface WorkflowProposal {
    kind: "execute" | "clarify" | "plan" | "answer";
    summary: string;
    steps: string[];
    question?: string;
    options?: string[];
    revision_id?: string | null;
    resolution?: DecisionAction;
    continuation_id?: string | null;
}
export type DecisionAction = "approve" | "answer" | "revise" | "dismiss";
export interface ToolCall {
    id?: string;
    name: string;
    status: "success" | "error" | "running";
    output?: string;
    duration_ms?: number;
    details?: unknown;
    run_id?: string;
    event_id?: string;
}
export interface ActivityItem {
    id: string;
    kind: "stage" | "verification";
    created_at: string;
    message?: string;
    ok?: boolean;
    checks?: unknown;
    compacted?: boolean;
}
export interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    created_at: string;
    event_type?: string;
    tool_calls?: ToolCall[];
    activity?: ActivityItem[];
    run_status?: RunStatus;
    finished_at?: string;
    details_pending?: boolean;
    details_version?: number;
    workflow?: WorkflowProposal | null;
}
export interface HistoryPage {
    messages: Message[];
    next_cursor: string | null;
    active_run_id: string | null;
    pending_run_id?: string | null;
}
export interface RunEvent {
    e: string;
    run_id: string;
    event_id: string;
    created_at: string;
    name?: string;
    call_id?: string;
    ok?: boolean;
    status?: RunStatus;
    message?: string;
    output?: string;
    details?: unknown;
    duration_ms?: number;
    url?: string | null;
    checks?: unknown;
    compacted?: boolean;
    workflow?: WorkflowProposal | null;
}
export interface RunSnapshot {
    id: string;
    created_at?: string;
    status: RunStatus;
    reason?: string;
    events: RunEvent[];
    workflow?: WorkflowProposal | null;
}
export interface WebSocketHandlers {
    terminalRuns: Set<string>;
    setIsBuilding: (value: boolean) => void;
    setRunId: (id: string | null) => void;
    setPendingRunId: (id: string | null) => void;
    setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
    setAppUrl: (url: string | null) => void;
    setError: (error: string | null) => void;
    consolidateMessages: (messages: Message[]) => Message[];
}
