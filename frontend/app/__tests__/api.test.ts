import { ApiException, handleResponse } from "../lib/api";

// We need to expose handleResponse for testing — add a named export in api.ts
// or test indirectly via login/register mocks.

describe("ApiException", () => {
    it("carries status and body", () => {
        const err = new ApiException(404, { detail: "Not found" });
        expect(err.status).toBe(404);
        expect(err.message).toBe("Not found");
        expect(err.body.detail).toBe("Not found");
        expect(err.name).toBe("ApiException");
    });

    it("propagates trace_id from backend", () => {
        const err = new ApiException(500, {
            detail: "Internal server error",
            trace_id: "abc-123",
            path: "/api/v1/incident/analyze",
        });
        expect(err.body.trace_id).toBe("abc-123");
        expect(err.body.path).toBe("/api/v1/incident/analyze");
    });
});

describe("token helpers", () => {
    it("setTokens / getAccessToken roundtrip", async () => {
        const { setTokens, getAccessToken, clearTokens } = await import("../lib/api");
        setTokens("my-access", "my-refresh");
        expect(getAccessToken()).toBe("my-access");
        clearTokens();
        expect(getAccessToken()).toBeUndefined();
    });
});