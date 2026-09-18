// API Response Types

export interface UserData {
    id: number;
    email: string;
    name: string;
    tokens_remaining: number;
    credits_limit: number;
    tokens_reset_at?: string | null;
    credits_unlimited?: boolean;
    bio?: string;
    email_verified?: boolean;
    created_at?: string;
    providers?: string[];
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
