"use client";

import {
  ChangeEvent,
  FormEvent,
  KeyboardEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Activity,
  ArrowLeft,
  Bot,
  Brain,
  CheckCircle2,
  ChevronDown,
  FileText,
  GitBranch,
  History,
  LogIn,
  Network,
  Paperclip,
  Plus,
  Send,
  Settings,
  Shield,
  Sparkles,
  Terminal,
  Trash2,
  User,
  UserPlus,
  Workflow,
  Zap,
} from "lucide-react";
import { getAccessToken, streamIncident, uploadDocuments } from "../lib/apis";

type Message = {
  role: "user" | "assistant";
  content: string;
};

type ChatSessionLocal = {
  id: string;
  title: string;
  createdAt: string;
  backendSessionId: string | null;
  messages: Message[];
};

type Attachment = {
  filename: string;
  markdown: string;
  characters: number;
};

const STORAGE_KEY = "ops_pilot_chat_sessions_v3";

const agentTimeline = [
  {
    name: "Orchestrator",
    key: "orchestrator",
    icon: Workflow,
    color: "#00ccff",
    status: "Routes the turn",
  },
  {
    name: "Document Processor",
    key: "document_processor",
    icon: FileText,
    color: "#00ff88",
    status: "Adds document context",
  },
  {
    name: "Classifier",
    key: "classifier",
    icon: Bot,
    color: "#00ff88",
    status: "Sets severity",
  },
  {
    name: "Entity Extractor",
    key: "entity_extractor",
    icon: Terminal,
    color: "#00ccff",
    status: "Parses context",
  },
  {
    name: "Repo Scanner",
    key: "repo_scout",
    icon: GitBranch,
    color: "#00ff88",
    status: "Checks code changes",
  },
  {
    name: "Graph Analyzer",
    key: "graph_analyzer",
    icon: Network,
    color: "#ffaa00",
    status: "Maps blast radius",
  },
  {
    name: "Ops Analyst",
    key: "ops_analyst",
    icon: Activity,
    color: "#ffaa00",
    status: "Reads telemetry",
  },
  {
    name: "Root Cause Analyzer",
    key: "root_cause_finder",
    icon: Brain,
    color: "#00ccff",
    status: "Builds causal chain",
  },
  {
    name: "Remediator",
    key: "remediator",
    icon: Shield,
    color: "#00ff88",
    status: "Writes action plan",
  },
];

const starterPrompts = [
  "Checkout latency is spiking after deployment v2.3.1. Error rate is 12%.",
  "Payment service is timing out and Redis CPU is above 90%.",
  "Inventory writes are failing after the latest release. Find likely blast radius.",
];

function newSession(): ChatSessionLocal {
  return {
    id: crypto.randomUUID(),
    title: "New incident",
    createdAt: new Date().toISOString(),
    backendSessionId: null,
    messages: [
      {
        role: "assistant",
        content:
          "Ops-Pilot is ready. Paste an incident summary or upload PDFs, DOCX, PPTX, HTML, Excel, CSV, Markdown, or text files. Uploaded documents are converted to markdown and sent with the same chat turn.",
      },
    ],
  };
}

function loadSessions(): ChatSessionLocal[] {
  if (typeof window === "undefined") return [];
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
    return Array.isArray(parsed) && parsed.length > 0 ? parsed : [newSession()];
  } catch {
    return [newSession()];
  }
}

