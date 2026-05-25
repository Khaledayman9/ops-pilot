"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Zap, Mail, Lock, User, AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { register, ApiException } from "@/app/lib/api";

export default function RegisterPage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [success, setSuccess] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleSubmit = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        if (password.length < 8) { setError("Password must be at least 8 characters."); return; }
        setLoading(true);
        try {
            await register(email, username, password);
            setSuccess(true);
            setTimeout(() => router.push("/login"), 1800);
        } catch (err) {
            if (err instanceof ApiException) {
                setError(err.body.detail ?? "Registration failed");
            } else if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("Unexpected error");
            }
        } finally {
            setLoading(false);
        }
    }, [email, username, password, router]);

    return (
        <div className="min-h-screen bg-void grid-bg flex items-center justify-center px-4">
            <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[500px] h-[500px] rounded-full pointer-events-none"
                style={{ background: "radial-gradient(circle, rgba(0,255,136,0.05) 0%, transparent 70%)" }} />

            <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }} className="relative z-10 w-full max-w-md">

                <div className="flex items-center justify-center gap-2 mb-10">
                    <Zap size={22} className="text-plasma" />
                    <span className="font-display font-bold text-xl text-chrome">
                        ops<span className="text-plasma">-pilot</span>
                    </span>
                </div>

                <div className="bg-surface-1 border border-border-1 rounded-2xl p-8">
                    <h1 className="font-display font-bold text-2xl text-chrome mb-1">Create account</h1>
                    <p className="text-chrome-dim text-sm font-mono mb-8">Get access to the AI SRE control plane</p>

                    {error && (
                        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
                            className="flex items-start gap-2 px-4 py-3 bg-ember/10 border border-ember/30 rounded-lg mb-6 text-sm text-ember font-mono">
                            <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
                            <span>{error}</span>
                        </motion.div>
                    )}

                    {success && (
                        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
                            className="flex items-center gap-2 px-4 py-3 bg-plasma/10 border border-plasma/30 rounded-lg mb-6 text-sm text-plasma font-mono">
                            <CheckCircle size={14} />
                            Account created! Redirecting to login…
                        </motion.div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label className="block text-xs font-mono text-chrome-dim mb-1.5">Email</label>
                            <div className="relative">
                                <Mail size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-chrome-dim" />
                                <input type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="you@company.com"
                                    className="w-full bg-surface-2 border border-border-1 rounded-lg pl-9 pr-4 py-3 text-sm font-mono text-chrome placeholder-border-2 focus:outline-none focus:border-plasma/50 transition-colors" />
                            </div>
                        </div>
                        <div>
                            <label className="block text-xs font-mono text-chrome-dim mb-1.5">Username</label>
                            <div className="relative">
                                <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-chrome-dim" />
                                <input type="text" value={username} onChange={e => setUsername(e.target.value)}
                                    required minLength={3} maxLength={64} pattern="^[a-zA-Z0-9_-]+" placeholder="sre-engineer"
                                    className="w-full bg-surface-2 border border-border-1 rounded-lg pl-9 pr-4 py-3 text-sm font-mono text-chrome placeholder-border-2 focus:outline-none focus:border-plasma/50 transition-colors" />
                            </div>
                        </div>
                        <div>
                            <label className="block text-xs font-mono text-chrome-dim mb-1.5">
                                Password <span className="text-border-2">(min. 8 characters)</span>
                            </label>
                            <div className="relative">
                                <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-chrome-dim" />
                                <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                                    required minLength={8} placeholder="••••••••"
                                    className="w-full bg-surface-2 border border-border-1 rounded-lg pl-9 pr-4 py-3 text-sm font-mono text-chrome placeholder-border-2 focus:outline-none focus:border-plasma/50 transition-colors" />
                            </div>
                        </div>
                        <button type="submit" disabled={loading || success}
                            className="w-full flex items-center justify-center gap-2 py-3 bg-plasma text-void font-display font-bold rounded-lg hover:bg-plasma-dim transition-colors disabled:opacity-50">
                            {loading ? <><Loader2 size={16} className="animate-spin" />Creating account…</> : "Create account"}
                        </button>
                    </form>

                    <p className="text-center text-xs font-mono text-chrome-dim mt-6">
                        Already have an account?{" "}
                        <Link href="/login" className="text-plasma hover:underline">Sign in</Link>
                    </p>
                </div>
            </motion.div>
        </div>
    );
}