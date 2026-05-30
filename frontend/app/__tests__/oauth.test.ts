/**
 * oauth.test.ts
 * Tests for OAuth flows (startOAuth, finishOAuth) and refreshTokens.
 */
import Cookies from "js-cookie";
import {
  startOAuth,
  finishOAuth,
  refreshTokens,
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
// startOAuth
// ---------------------------------------------------------------------------
describe("startOAuth()", () => {
  it("returns the redirect URL from the backend", async () => {
    mockFetch(200, { url: "https://accounts.google.com/oauth?..." });
    const url = await startOAuth(
      "google",
      "https://app.example.com/auth/callback?provider=google",
    );
    expect(url).toBe("https://accounts.google.com/oauth?...");
  });

  it("calls the correct endpoint for github provider", async () => {
    mockFetch(200, { url: "https://github.com/login/oauth/authorize?..." });
    await startOAuth(
      "github",
      "https://app.example.com/auth/callback?provider=github",
    );
    const fetchCall = (global.fetch as jest.Mock).mock.calls[0];
    expect(fetchCall[0]).toContain("/api/v1/auth/oauth/github/start");
  });

  it("throws ApiException on backend error", async () => {
    mockFetch(500, { detail: "OAuth provider unavailable" });
    await expect(
      startOAuth("google", "http://localhost/callback"),
    ).rejects.toBeInstanceOf(ApiException);
  });
});

// ---------------------------------------------------------------------------
// finishOAuth
// ---------------------------------------------------------------------------
describe("finishOAuth()", () => {
  it("stores tokens and returns TokenResponse", async () => {
    mockFetch(200, {
      access_token: "acc",
      refresh_token: "ref",
      token_type: "bearer",
    });
    const result = await finishOAuth(
      "google",
      "auth-code-123",
      "http://localhost/callback",
    );
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

  it("sends the code and redirect_uri in the request body", async () => {
    mockFetch(200, {
      access_token: "a",
      refresh_token: "r",
      token_type: "bearer",
    });
    await finishOAuth("github", "code-xyz", "http://localhost/cb");
    const fetchCall = (global.fetch as jest.Mock).mock.calls[0];
    const body = JSON.parse(fetchCall[1].body);
    expect(body.code).toBe("code-xyz");
    expect(body.redirect_uri).toBe("http://localhost/cb");
  });

  it("throws ApiException on invalid code", async () => {
    mockFetch(400, { detail: "Invalid authorization code" });
    await expect(
      finishOAuth("google", "bad-code", "http://localhost/cb"),
    ).rejects.toBeInstanceOf(ApiException);
  });
});

// ---------------------------------------------------------------------------
// refreshTokens
// ---------------------------------------------------------------------------
describe("refreshTokens()", () => {
  it("throws ApiException immediately when no refresh token in cookie", async () => {
    global.fetch = jest.fn();
    mockCookies.get.mockReturnValue(undefined as any);
    await expect(refreshTokens()).rejects.toBeInstanceOf(ApiException);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("exchanges refresh token and stores new tokens", async () => {
    mockCookies.get.mockReturnValue("old-refresh-token" as any);
    mockFetch(200, {
      access_token: "new-acc",
      refresh_token: "new-ref",
      token_type: "bearer",
    });
    const result = await refreshTokens();
    expect(result.access_token).toBe("new-acc");
    expect(mockCookies.set).toHaveBeenCalledWith(
      "access_token",
      "new-acc",
      expect.anything(),
    );
  });

  it("throws ApiException when refresh token is expired", async () => {
    mockCookies.get.mockReturnValue("expired-token" as any);
    mockFetch(401, { detail: "Refresh token expired" });
    await expect(refreshTokens()).rejects.toBeInstanceOf(ApiException);
  });
});