function stringifyResult(data: unknown): string {
  if (!data || typeof data !== "object") return "Analysis complete.";

  const d = data as Record<string, unknown>;
  const remediation = Array.isArray(d.remediation_steps)
    ? d.remediation_steps
    : [];
  const rollback = Array.isArray(d.rollback_steps) ? d.rollback_steps : [];
  const completed = Array.isArray(d.completed_steps) ? d.completed_steps : [];

  return [
    "Orchestrator completed the incident turn.",
    "",
    `Service: ${d.service ?? "unknown"}`,
    `Severity: ${d.severity ?? "unknown"}`,
    `Root cause: ${d.root_cause ?? "No root cause returned"}`,
    "",
    "Remediation:",
    remediation.length
      ? remediation
          .map((item, index) => `${index + 1}. ${String(item)}`)
          .join("\n")
      : "No remediation steps returned.",
    "",
    "Rollback:",
    rollback.length
      ? rollback
          .map((item, index) => `${index + 1}. ${String(item)}`)
          .join("\n")
      : "No rollback steps returned.",
    "",
    `Completed steps: ${completed.join(", ")}`,
  ].join("\n");
}

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSessionLocal[]>([]);
  const [activeId, setActiveId] = useState("");
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [running, setRunning] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [activeAgentKeys, setActiveAgentKeys] = useState<string[]>([
    "orchestrator",
  ]);
  const fileRef = useRef<HTMLInputElement>(null);
  const stopStreamRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    const loaded = loadSessions();
    setSessions(loaded);
    setActiveId(loaded[0].id);
  }, []);

  useEffect(() => {
    if (sessions.length)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  }, [sessions]);

  useEffect(() => {
    return () => stopStreamRef.current?.();
  }, []);

  const activeSession =
    sessions.find((session) => session.id === activeId) ?? sessions[0];
  const messages = activeSession?.messages ?? [];
  const isAuthed = Boolean(getAccessToken());

  const activeAgents = useMemo(
    () => agentTimeline.filter((agent) => activeAgentKeys.includes(agent.key)),
    [activeAgentKeys],
  );

  function updateActiveSession(
    updater: (session: ChatSessionLocal) => ChatSessionLocal,
  ) {
    setSessions((prev) =>
      prev.map((session) =>
        session.id === activeId ? updater(session) : session,
      ),
    );
  }

  function createNewChat() {
    const session = newSession();
    setSessions((prev) => [session, ...prev]);
    setActiveId(session.id);
    setInput("");
    setAttachments([]);
    setActiveAgentKeys(["orchestrator"]);
  }

  function deleteSession(id: string) {
    setSessions((prev) => {
      const next = prev.filter((session) => session.id !== id);
      if (activeId === id) setActiveId(next[0]?.id ?? "");
      return next.length ? next : [newSession()];
    });
  }

  async function handleFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    if (!files.length) return;

    setUploading(true);
    setActiveAgentKeys((prev) =>
      Array.from(new Set([...prev, "document_processor"])),
    );

    try {
      const result = await uploadDocuments(files);
      setAttachments((prev) => [
        ...prev,
        ...result.documents.map((doc) => ({
          filename: doc.filename,
          markdown: doc.markdown,
          characters: doc.characters,
        })),
      ]);
    } catch (error) {
      const detail =
        error instanceof Error ? error.message : "Document upload failed.";
      updateActiveSession((session) => ({
        ...session,
        messages: [
          ...session.messages,
          { role: "assistant", content: `Document Processor error: ${detail}` },
        ],
      }));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  function appendAssistant(content: string) {
    updateActiveSession((session) => {
      const copy = [...session.messages];
      const last = copy[copy.length - 1];

      if (
        last?.role === "assistant" &&
        last.content.startsWith("Running orchestration")
      ) {
        copy[copy.length - 1] = { role: "assistant", content };
      } else {
        copy.push({ role: "assistant", content });
      }

      return { ...session, messages: copy };
    });
  }

  function submitIncident(event?: FormEvent<HTMLFormElement>, prompt?: string) {
    event?.preventDefault();

    const text = (prompt ?? input).trim();
    if ((!text && !attachments.length) || running) return;

    const documentContext = attachments
      .map(
        (file) => `# Uploaded document: ${file.filename}\n\n${file.markdown}`,
      )
      .join("\n\n---\n\n");

    const title =
      text.slice(0, 48) || attachments[0]?.filename || "Document analysis";

    updateActiveSession((session) => ({
      ...session,
      title: session.title === "New incident" ? title : session.title,
      messages: [
        ...session.messages,
        {
          role: "user",
          content:
            text || `Analyze ${attachments.length} uploaded document(s).`,
        },
        {
          role: "assistant",
          content:
            "Running orchestration...\n\nDocument context, text message, and agent steps are being processed as one chat turn.",
        },
      ],
    }));

    setInput("");
    setAttachments([]);
    setRunning(true);
    setActiveAgentKeys([
      "orchestrator",
      ...(documentContext ? ["document_processor"] : []),
    ]);

    stopStreamRef.current?.();
    stopStreamRef.current = streamIncident(
      text || "Analyze uploaded document context.",
      activeSession.backendSessionId,
      documentContext,
      (event) => {
        if (event.agent) {
          setActiveAgentKeys((prev) =>
            Array.from(new Set([...prev, event.agent as string])),
          );
        }

        if (
          event.event === "session" &&
          event.data &&
          typeof event.data === "object"
        ) {
          const sid = (event.data as Record<string, unknown>).session_id;
          if (typeof sid === "string") {
            updateActiveSession((session) => ({
              ...session,
              backendSessionId: sid,
            }));
          }
        }

        if (event.event === "result") {
          appendAssistant(stringifyResult(event.data));
        }
      },
      (sessionId) => {
        if (sessionId)
          updateActiveSession((session) => ({
            ...session,
            backendSessionId: sessionId,
          }));
        setRunning(false);
      },
      (error) => {
        appendAssistant(`Orchestration error: ${error.message}`);
        setRunning(false);
      },
    );
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitIncident();
    }
  }

  if (!activeSession) return null;

  return (
    <div className="min-h-screen bg-void grid-bg text-chrome">
      <nav className="border-b border-border-1 bg-void/80 backdrop-blur-md">
        <div className="max-w-[1600px] mx-auto px-6 h-14 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2 text-chrome hover:text-plasma transition-colors"
          >
            <ArrowLeft size={16} />
            <Zap size={16} className="text-plasma" />
            <span className="font-display font-semibold text-sm">
              ops<span className="text-plasma">-pilot</span>
            </span>
          </Link>

          <div className="relative">
            <button
              onClick={() => setProfileOpen((open) => !open)}
              className="flex items-center gap-2 px-3 py-2 border border-border-1 rounded-lg text-xs font-mono text-chrome-dim hover:border-plasma hover:text-plasma transition-colors"
            >
              <User size={14} />
              Profile
              <ChevronDown size={13} />
            </button>

            {profileOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-surface-1 border border-border-1 rounded-lg p-2 shadow-xl z-50">
                {isAuthed ? (
                  <Link
                    href="/profile"
                    className="flex items-center gap-2 px-3 py-2 rounded text-xs font-mono text-chrome-dim hover:bg-surface-2 hover:text-plasma"
                  >
                    <User size={13} />
                    View profile
                  </Link>
                ) : (
                  <>
                    <Link
                      href="/login"
                      className="flex items-center gap-2 px-3 py-2 rounded text-xs font-mono text-chrome-dim hover:bg-surface-2 hover:text-plasma"
                    >
                      <LogIn size={13} />
                      Login
                    </Link>
                    <Link
                      href="/register"
                      className="flex items-center gap-2 px-3 py-2 rounded text-xs font-mono text-chrome-dim hover:bg-surface-2 hover:text-plasma"
                    >
                      <UserPlus size={13} />
                      Register
                    </Link>
                  </>
                )}
                <Link
                  href="/settings"
                  className="flex items-center gap-2 px-3 py-2 rounded text-xs font-mono text-chrome-dim hover:bg-surface-2 hover:text-plasma"
                >
                  <Settings size={13} />
                  Settings
                </Link>
              </div>
            )}
          </div>
        </div>
      </nav>

      <main className="max-w-[1600px] mx-auto px-6 py-6 grid grid-cols-1 xl:grid-cols-[260px_250px_minmax(0,1fr)] gap-5">
        <aside className="bg-surface-1 border border-border-1 rounded-xl p-4 h-[calc(100vh-6.5rem)] overflow-y-auto">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <History size={16} className="text-plasma" />
              <h2 className="font-display font-semibold text-sm">History</h2>
            </div>
            <button
              onClick={createNewChat}
              className="p-1.5 rounded border border-border-1 hover:border-plasma text-chrome-dim hover:text-plasma"
            >
              <Plus size={14} />
            </button>
          </div>

          <div className="space-y-2">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => setActiveId(session.id)}
                className={`w-full text-left p-3 rounded border transition-colors ${
                  session.id === activeId
                    ? "border-plasma bg-plasma/10 text-plasma"
                    : "border-border-1 text-chrome-dim hover:border-border-2"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="truncate text-xs font-mono flex-1">
                    {session.title}
                  </span>
                  <Trash2
                    size={12}
                    onClick={(click) => {
                      click.stopPropagation();
                      deleteSession(session.id);
                    }}
                  />
                </div>
                <div className="text-[10px] font-mono opacity-60 mt-1">
                  {new Date(session.createdAt).toLocaleString()}
                </div>
              </button>
            ))}
          </div>
        </aside>

        <aside className="space-y-4 h-[calc(100vh-6.5rem)] overflow-y-auto">
          <section className="bg-surface-1 border border-border-1 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-4">
              <Workflow size={16} className="text-ice" />
              <h2 className="font-display font-semibold text-sm">Agents</h2>
            </div>

            <div className="space-y-3">
              {agentTimeline.map((agent) => {
                const active = activeAgents.some((a) => a.key === agent.key);

                return (
                  <motion.div
                    key={agent.name}
                    initial={{ opacity: 0.45 }}
                    animate={{ opacity: active ? 1 : 0.45 }}
                    className="flex items-center gap-3"
                  >
                    <div className="w-8 h-8 rounded border border-border-1 bg-surface-2 flex items-center justify-center">
                      <agent.icon
                        size={14}
                        style={{ color: active ? agent.color : "#888888" }}
                      />
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-mono text-chrome truncate">
                        {agent.name}
                      </div>
                      <div className="text-[11px] font-mono text-chrome-dim truncate">
                        {agent.status}
                      </div>
                    </div>
                    {active && (
                      <CheckCircle2 size={13} className="ml-auto text-plasma" />
                    )}
                  </motion.div>
                );
              })}
            </div>
          </section>

          <section className="bg-surface-1 border border-border-1 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles size={16} className="text-plasma" />
              <h2 className="font-display font-semibold text-sm">Starters</h2>
            </div>
            <div className="space-y-2">
              {starterPrompts.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => submitIncident(undefined, prompt)}
                  className="w-full text-left text-xs font-mono text-chrome-dim border border-border-1 rounded p-3 hover:border-plasma hover:text-plasma transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </section>
        </aside>

        <section className="bg-surface-1 border border-border-1 rounded-xl h-[calc(100vh-6.5rem)] flex flex-col overflow-hidden">
          <div className="border-b border-border-1 p-5 flex items-center justify-between">
            <div>
              <h1 className="font-display font-bold text-xl">
                Incident Analysis
              </h1>
              <p className="text-xs text-chrome-dim font-mono mt-1">
                Enter sends. Shift+Enter adds a new line.
              </p>
            </div>
            <FileText size={18} className="text-plasma" />
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {messages.map((message, index) => (
              <motion.div
                key={`${message.role}-${index}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={
                  message.role === "user"
                    ? "flex justify-end"
                    : "flex justify-start"
                }
              >
                <div
                  className={
                    message.role === "user"
                      ? "max-w-[78%] rounded-xl bg-plasma text-void p-4 text-sm font-mono whitespace-pre-wrap"
                      : "max-w-[86%] rounded-xl bg-surface-2 border border-border-1 text-chrome p-4 text-sm font-mono leading-relaxed whitespace-pre-wrap"
                  }
                >
                  {message.content}
                </div>
              </motion.div>
            ))}
          </div>

          {attachments.length > 0 && (
            <div className="border-t border-border-1 px-4 py-3 flex flex-wrap gap-2">
              {attachments.map((file) => (
                <span
                  key={file.filename}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded border border-border-1 text-xs font-mono text-chrome-dim"
                >
                  <FileText size={12} className="text-plasma" />
                  {file.filename}
                  <span className="opacity-60">{file.characters} chars</span>
                </span>
              ))}
            </div>
          )}

          <form
            onSubmit={submitIncident}
            className="border-t border-border-1 p-4 flex gap-3"
          >
            <input
              ref={fileRef}
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.html,.htm,.md,.txt,.csv"
              onChange={handleFiles}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              disabled={uploading || running}
              className="self-end h-[52px] px-4 rounded-lg border border-border-2 text-chrome-dim hover:border-plasma hover:text-plasma transition-colors disabled:opacity-50"
              title="Upload documents"
            >
              <Paperclip size={17} />
            </button>
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Paste incident details, or upload documents to send with this turn..."
              className="flex-1 min-h-[52px] max-h-36 resize-y bg-surface-2 border border-border-1 rounded-lg px-4 py-3 text-sm font-mono text-chrome placeholder:text-chrome-dim/60 focus:outline-none focus:border-plasma"
            />
            <button
              type="submit"
              disabled={uploading || running}
              className="self-end h-[52px] px-5 rounded-lg bg-plasma text-void font-display font-bold hover:bg-plasma-dim transition-colors flex items-center gap-2 disabled:opacity-60"
            >
              <Send size={16} />
              {running ? "Running" : uploading ? "Uploading" : "Analyze"}
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
