"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Github, KeyRound, LogIn, LogOut, Settings, User } from "lucide-react";
import { clearTokens, getAccessToken, getMe, UserPublic } from "../lib/apis";
import NavBar from "../components/NavBar";
import PageFooter from "../components/PageFooter";

type LLMConfig = {
  provider: string;
  api_key: string;
  base_url: string;
  model_name: string;
  temperature: number;
  max_retries: number;
};

type GitHubConfig = {
  github_token: string;
  github_repo: string;
};

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? { ...fallback, ...JSON.parse(raw) } : fallback;
  } catch {
    return fallback;
  }
}

function mask(value: string) {
  if (!value) return "Not configured";
  if (value.length <= 8) return "Configured";
  return `${value.slice(0, 4)}...${value.slice(-4)}`;
}

export default function ProfilePage() {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [llm, setLlm] = useState<LLMConfig>({
    provider: "openai",
    api_key: "",
    base_url: "",
    model_name: "gpt-4o",
    temperature: 0,
    max_retries: 3,
  });
  const [github, setGithub] = useState<GitHubConfig>({
    github_token: "",
    github_repo: "",
  });

  useEffect(() => {
    setLlm(readJson("ops_pilot_llm_config", llm));
    setGithub(readJson("ops_pilot_github_config", github));

    if (!getAccessToken()) {
      setLoading(false);
      return;
    }

    getMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function logout() {
    clearTokens();
    setUser(null);
  }

  return (
    <div className="min-h-screen bg-void grid-bg text-chrome flex flex-col">
      <NavBar variant="inner" />

      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-12 pt-24">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-lg border border-plasma/40 bg-plasma/10 flex items-center justify-center">
              <User size={22} className="text-plasma" />
            </div>
            <div>
              <h1 className="font-display text-3xl font-bold">Profile</h1>
              <p className="text-sm font-mono text-chrome-dim">
                Account and local Ops-Pilot settings
              </p>
            </div>
          </div>

          {!loading && !user && (
            <section className="bg-surface-1 border border-border-1 rounded-xl p-6 mb-6">
              <h2 className="font-display font-semibold mb-2">
                You are not signed in
              </h2>
              <p className="text-sm font-mono text-chrome-dim mb-5">
                Sign in or create an account to sync chat sessions with the
                backend.
              </p>
              <div className="flex flex-wrap gap-3">
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 px-5 py-3 bg-plasma text-void rounded-lg font-display font-bold text-sm"
                >
                  <LogIn size={15} />
                  Login
                </Link>
              </div>
            </section>
          )}

          {user && (
            <section className="bg-surface-1 border border-border-1 rounded-xl p-6 mb-6">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="font-display font-semibold mb-1">
                    {user.username}
                  </h2>
                  <p className="text-sm font-mono text-chrome-dim">
                    {user.email}
                  </p>
                  <p className="text-xs font-mono text-chrome-dim mt-2">
                    Active: {user.is_active ? "yes" : "no"} | Verified:{" "}
                    {user.is_verified ? "yes" : "no"}
                  </p>
                </div>
                <button
                  onClick={logout}
                  className="inline-flex items-center gap-2 px-4 py-2 border border-border-2 rounded-lg text-xs font-mono text-chrome-dim hover:border-ember hover:text-ember"
                >
                  <LogOut size={14} />
                  Logout
                </button>
              </div>
            </section>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <section className="bg-surface-1 border border-border-1 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-5">
                <KeyRound size={17} className="text-plasma" />
                <h2 className="font-display font-semibold">LLM Settings</h2>
              </div>
              <div className="space-y-3 text-sm font-mono">
                <p>
                  <span className="text-chrome-dim">Provider:</span>{" "}
                  {llm.provider}
                </p>
                <p>
                  <span className="text-chrome-dim">Model:</span>{" "}
                  {llm.model_name}
                </p>
                <p>
                  <span className="text-chrome-dim">API key:</span>{" "}
                  {mask(llm.api_key)}
                </p>
                <p>
                  <span className="text-chrome-dim">Base URL:</span>{" "}
                  {llm.base_url || "Default"}
                </p>
                <p>
                  <span className="text-chrome-dim">Temperature:</span>{" "}
                  {llm.temperature}
                </p>
                <p>
                  <span className="text-chrome-dim">Max retries:</span>{" "}
                  {llm.max_retries}
                </p>
              </div>
            </section>

            <section className="bg-surface-1 border border-border-1 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-5">
                <Github size={17} className="text-plasma" />
                <h2 className="font-display font-semibold">GitHub Settings</h2>
              </div>
              <div className="space-y-3 text-sm font-mono">
                <p>
                  <span className="text-chrome-dim">Token:</span>{" "}
                  {mask(github.github_token)}
                </p>
                <p>
                  <span className="text-chrome-dim">Default repo:</span>{" "}
                  {github.github_repo || "Not configured"}
                </p>
              </div>
            </section>
          </div>

          <Link
            href="/settings"
            className="mt-6 inline-flex items-center gap-2 px-5 py-3 border border-border-2 rounded-lg text-sm font-mono text-chrome-dim hover:border-plasma hover:text-plasma"
          >
            <Settings size={15} />
            Edit settings
          </Link>
        </motion.div>
      </main>
      <PageFooter />
    </div>
  );
}
