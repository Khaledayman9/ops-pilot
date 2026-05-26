"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Zap, Save, Github, Cpu, CheckCircle, AlertCircle, Eye, EyeOff } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────

interface LLMConfig {
    provider: "openai" | "anthropic" | "google";
    api_key: string;
    base_url: string;
    model_name: string;
    temperature: number;
    max_retries: number;
}

interface GitHubConfig {
    github_token: string;
    github_repo: string;
}

type SaveStatus = "idle" | "saving" | "saved" | "error";

// ── Storage helpers (localStorage, safe) ──────────────────────────────────

function loadLLMConfig(): LLMConfig {
    if (typeof window === "undefined") return defaultLLM();
    try {
        const raw = localStorage.getItem("ops_pilot_llm_config");
        return raw ? { ...defaultLLM(), ...JSON.parse(raw) } : defaultLLM();
    } catch {
        return defaultLLM();
    }
}

function loadGitHubConfig(): GitHubConfig {
    if (typeof window === "undefined") return defaultGitHub();
    try {
        const raw = localStorage.getItem("ops_pilot_github_config");
        return raw ? { ...defaultGitHub(), ...JSON.parse(raw) } : defaultGitHub();
    } catch {
        return defaultGitHub();
    }
}

function defaultLLM(): LLMConfig {
    return {
        provider: "openai",
        api_key: "",
        base_url: "",
        model_name: "gpt-4o",
        temperature: 0,
        max_retries: 3,
    };
}

function defaultGitHub(): GitHubConfig {
    return { github_token: "", github_repo: "" };
}

// ── Field components ───────────────────────────────────────────────────────

function FieldLabel({ label, required, optional }: { label: string; required?: boolean; optional?: boolean }) {
    return (
        <label className="block text-xs font-mono text-chrome-dim mb-1.5">
            {label}
            {required && <span className="text-ember ml-1">*</span>}
            {optional && <span className="text-chrome-dim ml-1 opacity-50">(optional)</span>}
        </label>
    );
}

function Input({
    value,
    onChange,
    placeholder,
    type = "text",
    disabled,
}: {
    value: string | number;
    onChange: (v: string) => void;
    placeholder?: string;
    type?: string;
    disabled?: boolean;
}) {
    return (
        <input
            type={type}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            disabled={disabled}
            className="w-full bg-surface-2 border border-border-1 rounded px-3 py-2 text-xs font-mono text-chrome placeholder:text-chrome-dim/50 focus:outline-none focus:border-plasma transition-colors disabled:opacity-40"
        />
    );
}

