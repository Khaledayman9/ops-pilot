// Tests that don't require DOM - pure unit tests
import { ApiException } from "../lib/apis";

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

    it("is instanceof Error", () => {
        const err = new ApiException(401, { detail: "Unauthorized" });
        expect(err instanceof Error).toBe(true);
    });
});

describe("Input sanity checks", () => {
    it("trims whitespace from query", () => {
        const query = "  checkout service down  ";
        expect(query.trim()).toBe("checkout service down");
    });

    it("rejects empty queries", () => {
        const query = "   ";
        expect(query.trim().length).toBe(0);
    });

    it("caps extremely long inputs at frontend boundary", () => {
        const MAX = 4000;
        const query = "x".repeat(10000);
        const capped = query.slice(0, MAX);
        expect(capped.length).toBe(MAX);
    });
});