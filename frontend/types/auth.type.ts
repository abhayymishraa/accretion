// API Response Types

/** This month's build budget, in USD. Resets on the first of the month, UTC; a demo's never does (null). */
export interface CostAllowance {
    unlimited: boolean;
    limit_usd: number;
    remaining_usd: number;
    resets_at: string | null;
}

export interface UserData {
    id: number;
    email: string;
    name: string;
    cost_allowance?: CostAllowance | null;
    bio?: string;
    email_verified?: boolean;
    created_at?: string;
    providers?: string[];
    default_model_choice?: string;
    waitlisted?: boolean;
}

/** One account on the admin's waitlist page. `approved_at` is null while it waits. */
export interface AccountRow {
    id: number;
    email: string;
    name: string;
    email_verified: boolean;
    created_at: string;
    approved_at: string | null;
}

export type AccountStatus = "waiting" | "approved" | "all";

/** One page of accounts, with totals across every account. */
export interface AccountPage {
    items: AccountRow[];
    total: number;
    page: number;
    page_size: number;
    counts: { waiting: number; approved: number; unconfirmed: number };
}

export interface LoginResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export interface RegisterResponse {
    verification_required: boolean;
    message: string;
}

export interface AuthOptions {
    providers: { google: boolean; github: boolean };
    email_verification: boolean;
}

export interface LoginRequest {
    email: string;
    password: string;
}

export interface RegisterRequest {
    email: string;
    password: string;
    name: string;
}

/** A demo account on the admin page. `spent_usd` is its model spend, all time. */
export interface DemoAccount {
    id: number;
    name: string;
    created_at: string;
    link_active: boolean;
    spent_usd: number;
    default_model_choice: string;
}

/** A new demo link's raw token: shown once, only its digest is stored. */
export interface DemoLink {
    user_id: number;
    token: string;
}

/** One build of a demo account, read-only for the admin. */
export interface AccountRun {
    id: string;
    project_title: string | null;
    prompt: string;
    status: string;
    created_at: string;
}