function SecretInput({
    value,
    onChange,
    placeholder,
}: {
    value: string;
    onChange: (v: string) => void;
    placeholder?: string;
}) {
    const [show, setShow] = useState(false);
    return (
        <div className="relative">
            <input
                type={show ? "text" : "password"}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder={placeholder}
                className="w-full bg-surface-2 border border-border-1 rounded px-3 py-2 pr-9 text-xs font-mono text-chrome placeholder:text-chrome-dim/50 focus:outline-none focus:border-plasma transition-colors"
            />
            <button
                type="button"
                onClick={() => setShow((s) => !s)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-chrome-dim hover:text-plasma transition-colors"
            >
                {show ? <EyeOff size={13} /> : <Eye size={13} />}
            </button>
        </div>
    );
}

// ── Provider presets ───────────────────────────────────────────────────────

const PROVIDER_PRESETS: Record<LLMConfig["provider"], { defaultModel: string; modelOptions: string[] }> = {
    openai: {
        defaultModel: "gpt-4o",
        modelOptions: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    },
    anthropic: {
        defaultModel: "claude-3-5-sonnet-20241022",
        modelOptions: ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
    },
    google: {
        defaultModel: "gemini-1.5-pro",
        modelOptions: ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"],
    },
};

// ── Main page ──────────────────────────────────────────────────────────────

export default function SettingsPage() {
    const [llm, setLLM] = useState<LLMConfig>(defaultLLM());
    const [github, setGitHub] = useState<GitHubConfig>(defaultGitHub());
    const [llmStatus, setLLMStatus] = useState<SaveStatus>("idle");
    const [githubStatus, setGithubStatus] = useState<SaveStatus>("idle");
    const [mounted, setMounted] = useState(false);

    // Load from localStorage after mount (SSR-safe)
    useEffect(() => {
        setLLM(loadLLMConfig());
        setGitHub(loadGitHubConfig());
        setMounted(true);
    }, []);

    function updateLLM<K extends keyof LLMConfig>(key: K, value: LLMConfig[K]) {
        setLLM((prev) => ({ ...prev, [key]: value }));
    }

    function updateGitHub<K extends keyof GitHubConfig>(key: K, value: GitHubConfig[K]) {
        setGitHub((prev) => ({ ...prev, [key]: value }));
    }

    function handleProviderChange(provider: LLMConfig["provider"]) {
        const preset = PROVIDER_PRESETS[provider];
        setLLM((prev) => ({
            ...prev,
            provider,
            model_name: preset.defaultModel,
            base_url: "",
        }));
    }

    async function saveLLMConfig() {
        if (!llm.api_key.trim()) {
            setLLMStatus("error");
            setTimeout(() => setLLMStatus("idle"), 3000);
            return;
        }
        setLLMStatus("saving");
        try {
            localStorage.setItem("ops_pilot_llm_config", JSON.stringify(llm));
            // Persist to backend env via settings endpoint (best-effort)
            await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/settings/llm`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(llm),
            }).catch(() => null); // non-blocking
            setLLMStatus("saved");
            setTimeout(() => setLLMStatus("idle"), 3000);
        } catch {
            setLLMStatus("error");
            setTimeout(() => setLLMStatus("idle"), 3000);
        }
    }

    async function saveGitHubConfig() {
        setGithubStatus("saving");
        try {
            localStorage.setItem("ops_pilot_github_config", JSON.stringify(github));
            await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/settings/github`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(github),
            }).catch(() => null);
            setGithubStatus("saved");
            setTimeout(() => setGithubStatus("idle"), 3000);
        } catch {
            setGithubStatus("error");
            setTimeout(() => setGithubStatus("idle"), 3000);
        }
    }

    function SaveButton({ status, onClick }: { status: SaveStatus; onClick: () => void }) {
        return (
            <button
                onClick={onClick}
                disabled={status === "saving"}
                className="flex items-center gap-2 px-4 py-2 bg-plasma text-void font-mono font-semibold text-xs rounded hover:bg-plasma-dim transition-colors disabled:opacity-60"
            >
                {status === "saving" && <span className="animate-spin">⟳</span>}
                {status === "saved" && <CheckCircle size={13} />}
                {status === "error" && <AlertCircle size={13} />}
                {status === "idle" && <Save size={13} />}
                {status === "saving" ? "Saving…" : status === "saved" ? "Saved!" : status === "error" ? "Error" : "Save"}
            </button>
        );
    }

    if (!mounted) return null;

    const preset = PROVIDER_PRESETS[llm.provider];

    return (
        <div className="min-h-screen bg-void">
            {/* Navbar */}
            <nav className="fixed top-0 w-full z-50 border-b border-border-1 bg-void/80 backdrop-blur-md">
                <div className="max-w-4xl mx-auto px-6 h-14 flex items-center justify-between">
                    <Link href="/" className="flex items-center gap-2">
                        <Zap size={16} className="text-plasma" />
                        <span className="font-display font-semibold text-chrome tracking-tight text-sm">
                            ops<span className="text-plasma">-pilot</span>
                        </span>
                    </Link>
                    <div className="flex items-center gap-4 text-xs font-mono text-chrome-dim">
                        <Link href="/chat" className="hover:text-plasma transition-colors">Chat</Link>
                        <span className="text-plasma">Settings</span>
                    </div>
                </div>
            </nav>

            <div className="max-w-4xl mx-auto px-6 pt-24 pb-16">
                <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4 }}
                >
                    <h1 className="font-display text-2xl font-bold text-chrome mb-1">Settings</h1>
                    <p className="text-chrome-dim text-xs font-mono mb-10">
                        Configure your LLM provider and GitHub integration. Settings are saved locally and synced to the backend.
                    </p>

                    <div className="space-y-8">
                        {/* ── LLM Configuration ── */}
                        <section className="bg-surface-1 border border-border-1 rounded-xl p-6">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-3">
                                    <Cpu size={16} className="text-plasma" />
                                    <div>
                                        <h2 className="font-display font-semibold text-chrome text-sm">LLM Provider</h2>
                                        <p className="text-chrome-dim text-xs font-mono mt-0.5">Configure the AI model used by all agents</p>
                                    </div>
                                </div>
                                <SaveButton status={llmStatus} onClick={saveLLMConfig} />
                            </div>

                            {llmStatus === "error" && (
                                <div className="mb-4 px-3 py-2 bg-ember/10 border border-ember/30 rounded text-xs font-mono text-ember">
                                    API Key is required to save LLM configuration.
                                </div>
                            )}

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {/* Provider */}
                                <div>
                                    <FieldLabel label="Provider" required />
                                    <div className="flex gap-2">
                                        {(["openai", "anthropic", "google"] as const).map((p) => (
                                            <button
                                                key={p}
                                                onClick={() => handleProviderChange(p)}
                                                className={`flex-1 px-3 py-2 rounded border text-xs font-mono transition-colors ${llm.provider === p
                                                    ? "border-plasma text-plasma bg-plasma/10"
                                                    : "border-border-1 text-chrome-dim hover:border-border-2"
                                                    }`}
                                            >
                                                {p === "openai" ? "ChatGPT" : p === "anthropic" ? "Claude" : "Gemini"}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* API Key */}
                                <div>
                                    <FieldLabel label="API Key" required />
                                    <SecretInput
                                        value={llm.api_key}
                                        onChange={(v) => updateLLM("api_key", v)}
                                        placeholder={
                                            llm.provider === "openai"
                                                ? "sk-..."
                                                : llm.provider === "anthropic"
                                                    ? "sk-ant-..."
                                                    : "AIza..."
                                        }
                                    />
                                </div>

                                {/* Model */}
                                <div>
                                    <FieldLabel label="Model" optional />
                                    <div className="flex gap-2">
                                        <select
                                            value={llm.model_name}
                                            onChange={(e) => updateLLM("model_name", e.target.value)}
                                            className="flex-1 bg-surface-2 border border-border-1 rounded px-3 py-2 text-xs font-mono text-chrome focus:outline-none focus:border-plasma transition-colors"
                                        >
                                            {preset.modelOptions.map((m) => (
                                                <option key={m} value={m}>{m}</option>
                                            ))}
                                            <option value="custom">Custom…</option>
                                        </select>
                                    </div>
                                    {llm.model_name === "custom" && (
                                        <div className="mt-2">
                                            <Input
                                                value=""
                                                onChange={(v) => updateLLM("model_name", v)}
                                                placeholder="Enter model name"
                                            />
                                        </div>
                                    )}
                                </div>

                                {/* Base URL */}
                                <div>
                                    <FieldLabel label="Base URL" optional />
                                    <Input
                                        value={llm.base_url}
                                        onChange={(v) => updateLLM("base_url", v)}
                                        placeholder={
                                            llm.provider === "openai"
                                                ? "https://api.openai.com/v1 (default)"
                                                : "Leave blank for default"
                                        }
                                    />
                                </div>

                                {/* Temperature */}
                                <div>
                                    <FieldLabel label={`Temperature — ${llm.temperature}`} optional />
                                    <input
                                        type="range"
                                        min={0} max={2} step={0.1}
                                        value={llm.temperature}
                                        onChange={(e) => updateLLM("temperature", parseFloat(e.target.value))}
                                        className="w-full accent-plasma h-1.5 rounded"
                                    />
                                    <div className="flex justify-between text-xs font-mono text-chrome-dim mt-1">
                                        <span>0 (precise)</span>
                                        <span>2 (creative)</span>
                                    </div>
                                </div>

                                {/* Max Retries */}
                                <div>
                                    <FieldLabel label="Max Retries" optional />
                                    <Input
                                        type="number"
                                        value={llm.max_retries}
                                        onChange={(v) => updateLLM("max_retries", parseInt(v, 10) || 3)}
                                        placeholder="3"
                                    />
                                </div>
                            </div>
                        </section>

                        {/* ── GitHub Integration ── */}
                        <section className="bg-surface-1 border border-border-1 rounded-xl p-6">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-3">
                                    <Github size={16} className="text-plasma" />
                                    <div>
                                        <h2 className="font-display font-semibold text-chrome text-sm">GitHub Integration</h2>
                                        <p className="text-chrome-dim text-xs font-mono mt-0.5">
                                            Enable the repo-scouter agent to correlate incidents with commits and PRs
                                        </p>
                                    </div>
                                </div>
                                <SaveButton status={githubStatus} onClick={saveGitHubConfig} />
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {/* Token */}
                                <div>
                                    <FieldLabel label="Personal Access Token" optional />
                                    <SecretInput
                                        value={github.github_token}
                                        onChange={(v) => updateGitHub("github_token", v)}
                                        placeholder="ghp_..."
                                    />
                                    <p className="text-chrome-dim text-xs font-mono mt-1 opacity-60">
                                        Requires: repo, read:org, read:user scopes
                                    </p>
                                </div>

                                {/* Repo */}
                                <div>
                                    <FieldLabel label="Default Repository" optional />
                                    <Input
                                        value={github.github_repo}
                                        onChange={(v) => updateGitHub("github_repo", v)}
                                        placeholder="owner/repo-name"
                                    />
                                    <p className="text-chrome-dim text-xs font-mono mt-1 opacity-60">
                                        Used by repo-scouter for deployment correlation
                                    </p>
                                </div>
                            </div>

                            <div className="mt-4 p-3 bg-surface-2 border border-border-1 rounded text-xs font-mono text-chrome-dim">
                                <p className="text-plasma mb-1">How GitHub MCP works:</p>
                                <p>The backend uses <code>mcp-server-github</code> via the MCP stdio transport. The token set here is forwarded as <code>GITHUB_TOKEN</code> to the MCP server process. The repo-scouter agent uses it to fetch recent commits, PRs, and releases for deployment correlation.</p>
                            </div>
                        </section>
                    </div>
                </motion.div>
            </div>
        </div>
    );
}