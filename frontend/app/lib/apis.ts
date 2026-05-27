import Cookies from "js-cookie";
import { z } from "zod";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function getAccessToken(): string | undefined {
  return Cookies.get("access_token");
}

export function setTokens(access: string, refresh: string): void {
  const opts = {
    sameSite: "strict" as const,
    secure: process.env.NODE_ENV === "production",
  };
  Cookies.set("access_token", access, opts);
  Cookies.set("refresh_token", refresh, opts);
}

export function clearTokens(): void {
  Cookies.remove("access_token");
  Cookies.remove("refresh_token");
}

function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface ApiError {
  detail: string;
  trace_id?: string;
  path?: string;
  code?: string;
}

export class ApiException extends Error {
  status: number;
  body: ApiError;

  constructor(status: number, body: ApiError) {
    super(body.detail);
    this.status = status;
    this.body = body;
    this.name = "ApiException";
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.ok) return res.json() as Promise<T>;

  let body: ApiError;
  try {
    body = await res.json();
  } catch {
    body = { detail: res.statusText };
  }

  throw new ApiException(res.status, body);
}

const RegisterSchema = z.object({
  email: z.string().email(),
  username: z
    .string()
    .min(3)
    .max(64)
    .regex(/^[a-zA-Z0-9_-]+$/),
  password: z.string().min(8),
});

const LoginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

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

export interface ChatSession {
  id: string;
  title?: string;
  created_at: string;
}

export interface StreamEvent {
  event: string;
  agent?: string;
  step?: string;
  data?: Record<string, unknown> | string | null;
  status?: string;
}

export interface ConvertedDocument {
  filename: string;
  markdown: string;
  chunks: number;
  characters: number;
  mime_type?: string;
}

export interface DocumentConversionResponse {
  documents: ConvertedDocument[];
  combined_markdown: string;
}

export async function register(
  email: string,
  username: string,
  password: string,
): Promise<UserPublic> {
  const body = RegisterSchema.parse({ email, username, password });
  const res = await fetch(`${API}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse<UserPublic>(res);
}

export async function login(
  email: string,
  password: string,
): Promise<TokenResponse> {
  const body = LoginSchema.parse({ email, password });
  const res = await fetch(`${API}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const tokens = await handleResponse<TokenResponse>(res);
  setTokens(tokens.access_token, tokens.refresh_token);
  return tokens;
}

export async function refreshTokens(): Promise<TokenResponse> {
  const refreshToken = Cookies.get("refresh_token");
  if (!refreshToken)
    throw new ApiException(401, { detail: "No refresh token" });

  const res = await fetch(`${API}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  const tokens = await handleResponse<TokenResponse>(res);
  setTokens(tokens.access_token, tokens.refresh_token);
  return tokens;
}

export async function getMe(): Promise<UserPublic> {
  const res = await fetch(`${API}/api/v1/auth/me`, {
    headers: { "Content-Type": "application/json", ...authHeaders() },
  });
  return handleResponse<UserPublic>(res);
}

export async function logout(): Promise<void> {
  clearTokens();
}

export async function createChat(title?: string): Promise<ChatSession> {
  const res = await fetch(`${API}/api/v1/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ title }),
  });
  return handleResponse<ChatSession>(res);
}

export async function listChats(): Promise<ChatSession[]> {
  const res = await fetch(`${API}/api/v1/chat/`, { headers: authHeaders() });
  if (!res.ok) return [];
  return res.json();
}

export async function deleteChat(sessionId: string): Promise<void> {
  await fetch(`${API}/api/v1/chat/${sessionId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
}

export async function uploadDocuments(
  files: File[],
): Promise<DocumentConversionResponse> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));

  const res = await fetch(`${API}/api/v1/documents/convert`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });

  return handleResponse<DocumentConversionResponse>(res);
}

export function streamIncident(
  query: string,
  sessionId: string | null,
  documentContext: string,
  enabledAgents: string[],
  onEvent: (e: StreamEvent) => void,
  onDone: (sessionId: string) => void,
  onError: (err: Error | ApiException) => void,
): () => void {
  const params = new URLSearchParams({ query });
  if (sessionId) params.set("session_id", sessionId);
  if (documentContext.trim()) params.set("document_context", documentContext);
  if (enabledAgents.length)
    params.set("enabled_agents", enabledAgents.join(","));

  const token = getAccessToken();
  if (token) params.set("token", token);

  const url = `${API}/api/v1/stream/incident?${params.toString()}`;
  const es = new EventSource(url);

  const types = ["session", "step", "graph", "reasoning", "result"];
  types.forEach((type) => {
    es.addEventListener(type, (e: MessageEvent) => {
      try {
        const parsed = JSON.parse(e.data);
        onEvent({ ...parsed, event: type } as StreamEvent);
      } catch {
        onEvent({ event: type, data: e.data });
      }
    });
  });

  es.addEventListener("error_event", (e: MessageEvent) => {
    try {
      const parsed = JSON.parse(e.data) as ApiError;
      onError(new ApiException(422, parsed));
    } catch {
      onError(new Error("Unknown stream error"));
    }
    es.close();
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
    onError(
      new ApiException(503, {
        detail: "SSE connection failed. Is the backend running?",
      }),
    );
    es.close();
  };

  return () => es.close();
}

export async function startOAuth(
  provider: "google" | "github",
  redirectUri: string,
): Promise<string> {
  const params = new URLSearchParams({ redirect_uri: redirectUri });
  const res = await fetch(
    `${API}/api/v1/auth/oauth/${provider}/start?${params.toString()}`,
  );
  const body = await handleResponse<{ url: string }>(res);
  return body.url;
}

export async function finishOAuth(
  provider: "google" | "github",
  code: string,
  redirectUri: string,
): Promise<TokenResponse> {
  const res = await fetch(`${API}/api/v1/auth/oauth/${provider}/callback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, redirect_uri: redirectUri }),
  });
  const tokens = await handleResponse<TokenResponse>(res);
  setTokens(tokens.access_token, tokens.refresh_token);
  return tokens;
}
