/**
 * API client — all HTTP + SSE calls to the backend.
 * Auth tokens are read from cookies (set by the auth module).
 */
import Cookies from "js-cookie";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Token helpers ──────────────────────────────────────────────────────────

export function getAccessToken(): string | undefined {
    return Cookies.get("access_token");
}

export function setTokens(access: string, refresh: string) {
    Cookies.set("access_token", access, { sameSite: "strict", secure: false });
    Cookies.set("refresh_token", refresh, { sameSite: "strict", secure: false });
}

export function clearTokens() {
    Cookies.remove("access_token");
    Cookies.remove("refresh_token");
}

// ── Auth ───────────────────────────────────────────────────────────────────

export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export interface UserPublic {
    id: string;
    email: string;
    username: string;
    is_active: boolean;
    is_verified: boolean;
}

export async function register(
    email: string,
    username: string,
    password: string
): Promise<UserPublic> {
    const res = await fetch(`${API}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, username, password }),
    });
    if (!res.ok) throw new Error((await res.json()).detail ?? "Registration failed");
    return res.json();
}

export async function login(email: string, password: string): Promise<TokenResponse> {
    const res = await fetch(`${API}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
    });
    if (!res.ok) throw new Error((await res.json()).detail ?? "Login failed");
    const tokens: TokenResponse = await res.json();
    setTokens(tokens.access_token, tokens.refresh_token);
    return tokens;
}

export async function getMe(): Promise<UserPublic> {
    const token = getAccessToken();
    const res = await fetch(`${API}/api/v1/auth/me`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error("Not authenticated");
    return res.json();
}

// ── Auth header helper ──────────────────────────────────────────────────────

function authHeaders(): Record<string, string> {
    const token = getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── Chat ───────────────────────────────────────────────────────────────────

export interface ChatSession {
    id: string;
    title?: string;
    created_at: string;
}

export async function createChat(title?: string): Promise<ChatSession> {
    const res = await fetch(`${API}/api/v1/chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ title }),
    });
    if (!res.ok) throw new Error("Failed to create chat");
    return res.json();
}

export async function listChats(): Promise<ChatSession[]> {
    const res = await fetch(`${API}/api/v1/chat/`, {
        headers: authHeaders(),
    });
    if (!res.ok) return [];
    return res.json();
}

// ── Streaming ──────────────────────────────────────────────────────────────

export interface StreamEvent {
    event: string;
    agent?: string;
    step?: string;
    data?: Record<string, unknown> | null;
    status?: string;
}

export function streamIncident(
    query: string,
    sessionId: string | null,
    onEvent: (e: StreamEvent) => void,
    onDone: (sessionId: string) => void,
    onError: (err: Error) => void
): () => void {
    const params = new URLSearchParams({ query });
    if (sessionId) params.set("session_id", sessionId);

    const token = getAccessToken();
    if (token) params.set("token", token); // SSE can't set headers; pass as param

    const url = `${API}/api/v1/stream/incident?${params.toString()}`;
    const es = new EventSource(url);

    const types = ["step", "graph", "reasoning", "result", "error", "session"];
    types.forEach((t) => {
        es.addEventListener(t, (e: MessageEvent) => {
            try {
                const parsed = JSON.parse(e.data);
                onEvent({ ...parsed, event: t } as StreamEvent);
            } catch {
                /* ignore */
            }
        });
    });

    es.addEventListener("done", (e: MessageEvent) => {
        try {
            onDone(JSON.parse(e.data).session_id);
        } catch {
            onDone("");
        }
        es.close();
    });

    es.onerror = () => {
        onError(new Error("SSE connection failed"));
        es.close();
    };

    return () => es.close();
}