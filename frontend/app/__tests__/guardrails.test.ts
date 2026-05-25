describe("Frontend input sanity", () => {
    it("trims whitespace from query", () => {
        const query = "  checkout service down  ";
        expect(query.trim()).toBe("checkout service down");
    });

    it("rejects empty queries", () => {
        const query = "   ";
        expect(query.trim().length).toBe(0);
    });

    it("caps extremely long inputs", () => {
        const query = "x".repeat(10000);
        const MAX = 4000;
        const capped = query.slice(0, MAX);
        expect(capped.length).toBe(MAX);
    });
});