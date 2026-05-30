/**
 * validation.test.ts
 * Tests for Zod schemas used in register and login (via apis.ts logic)
 * We test the validation rules directly since the schemas enforce them before any fetch.
 */
import { z } from "zod";

// Mirror the schemas from apis.ts so we can test them in isolation
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

// ---------------------------------------------------------------------------
// RegisterSchema
// ---------------------------------------------------------------------------
describe("RegisterSchema", () => {
  const valid = { email: "user@example.com", username: "user_01", password: "secret99" };

  it("accepts valid registration data", () => {
    expect(() => RegisterSchema.parse(valid)).not.toThrow();
  });

  it("rejects invalid email", () => {
    expect(() => RegisterSchema.parse({ ...valid, email: "not-an-email" })).toThrow();
  });

  it("rejects username shorter than 3 characters", () => {
    expect(() => RegisterSchema.parse({ ...valid, username: "ab" })).toThrow();
  });

  it("rejects username longer than 64 characters", () => {
    expect(() => RegisterSchema.parse({ ...valid, username: "a".repeat(65) })).toThrow();
  });

  it("rejects username with special characters", () => {
    expect(() => RegisterSchema.parse({ ...valid, username: "user name!" })).toThrow();
  });

  it("accepts username with hyphens and underscores", () => {
    expect(() => RegisterSchema.parse({ ...valid, username: "user-name_01" })).not.toThrow();
  });

  it("rejects password shorter than 8 characters", () => {
    expect(() => RegisterSchema.parse({ ...valid, password: "short" })).toThrow();
  });

  it("accepts password exactly 8 characters", () => {
    expect(() => RegisterSchema.parse({ ...valid, password: "exactly8" })).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// LoginSchema
// ---------------------------------------------------------------------------
describe("LoginSchema", () => {
  const valid = { email: "user@example.com", password: "anypassword" };

  it("accepts valid login data", () => {
    expect(() => LoginSchema.parse(valid)).not.toThrow();
  });

  it("rejects invalid email format", () => {
    expect(() => LoginSchema.parse({ ...valid, email: "bad" })).toThrow();
  });

  it("rejects empty password", () => {
    expect(() => LoginSchema.parse({ ...valid, password: "" })).toThrow();
  });

  it("accepts a single character password", () => {
    // LoginSchema only requires min(1) — server does further validation
    expect(() => LoginSchema.parse({ ...valid, password: "x" })).not.toThrow();
  });
});
