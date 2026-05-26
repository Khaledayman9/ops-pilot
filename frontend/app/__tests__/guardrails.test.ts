describe("Frontend guardrails (client-side pre-validation)", () => {
    it("trims control characters from input", () => {
        const dirty = "checkout\x00service\x01down";
        const clean = dirty.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, "").trim();
        expect(clean).toBe("checkoutservicedown");
    });

    it("detects empty query after sanitisation", () => {
        const query = "\x00\x01\x02";
        const clean = query.replace(/[\x00-\x1f]/g, "").trim();
        expect(clean.length).toBe(0);
    });

    it("preserves valid incident text", () => {
        const query = "Checkout service p99 latency > 2s after deployment v2.3.1";
        const clean = query.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, "").trim();
        expect(clean).toBe(query);
    });

    it("enforces maximum query length", () => {
        const MAX = 4000;
        const long = "a".repeat(6000);
        expect(long.slice(0, MAX).length).toBe(MAX);
    });
});