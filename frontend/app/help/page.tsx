"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  CheckCircle2,
  GitBranch,
  HelpCircle,
  Network,
  Settings,
  Terminal,
  Workflow,
  Zap,
} from "lucide-react";
import NavBar from "../components/NavBar";
import PageFooter from "../components/PageFooter";

const sections = [
  {
    title: "Start an incident",
    icon: Terminal,
    text: "Open Chat, paste the incident symptoms, include affected services, timestamps, deployment IDs, and any useful log fragments.",
  },
  {
    title: "Understand orchestration",
    icon: Workflow,
    text: "The Orchestrator routes work to specialist agents, merges evidence, and asks for more analysis when confidence is low.",
  },
  {
    title: "Connect repo context",
    icon: GitBranch,
    text: "Set a GitHub token and default repository in Settings so Repo Scanner can inspect recent commits, PRs, and releases.",
  },
  {
    title: "Use graph evidence",
    icon: Network,
    text: "Graph Analyzer explains blast radius from service dependencies and helps identify upstream and downstream risk.",
  },
];

const checklist = [
  "Backend API is running and reachable from NEXT_PUBLIC_API_URL.",
  "LLM provider and API key are saved in Settings.",
  "GitHub repository is configured for Repo Scanner.",
  "Incident text includes service names and approximate time window.",
  "Operators validate remediation before running production changes.",
];

export default function HelpPage() {
  return (
    <div className="min-h-screen bg-void grid-bg text-chrome">
      <NavBar variant="inner" />

      <main className="max-w-6xl mx-auto px-6 py-16 pt-24">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 border border-border-2 rounded text-xs text-chrome-dim mb-6 font-mono">
            <HelpCircle size={12} className="text-plasma" />
            OPERATOR GUIDE
          </div>
          <h1 className="font-display text-4xl font-bold mb-4">Help Center</h1>
          <p className="text-chrome-dim font-mono text-sm max-w-2xl leading-relaxed">
            Use this page as the quick guide for running incidents through
            Ops-Pilot and understanding what each agent contributes.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
          {sections.map((section, index) => (
            <motion.section
              key={section.title}
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.06 }}
              className="bg-surface-1 border border-border-1 rounded-xl p-6"
            >
              <section.icon size={22} className="text-plasma mb-4" />
              <h2 className="font-display font-semibold mb-2">
                {section.title}
              </h2>
              <p className="text-sm text-chrome-dim font-mono leading-relaxed">
                {section.text}
              </p>
            </motion.section>
          ))}
        </div>

        <section className="bg-surface-1 border border-border-1 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-6">
            <Settings size={18} className="text-plasma" />
            <h2 className="font-display font-semibold">Pre-flight checklist</h2>
          </div>
          <div className="space-y-3">
            {checklist.map((item) => (
              <div key={item} className="flex items-start gap-3">
                <CheckCircle2
                  size={15}
                  className="text-plasma mt-0.5 shrink-0"
                />
                <p className="text-sm text-chrome-dim font-mono">{item}</p>
              </div>
            ))}
          </div>
        </section>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/chat"
            className="px-5 py-3 bg-plasma text-void rounded-lg font-display font-bold text-sm hover:bg-plasma-dim transition-colors"
          >
            Open Chat
          </Link>
          <Link
            href="/settings"
            className="px-5 py-3 border border-border-2 text-chrome-dim rounded-lg font-mono text-sm hover:border-plasma hover:text-plasma transition-colors"
          >
            Configure Settings
          </Link>
        </div>
      </main>
      <PageFooter />
    </div>
  );
}
