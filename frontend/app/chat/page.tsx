"use client";

import { useCallback, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Zap, LayoutPanelLeft, Plus } from "lucide-react";
import Link from "next/link";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { ChatInput } from "@/components/chat/ChatInput";
import { SessionSidebar } from "@/components/chat/SessionSidebar";
import { AgentExecutionPanel } from "@/components/agents/AgentExecutionPanel";
import { ServiceGraph } from "@/components/graph/ServiceGraph";
import { useChatStore } from "@/store/chat-store";
import { useIncidentStream } from "@/hooks/useIncidentStream";
import type { GraphContext } from "@/types";

export default function ChatPage() {
  const { messages, clearMessages, setActiveSession } = useChatStore();
  const { submit, cancel } = useIncidentStream();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const handleNewChat = useCallback(() => {
    clearMessages();
    setActiveSession("");
  }, [clearMessages, setActiveSession]);

  const lastResult = [...messages].reverse().find((m) => m.finalResult)?.finalResult;
  const graphCtx = (lastResult?.graph_context as GraphContext | undefined) ?? null;

  return (
    <div className="flex h-screen bg-void overflow-hidden">
      {/* ── Sidebar ── */}
      <SessionSidebar onNewChat={handleNewChat} />

      {/* ── Main ── */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <div className="h-14 border-b border-border-1 bg-surface-1 flex items-center justify-between px-6 flex-shrink-0">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
              <Zap size={16} className="text-plasma" />
              <span className="text-sm font-mono text-chrome font-semibold">ops-pilot</span>
            </Link>
            <span className="text-border-1">/</span>
            <span className="text-sm font-mono text-chrome-dim">Incident Analysis</span>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono text-chrome-dim">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-plasma animate-pulse" />
              <span className="text-plasma">AGENTS READY</span>
            </div>
            <button
              onClick={handleNewChat}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-border-1 rounded hover:border-plasma hover:text-plasma transition-colors"
            >
              <Plus size={12} />
              New Chat
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center h-full gap-8 text-center"
            >
              <div className="relative">
                <div className="w-20 h-20 rounded-2xl bg-surface-2 border border-border-1 flex items-center justify-center">
                  <Zap size={36} className="text-plasma" />
                </div>
                <motion.div
                  animate={{ scale: [1, 1.4, 1], opacity: [0.5, 0, 0.5] }}
                  transition={{ repeat: Infinity, duration: 2.5 }}
                  className="absolute inset-0 rounded-2xl border border-plasma"
                />
              </div>
              <div className="max-w-md">
                <h2 className="font-display text-2xl font-bold text-chrome mb-3">
                  ops<span className="text-plasma">-pilot</span>
                </h2>
                <p className="text-chrome-dim text-sm font-mono leading-relaxed">
                  Describe a production incident below. Five AI agents will classify it,
                  traverse your service dependency graph, identify root cause, and stream
                  a full remediation plan — live.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3 max-w-md w-full">
                {[
                  "5 specialized agents",
                  "Neo4j graph traversal",
                  "Live SSE streaming",
                  "Structured LLM output",
                ].map((item) => (
                  <div
                    key={item}
                    className="flex items-center gap-2 px-3 py-2 bg-surface-1 border border-border-1 rounded text-xs font-mono text-chrome-dim"
                  >
                    <span className="text-plasma">●</span>
                    {item}
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          <AnimatePresence>
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
          </AnimatePresence>
          <div ref={bottomRef} />
        </div>

        <ChatInput onSubmit={submit} onCancel={cancel} />
      </div>

      {/* ── Right panel ── */}
      <div className="w-80 border-l border-border-1 bg-surface-1 flex flex-col gap-4 p-4 overflow-y-auto flex-shrink-0">
        <AgentExecutionPanel />
        <div className="flex-1 min-h-[280px]">
          <ServiceGraph graphContext={graphCtx} />
        </div>
      </div>
    </div>
  );
}