/**
 * api-fetch.test.ts
 * Tests for register, login, logout, createChat, deleteChat, listChats
 * using a mocked global fetch — no real network calls.
 */
import Cookies from "js-cookie";
import {
  register,
  login,
  logout,
  createChat,
  listChats,
  deleteChat,
  getMe,
  ApiException,
} from "../lib/apis";

jest.mock("js-cookie", () => ({
  get: jest.fn(),
  set: jest.fn(),
  remove: jest.fn(),
}));

const mockCookies = Cookies as jest.Mocked<typeof Cookies>;

function mockFetch(status: number, body: unknown) {
  global.fetch = jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: String(status),
    json: jest.fn().mockResolvedValue(body),
  } as unknown as Response);
}

beforeEach(() => {
  jest.clearAllMocks();
  mockCookies.get.mockReturnValue(undefined as any);
});

// ---------------------------------------------------------------------------
// register
// ---------------------------------------------------------------------------
describe("register()", () => {
  it("returns UserPublic on success", async () => {
    const user = {
      id: "1",
      email: "a@b.com",
      username: "alice",
      is_active: true,
      is_verified: false,
    };
    mockFetch(201, user);
    const result = await register("a@b.com", "alice", "password1");
    expect(result.username).toBe("alice");
  });

  it("throws ApiException on 409 conflict", async () => {
    mockFetch(409, { detail: "Email already registered" });
    await expect(register("a@b.com", "alice", "password1")).rejects.toThrow(
      ApiException,
    );
  });

  it("throws ZodError for invalid email before fetch", async () => {
    global.fetch = jest.fn();
    await expect(register("not-email", "alice", "password1")).rejects.toThrow();
    expect(global.fetch).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// login
// ---------------------------------------------------------------------------
describe("login()", () => {
  it("stores tokens and returns TokenResponse", async () => {
    mockFetch(200, {
      access_token: "acc",
      refresh_token: "ref",
      token_type: "bearer",
    });
    const result = await login("a@b.com", "password1");
    expect(result.access_token).toBe("acc");
    expect(mockCookies.set).toHaveBeenCalledWith(
      "access_token",
      "acc",
      expect.anything(),
    );
    expect(mockCookies.set).toHaveBeenCalledWith(
      "refresh_token",
      "ref",
      expect.anything(),
    );
  });

  it("throws ApiException on 401 invalid credentials", async () => {
    mockFetch(401, { detail: "Invalid credentials" });
    await expect(login("a@b.com", "wrongpass")).rejects.toBeInstanceOf(
      ApiException,
    );
  });

  it("throws ZodError for empty password before fetch", async () => {
    global.fetch = jest.fn();
    await expect(login("a@b.com", "")).rejects.toThrow();
    expect(global.fetch).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// logout
// ---------------------------------------------------------------------------
describe("logout()", () => {
  it("removes both cookies without hitting the network", async () => {
    global.fetch = jest.fn();
    await logout();
    expect(mockCookies.remove).toHaveBeenCalledWith("access_token");
    expect(mockCookies.remove).toHaveBeenCalledWith("refresh_token");
    expect(global.fetch).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// getMe
// ---------------------------------------------------------------------------
describe("getMe()", () => {
  it("sends Authorization header when token exists", async () => {
    mockCookies.get.mockReturnValue("my-token" as any);
    const user = {
      id: "1",
      email: "a@b.com",
      username: "alice",
      is_active: true,
      is_verified: true,
    };
    mockFetch(200, user);
    await getMe();
    const fetchCall = (global.fetch as jest.Mock).mock.calls[0];
    expect(fetchCall[1].headers.Authorization).toBe("Bearer my-token");
  });

  it("throws ApiException on 401", async () => {
    mockFetch(401, { detail: "Unauthorized" });
    await expect(getMe()).rejects.toBeInstanceOf(ApiException);
  });
});

// ---------------------------------------------------------------------------
// createChat
// ---------------------------------------------------------------------------
describe("createChat()", () => {
  it("returns a ChatSession", async () => {
    mockFetch(201, {
      id: "session-1",
      title: "Incident #1",
      created_at: "2025-01-01T00:00:00Z",
    });
    const session = await createChat("Incident #1");
    expect(session.id).toBe("session-1");
  });

  it("creates chat without a title", async () => {
    mockFetch(201, { id: "session-2", created_at: "2025-01-01T00:00:00Z" });
    const session = await createChat();
    expect(session.id).toBe("session-2");
  });
});

// ---------------------------------------------------------------------------
// listChats
// ---------------------------------------------------------------------------
describe("listChats()", () => {
  it("returns array of sessions on success", async () => {
    mockFetch(200, [{ id: "s1", created_at: "2025-01-01" }]);
    const sessions = await listChats();
    expect(sessions).toHaveLength(1);
  });

  it("returns empty array on non-ok response instead of throwing", async () => {
    mockFetch(401, { detail: "Unauthorized" });
    const sessions = await listChats();
    expect(sessions).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// deleteChat
// ---------------------------------------------------------------------------
describe("deleteChat()", () => {
  it("calls DELETE on the correct endpoint", async () => {
    mockFetch(204, null);
    await deleteChat("session-abc");
    const fetchCall = (global.fetch as jest.Mock).mock.calls[0];
    expect(fetchCall[0]).toContain("/api/v1/chat/session-abc");
    expect(fetchCall[1].method).toBe("DELETE");
  });
});
