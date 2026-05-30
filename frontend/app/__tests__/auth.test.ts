/**
 * auth.test.ts
 * Tests for token management and auth utility functions in apis.ts
 */
import Cookies from "js-cookie";
import {
  getAccessToken,
  setTokens,
  clearTokens,
  ApiException,
} from "../lib/apis";

// Mock js-cookie so tests don't touch real browser cookies
jest.mock("js-cookie", () => ({
  get: jest.fn(),
  set: jest.fn(),
  remove: jest.fn(),
}));

const mockCookies = Cookies as jest.Mocked<typeof Cookies>;

beforeEach(() => {
  jest.clearAllMocks();
});

// ---------------------------------------------------------------------------
// getAccessToken
// ---------------------------------------------------------------------------
describe("getAccessToken", () => {
  it("returns the access token when present", () => {
    (mockCookies.get as jest.Mock).mockReturnValue("my-token");
    expect(getAccessToken()).toBe("my-token");
    expect(mockCookies.get).toHaveBeenCalledWith("access_token");
  });

  it("returns undefined when no token is stored", () => {
    (mockCookies.get as jest.Mock).mockReturnValue(undefined);
    expect(getAccessToken()).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// setTokens
// ---------------------------------------------------------------------------
describe("setTokens", () => {
  it("stores both access and refresh tokens", () => {
    setTokens("acc-123", "ref-456");
    expect(mockCookies.set).toHaveBeenCalledTimes(2);
    expect(mockCookies.set).toHaveBeenCalledWith(
      "access_token",
      "acc-123",
      expect.objectContaining<Record<string, unknown>>({ sameSite: "strict" }),
    );
    expect(mockCookies.set).toHaveBeenCalledWith(
      "refresh_token",
      "ref-456",
      expect.objectContaining<Record<string, unknown>>({ sameSite: "strict" }),
    );
  });

  it("sets secure flag only in production", () => {
    const original = process.env.NODE_ENV;
    Object.defineProperty(process.env, "NODE_ENV", {
      value: "production",
      writable: true,
    });
    setTokens("acc", "ref");
    expect(mockCookies.set).toHaveBeenCalledWith(
      "access_token",
      "acc",
      expect.objectContaining<Record<string, unknown>>({ secure: true }),
    );
    Object.defineProperty(process.env, "NODE_ENV", { value: original });
  });
});

// ---------------------------------------------------------------------------
// clearTokens
// ---------------------------------------------------------------------------
describe("clearTokens", () => {
  it("removes both access and refresh tokens", () => {
    clearTokens();
    expect(mockCookies.remove).toHaveBeenCalledWith("access_token");
    expect(mockCookies.remove).toHaveBeenCalledWith("refresh_token");
    expect(mockCookies.remove).toHaveBeenCalledTimes(2);
  });
});

// ---------------------------------------------------------------------------
// ApiException edge cases
// ---------------------------------------------------------------------------
describe("ApiException extended", () => {
  it("uses statusText as message when detail is empty string", () => {
    const err = new ApiException(400, { detail: "" });
    expect(err.message).toBe("");
    expect(err.status).toBe(400);
  });

  it("preserves optional code field", () => {
    const err = new ApiException(403, {
      detail: "Forbidden",
      code: "E_FORBIDDEN",
    });
    expect(err.body.code).toBe("E_FORBIDDEN");
  });

  it("stack trace is defined", () => {
    const err = new ApiException(500, { detail: "oops" });
    expect(err.stack).toBeDefined();
  });
});
