import { getSessionId } from "@/lib/auth/session";
import { apiClient } from "@/lib/http/client";
import {
    AuthOptions,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserData,
} from "@/types/auth.type";

/**
 * Auth API Service
 */
export const authService = {
    options: async (): Promise<AuthOptions> =>
        (await apiClient.get<AuthOptions>("/auth/options")).data,
    updateProfile: async (data: { name: string; bio: string }): Promise<UserData> =>
        (await apiClient.patch<UserData>("/auth/me", data)).data,
    requestVerification: async (email: string): Promise<{ message: string }> =>
        (await apiClient.post<{ message: string }>("/auth/verification/request", { email })).data,
    confirmVerification: async (token: string): Promise<LoginResponse> =>
        (await apiClient.post<LoginResponse>("/auth/verification/confirm", { token })).data,
    exchangeOAuth: async (token: string): Promise<LoginResponse> =>
        (await apiClient.post<LoginResponse>("/auth/oauth/exchange", { token })).data,
    linkProvider: async (provider: "google" | "github"): Promise<{ url: string }> =>
        (await apiClient.post<{ url: string }>(`/auth/oauth/${provider}/link`)).data,
    /**
     * Login user
     */
    login: async (credentials: LoginRequest): Promise<LoginResponse> => {
        const response = await apiClient.post<LoginResponse>("/auth/login", credentials);
        return response.data;
    },

    /**
     * Register new user
     */
    register: async (data: RegisterRequest): Promise<RegisterResponse> => {
        const response = await apiClient.post<RegisterResponse>("/auth/register", data);
        return response.data;
    },

    /**
     * Get current user data (refresh user info)
     */
    getCurrentUser: async (): Promise<UserData> => {
        const response = await apiClient.get<UserData>("/auth/me");
        return response.data;
    },

    /**
     * After a stream refusal: true when this session renewed its token since `token` was read, so
     * a retry can succeed. False for another session, an unchanged token, or a failed renewal.
     */
    tokenRenewed: async (token: string | null, sessionId: string | null): Promise<boolean> => {
        try {
            // The client's 401 interceptor renews the session on this request when it can.
            await authService.getCurrentUser();
        } catch {
            return false;
        }
        return getSessionId() === sessionId && localStorage.getItem("auth_token") !== token;
    },
};
