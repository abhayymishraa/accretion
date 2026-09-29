// API Response Types

/** This month's build budget, in USD. Resets on the first of the month, UTC. */
export interface CostAllowance {
    unlimited: boolean;
    limit_usd: number;
    remaining_usd: number;
    resets_at: string;
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
