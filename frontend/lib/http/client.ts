import { clearSession, getSessionId, storeTokens } from "@/lib/auth/session";
import type { LoginResponse } from "@/types/auth.type";
import axios, { type InternalAxiosRequestConfig } from "axios";

// API Base URL - change based on environment
import { API_BASE_URL } from "@/config/env";

// Create axios instance with default config
export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json",
    },
    timeout: 30000, // 30 seconds
});

type SessionRequest = InternalAxiosRequestConfig & {
    sessionId?: string | null;
    accessToken?: string | null;
    retriedAfterRefresh?: boolean;
};

const publicAuthPaths = new Set([
    "/auth/login",
    "/auth/register",
    "/auth/options",
    "/auth/refresh",
    "/auth/oauth/exchange",
    "/auth/verification/confirm",
    "/auth/verification/request",
]);
let pendingRefresh: { sessionId: string; promise: Promise<void> } | null = null;

function endSession(sessionId: string, destination = "/signin") {
    if (getSessionId() !== sessionId) return;
    clearSession();
    if (window.location.pathname !== destination) window.location.replace(destination);
}

async function renewSession(sessionId: string) {
    if (getSessionId() !== sessionId) throw new Error("Your session changed. Try again.");
    if (pendingRefresh?.sessionId === sessionId) return pendingRefresh.promise;
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
        endSession(sessionId);
        throw new Error("Please sign in again to continue.");
    }
    const promise = (async () => {
        try {
            // Use Axios directly so refresh failures never enter the retry interceptor.
            const { data } = await axios.post<LoginResponse>(
                `${API_BASE_URL}/auth/refresh`,
                { refresh_token: refreshToken },
                { timeout: 30000 },
            );
            if (getSessionId() !== sessionId) throw new Error("Your session changed. Try again.");
            // Another tab may have renewed this session while this request was pending.
            if (localStorage.getItem("refresh_token") !== refreshToken) return;
            storeTokens(data);
        } catch (error) {
            if (
                getSessionId() === sessionId &&
                localStorage.getItem("refresh_token") !== refreshToken
            )
                return;
            if (axios.isAxiosError(error) && [401, 403].includes(error.response?.status ?? 0)) {
                endSession(sessionId);
                throw new Error("Your session has expired. Please sign in again.");
            }
            // A network outage or server error must not erase valid credentials.
            throw new Error("Could not renew your session. Please try again.");
        }
    })();
    const pending = { sessionId, promise };
    pendingRefresh = pending;
    try {
        await promise;
    } finally {
        if (pendingRefresh === pending) pendingRefresh = null;
    }
}

// Request interceptor - Add auth token to requests
apiClient.interceptors.request.use(
    (config) => {
        if (publicAuthPaths.has(config.url || "")) return config;
        const request = config as SessionRequest;
        const sessionId = getSessionId();
        if (request.retriedAfterRefresh && request.sessionId !== sessionId) {
            throw new Error("Your session changed. Try again.");
        }
        // Get token from localStorage
        const token = localStorage.getItem("auth_token");
        request.sessionId = sessionId;
        request.accessToken = token;

        if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
        }

        return config;
    },
    (error) => {
        return Promise.reject(error);
    },
);

// Response interceptor - Handle errors globally
apiClient.interceptors.response.use(
    (response) => {
        const request = response.config as SessionRequest;
        if (request.sessionId && request.sessionId !== getSessionId()) {
            throw new Error("Your session changed. Try again.");
        }
        // Every page checks the session through /auth/me, which a waitlisted account may
        // still call. Sending it to /waitlist here closes pages like /profile that call
        // nothing else.
        if (
            request.url === "/auth/me" &&
            response.data?.waitlisted &&
            window.location.pathname !== "/waitlist"
        ) {
            window.location.replace("/waitlist");
        }
        return response;
    },
    async (error) => {
        const request = error.config as SessionRequest | undefined;
        if (request?.sessionId && request.sessionId !== getSessionId()) {
            throw new Error("Your session changed. Try again.");
        }
        const detail = error.response?.data?.detail;
        if (
            request?.sessionId &&
            error.response?.status === 403 &&
            typeof detail === "string" &&
            detail.startsWith("Verify your email")
        ) {
            endSession(request.sessionId, "/verify-email");
        }
        if (error.response?.status === 401 && request?.sessionId && request.accessToken) {
            if (request.retriedAfterRefresh) {
                if (localStorage.getItem("auth_token") === request.accessToken)
                    endSession(request.sessionId);
            } else {
                request.retriedAfterRefresh = true;
                // A late 401 may belong to a token another request has already renewed.
                if (localStorage.getItem("auth_token") === request.accessToken) {
                    await renewSession(request.sessionId);
                }
                return apiClient.request(request);
            }
        }

        // FastAPI validation errors contain objects, not a displayable string.
        let errorMessage = error.message || "Something went wrong. Please try again.";
        if (!error.response && error.code !== "ERR_CANCELED") {
            // No answer at all (offline, server down, timed out): Axios's own "Network Error" means nothing here.
            errorMessage = "Can't reach Accretion. Check your connection and try again.";
        } else if (
            error.config?.url === "/auth/verification/confirm" &&
            error.response?.status === 422
        ) {
            errorMessage = "This verification link is invalid or expired. Request a new one.";
        } else if (typeof detail === "string" && detail.trim()) {
            errorMessage = detail;
        } else if (Array.isArray(detail)) {
            const messages = detail
                .map((item: unknown) =>
                    item &&
                    typeof item === "object" &&
                    "msg" in item &&
                    typeof item.msg === "string"
                        ? item.msg.trim()
                        : "",
                )
                .filter(Boolean);
            if (messages.length) errorMessage = messages.join(" ");
        }
        return Promise.reject(new Error(errorMessage));
    },
);

export default apiClient;
