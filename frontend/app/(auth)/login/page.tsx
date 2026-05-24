"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Zap, Mail, Lock, AlertCircle, Loader2 } from "lucide-react";
import { login } from "@/app/lib/api";

export default function LoginPage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = useCallback(
        async (e: React.FormEvent) => {
            e.preventDefault();
            setError("");
            setLoading(true);
            try {
                await login(email, password);
                router.push("/chat");
            } catch (err: unknown) {
                setError(err instanceof Error ? err.message : "Login failed");
            } finally {
                setLoading(false);
            }
        },
        [email, password, router]
    );

    return (
        <div className="min-h-screen bg-void grid-bg flex items-center justify-center px-4">
            {/* Background glow */}
            <div
                className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[500px] h-[500px] rounded-full pointer-events-none"
                style={{ background: "radial-gradient(circle, rgba(0,255,136,0.05) 0%, transparent 70%)" }}
            />

            <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="relative z-10 w-full max-w-md"
            >
                {/* Logo */}
                <div className="flex items-center justify-center gap-2 mb-10">
                    <Zap size={22} className="text-plasma" />
                    <span className="font-display font-bold text-xl text-chrome">
                        ops<span className="text-plasma">-pilot</span>
                    </span>
                </div>

                <div className="bg-surface-1 border border-border-1 rounded-2xl p-8">
                    <h1 className="font-display font-bold text-2xl text-chrome mb-1">
                        Sign in
                    </h1>
                    <p className="text-chrome-dim text-sm font-mono mb-8">
                        Access the AI SRE control plane
                    </p>

                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -8 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="flex items-center gap-2 px-4 py-3 bg-ember/10 border border-ember/30 rounded-lg mb-6 text-sm text-ember font-mono"
                        >
                            <AlertCircle size={14} />
                            {error}
                        </motion.div>
                    )}

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
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                    placeholder="you@company.com"
                                    className="w-full bg-surface-2 border border-border-1 rounded-lg pl-9 pr-4 py-3 text-sm font-mono text-chrome placeholder-border-2 focus:outline-none focus:border-plasma/50 transition-colors"
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
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    placeholder="••••••••"
                                    className="w-full bg-surface-2 border border-border-1 rounded-lg pl-9 pr-4 py-3 text-sm font-mono text-chrome placeholder-border-2 focus:outline-none focus:border-plasma/50 transition-colors"
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full flex items-center justify-center gap-2 py-3 bg-plasma text-void font-display font-bold rounded-lg hover:bg-plasma-dim transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? (
                                <>
                                    <Loader2 size={16} className="animate-spin" />
                                    Signing in…
                                </>
                            ) : (
                                "Sign in"
                            )}
                        </button>
                    </form>

                    <p className="text-center text-xs font-mono text-chrome-dim mt-6">
                        Don&apos;t have an account?{" "}
                        <Link href="/register" className="text-plasma hover:underline">
                            Register
                        </Link>
                    </p>
                </div>
            </motion.div>
        </div>
    );
}