"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  CheckCircle2,
  Github,
  Mail,
  MessageSquare,
  Send,
  Shield,
  Zap,
} from "lucide-react";

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
  }

  return (
    <div className="min-h-screen bg-void grid-bg text-chrome">
      <nav className="border-b border-border-1 bg-void/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2 hover:text-plasma transition-colors"
          >
            <ArrowLeft size={16} />
            <Zap size={16} className="text-plasma" />
            <span className="font-display font-semibold text-sm">
              ops<span className="text-plasma">-pilot</span>
            </span>
          </Link>

          <div className="flex items-center gap-4 text-xs font-mono text-chrome-dim">
            <Link href="/chat" className="hover:text-plasma transition-colors">
              Chat
            </Link>
            <Link href="/help" className="hover:text-plasma transition-colors">
              Help
            </Link>
            <Link
              href="/settings"
              className="hover:text-plasma transition-colors"
            >
              Settings
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-16 grid grid-cols-1 lg:grid-cols-[0.9fr_1.1fr] gap-8">
        <motion.section
          initial={{ opacity: 0, x: -18 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 border border-border-2 rounded text-xs text-chrome-dim mb-6 font-mono">
            <Mail size={12} className="text-plasma" />
            CONTACT
          </div>

          <h1 className="font-display text-4xl font-bold mb-4">
            Talk to the Ops-Pilot team
          </h1>
          <p className="text-chrome-dim font-mono text-sm leading-relaxed mb-8">
            Send integration questions, deployment issues, bug reports, or
            feature requests. The form is local UI for now, so wire it to your
            backend email or ticket endpoint when ready.
          </p>

          <div className="space-y-4">
            {[
              {
                icon: MessageSquare,
                title: "Incident workflow feedback",
                text: "Share missing agent steps, confusing evidence, or operator needs.",
              },
              {
                icon: Github,
                title: "Repo Scanner setup",
                text: "Ask about GitHub token scopes, repository format, and deployment metadata.",
              },
              {
                icon: Shield,
                title: "Production readiness",
                text: "Discuss validation gates, audit trails, and remediation approval flows.",
              },
            ].map((item) => (
              <div
                key={item.title}
                className="bg-surface-1 border border-border-1 rounded-xl p-5"
              >
                <item.icon size={18} className="text-plasma mb-3" />
                <h2 className="font-display font-semibold mb-1">
                  {item.title}
                </h2>
                <p className="text-sm text-chrome-dim font-mono leading-relaxed">
                  {item.text}
                </p>
              </div>
            ))}
          </div>
        </motion.section>

        <motion.section
          initial={{ opacity: 0, x: 18 }}
          animate={{ opacity: 1, x: 0 }}
          className="bg-surface-1 border border-border-1 rounded-xl p-6"
        >
          {submitted ? (
            <div className="min-h-[420px] flex flex-col items-center justify-center text-center">
              <CheckCircle2 size={42} className="text-plasma mb-4" />
              <h2 className="font-display text-2xl font-bold mb-2">
                Message captured
              </h2>
              <p className="text-chrome-dim font-mono text-sm max-w-md">
                The UI is working. Connect this form to your backend contact
                endpoint to send real messages.
              </p>
              <button
                onClick={() => setSubmitted(false)}
                className="mt-6 px-5 py-3 border border-border-2 rounded-lg text-sm font-mono text-chrome-dim hover:border-plasma hover:text-plasma transition-colors"
              >
                Send another
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-chrome-dim mb-2">
                  Name
                </label>
                <input
                  className="w-full bg-surface-2 border border-border-1 rounded-lg px-4 py-3 text-sm font-mono text-chrome focus:outline-none focus:border-plasma"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-chrome-dim mb-2">
                  Email
                </label>
                <input
                  type="email"
                  className="w-full bg-surface-2 border border-border-1 rounded-lg px-4 py-3 text-sm font-mono text-chrome focus:outline-none focus:border-plasma"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-chrome-dim mb-2">
                  Topic
                </label>
                <select className="w-full bg-surface-2 border border-border-1 rounded-lg px-4 py-3 text-sm font-mono text-chrome focus:outline-none focus:border-plasma">
                  <option>Integration help</option>
                  <option>Bug report</option>
                  <option>Feature request</option>
                  <option>Production readiness</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono text-chrome-dim mb-2">
                  Message
                </label>
                <textarea
                  rows={8}
                  className="w-full bg-surface-2 border border-border-1 rounded-lg px-4 py-3 text-sm font-mono text-chrome focus:outline-none focus:border-plasma resize-y"
                  required
                />
              </div>

              <button
                type="submit"
                className="w-full flex items-center justify-center gap-2 px-5 py-3 bg-plasma text-void rounded-lg font-display font-bold hover:bg-plasma-dim transition-colors"
              >
                <Send size={16} />
                Send Message
              </button>
            </form>
          )}
        </motion.section>
      </main>
    </div>
  );
}
