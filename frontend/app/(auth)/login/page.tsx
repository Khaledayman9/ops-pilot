"use client";

import { FormEvent, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, Github, Loader2, Lock, Mail, Zap } from "lucide-react";
import { ApiException, login, startOAuth } from "../../lib/apis";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(email, password);
      router.push("/chat");
    } catch (err) {
      if (err instanceof ApiException)
        setError(err.body.detail ?? "Login failed");
      else if (err instanceof Error) setError(err.message);
      else setError("Unexpected error");
    } finally {
      setLoading(false);
    }
  }

  async function handleOAuth(provider: "google" | "github") {
    setError("");
    setLoading(true);

    try {
      const redirectUri = `${window.location.origin}/auth/callback?provider=${provider}`;
      const url = await startOAuth(provider, redirectUri);
      window.location.href = url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "OAuth sign in failed");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-void grid-bg flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md"
      >
        <Link href="/" className="flex items-center justify-center gap-2 mb-10">
          <Zap size={22} className="text-plasma" />
          <span className="font-display font-bold text-xl text-chrome">
            ops<span className="text-plasma">-pilot</span>
          </span>
        </Link>

        <div className="bg-surface-1 border border-border-1 rounded-xl p-8">
          <h1 className="font-display font-bold text-2xl text-chrome mb-1">
            Sign in
          </h1>
          <p className="text-chrome-dim text-sm font-mono mb-8">
            Access the AI SRE control plane
          </p>

          {error && (
            <div className="flex items-start gap-2 px-4 py-3 bg-ember/10 border border-ember/30 rounded-lg mb-6 text-sm text-ember font-mono">
              <AlertCircle size={14} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
          <div className="grid grid-cols-1 gap-3 mb-6">
            <button
              type="button"
              onClick={() => handleOAuth("google")}
              className="w-full flex items-center justify-center gap-2 py-3 border border-border-1 rounded-lg text-sm font-mono text-chrome-dim hover:border-plasma hover:text-plasma transition-colors"
            >
              <span className="w-4 h-4 rounded-full bg-chrome text-void text-[10px] font-display font-bold flex items-center justify-center">
                G
              </span>
              Sign in with Google
            </button>
            <button
              type="button"
              onClick={() => handleOAuth("github")}
              className="w-full flex items-center justify-center gap-2 py-3 border border-border-1 rounded-lg text-sm font-mono text-chrome-dim hover:border-plasma hover:text-plasma transition-colors"
            >
              <Github size={15} />
              Sign in with GitHub
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-mono text-chrome-dim mb-1.5">
                Email
              </label>
              <div className="relative">
                <Mail
                  size={14}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-chrome-dim"
                />
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  placeholder="you@company.com"
                  className="w-full bg-surface-2 border border-border-1 rounded-lg pl-9 pr-4 py-3 text-sm font-mono text-chrome focus:outline-none focus:border-plasma"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-mono text-chrome-dim mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock
                  size={14}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-chrome-dim"
                />
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  placeholder="Password"
                  className="w-full bg-surface-2 border border-border-1 rounded-lg pl-9 pr-4 py-3 text-sm font-mono text-chrome focus:outline-none focus:border-plasma"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 bg-plasma text-void font-display font-bold rounded-lg hover:bg-plasma-dim transition-colors disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </form>

          <p className="text-center text-xs font-mono text-chrome-dim mt-6">
            Do not have an account?{" "}
            <Link href="/register" className="text-plasma hover:underline">
              Register
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
