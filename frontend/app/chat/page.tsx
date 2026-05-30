"use client";

import {
  ChangeEvent,
  FormEvent,
  KeyboardEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import Link from "next/link";
import ReactDOM from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import {
  Activity,
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Bot,
  Brain,
  CheckCircle2,
  ExternalLink,
  FileSearch,
  FileText,
  GitBranch,
  History,
  Network,
  Paperclip,
  Plus,
  Send,
  Shield,
  Sparkles,
  Square,
  Terminal,
  Trash2,
  Wrench,
  Workflow,
  X,
  Zap,
} from "lucide-react";
import { streamIncident, uploadDocuments, type WebCitation } from "../lib/apis";

type Message = {
  role: "user" | "assistant";
  content: string;
  naturalResponse?: string;
  isIncidentRelevant?: boolean;
  citations?: WebCitation[];
};

type ChatSessionLocal = {
  id: string;
  title: string;
  createdAt: string;
  backendSessionId: string | null;
  messages: Message[];
  explainabilityEvents: ExplainabilityEvent[];
};

type Attachment = {
  filename: string;
  markdown: string;
  characters: number;
};

type ExplainabilityEvent = {
  id: string;
  agent: string;
  step: string;
  status: string;
  detail: string;
  rawData: Record<string, unknown> | null;
  inputHint: string | null;
  outputHint: string | null;
  errorInfo: string | null;
};

const STORAGE_KEY = "ops_pilot_chat_sessions_v4";

const requiredAgentKeys = new Set([
  "orchestrator",
  "classifier",
  "entity_extractor",
  "graph_analyzer",
  "root_cause_finder",
  "remediator",
  "conversationalist",
]);

const documentOnlyAgentKeys = new Set(["document_processor"]);

const agentTimeline = [
  {
    name: "Orchestrator",
    key: "orchestrator",
    icon: Workflow,
    color: "#00ccff",
    status: "Routes the turn",
    required: true,
  },
  {
    name: "Document Processor",
    key: "document_processor",
    icon: FileText,
    color: "#00ff88",
    status: "Adds document context",
    required: false,
  },
  {
    name: "Classifier",
    key: "classifier",
    icon: Bot,
    color: "#00ff88",
    status: "Sets severity",
    required: true,
  },
  {
    name: "Entity Extractor",
    key: "entity_extractor",
    icon: Terminal,
    color: "#00ccff",
    status: "Parses context",
    required: true,
  },
  {
    name: "Repo Scanner",
    key: "repo_scout",
    icon: GitBranch,
    color: "#00ff88",
    status: "Checks code changes",
    required: false,
  },
  {
    name: "Terraform Scanner",
    key: "terraform_scout",
    icon: Wrench,
    color: "#7c5cff",
    status: "Checks IaC drift",
    required: false,
  },
  {
    name: "Graph Analyzer",
    key: "graph_analyzer",
    icon: Network,
    color: "#ffaa00",
    status: "Maps blast radius",
    required: true,
  },
  {
    name: "Web Intelligence",
    key: "web_searcher",
    icon: FileSearch,
    color: "#ff4444",
    status: "Checks external signals",
    required: false,
  },
  {
    name: "Ops Analyst",
    key: "ops_analyst",
    icon: Activity,
    color: "#ffaa00",
    status: "Reads telemetry",
    required: false,
  },
  {
    name: "Crew Intelligence",
    key: "crew",
    icon: Sparkles,
    color: "#00ccff",
    status: "Synthesizes evidence",
    required: false,
  },
  {
    name: "Root Cause Analyzer",
    key: "root_cause_finder",
    icon: Brain,
    color: "#00ccff",
    status: "Builds causal chain",
    required: true,
  },
  {
    name: "Remediator",
    key: "remediator",
    icon: Shield,
    color: "#00ff88",
    status: "Writes action plan",
    required: true,
  },
  {
    name: "Conversationalist",
    key: "conversationalist",
    icon: Sparkles,
    color: "#c084fc",
    status: "Narrates the analysis",
    required: true,
  },
];

const defaultEnabledAgentKeys = agentTimeline
  .filter(
    (agent) =>
      !documentOnlyAgentKeys.has(agent.key) &&
      (agent.required ||
        !["repo_scout", "terraform_scout"].includes(agent.key)),
  )
  .map((agent) => agent.key);

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
          "Ops-Pilot is ready. Paste an incident summary or upload supported documents: PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX, HTML, Markdown, CSV, and TXT. Uploaded documents are converted to markdown by the Document Processor and sent with the same chat turn.",
      },
    ],
    explainabilityEvents: [],
  };
}

function loadSessions(): ChatSessionLocal[] {
  if (typeof window === "undefined") return [];
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
    if (!Array.isArray(parsed) || parsed.length === 0) return [newSession()];
    return parsed.map((s: ChatSessionLocal) => ({
      ...s,
      explainabilityEvents: Array.isArray(s.explainabilityEvents)
        ? s.explainabilityEvents
        : [],
    }));
  } catch {
    return [newSession()];
  }
}

function isSuccessStatus(status?: string) {
  return ["complete", "completed", "success", "done"].includes(
    (status ?? "").toLowerCase(),
  );
}

function isErrorStatus(status?: string) {
  return ["error", "failed", "failure"].includes((status ?? "").toLowerCase());
}

function statusDotClass(status?: string) {
  if (isSuccessStatus(status)) return "bg-emerald-400";
  if (isErrorStatus(status)) return "bg-red-500";
  return "bg-plasma";
}

function statusBorderClass(status?: string) {
  if (isSuccessStatus(status)) return "border-emerald-500/40";
  if (isErrorStatus(status)) return "border-red-500/40";
  return "border-border-1";
}

function statusGlowColor(status?: string) {
  if (isSuccessStatus(status)) return "rgba(52, 211, 153, 0.65)";
  if (isErrorStatus(status)) return "rgba(239, 68, 68, 0.65)";
  return "rgba(34, 211, 238, 0.55)";
}

function statusLabel(status?: string) {
  if (isSuccessStatus(status)) return "Completed";
  if (isErrorStatus(status)) return "Error";
  return "Running";
}

/** Render assistant message content with proper markdown */
function AssistantMessage({ message }: { message: Message }) {
  const hasBoth =
    message.isIncidentRelevant !== false &&
    message.naturalResponse &&
    message.content &&
    message.content !== message.naturalResponse;

  const textToRender = message.naturalResponse ?? message.content;

  return (
    <div className="max-w-[90%] rounded-xl bg-surface-2 border border-border-1 text-chrome p-4 text-sm font-mono leading-relaxed space-y-3">
      {/* Markdown-rendered natural language response */}
      <div className="prose-ops">
        <ReactMarkdown
          components={{
            h1: ({ children }) => (
              <h1 className="text-base font-bold text-chrome mb-2 mt-3 first:mt-0">
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-sm font-bold text-chrome mb-1.5 mt-3 first:mt-0">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-sm font-semibold text-chrome mb-1 mt-2 first:mt-0">
                {children}
              </h3>
            ),
            p: ({ children }) => (
              <p className="mb-2 last:mb-0 text-chrome leading-relaxed">
                {children}
              </p>
            ),
            strong: ({ children }) => (
              <strong className="font-bold text-chrome">{children}</strong>
            ),
            em: ({ children }) => (
              <em className="italic text-chrome-dim">{children}</em>
            ),
            ul: ({ children }) => (
              <ul className="list-disc list-inside space-y-1 mb-2 text-chrome">
                {children}
              </ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal list-inside space-y-1 mb-2 text-chrome">
                {children}
              </ol>
            ),
            li: ({ children }) => (
              <li className="text-chrome leading-relaxed">{children}</li>
            ),
            code: ({ children, className }) => {
              const isBlock = className?.includes("language-");
              if (isBlock) {
                return (
                  <code className="block bg-surface-1 border border-border-1 rounded p-3 text-xs text-plasma whitespace-pre-wrap mb-2">
                    {children}
                  </code>
                );
              }
              return (
                <code className="bg-surface-1 border border-border-1 rounded px-1 py-0.5 text-xs text-plasma">
                  {children}
                </code>
              );
            },
            pre: ({ children }) => (
              <pre className="bg-surface-1 border border-border-1 rounded p-3 overflow-x-auto mb-2 text-xs text-plasma">
                {children}
              </pre>
            ),
            blockquote: ({ children }) => (
              <blockquote className="border-l-2 border-plasma pl-3 text-chrome-dim italic mb-2">
                {children}
              </blockquote>
            ),
            a: ({ href, children }) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-plasma hover:underline inline-flex items-center gap-1"
              >
                {children}
                <ExternalLink size={10} className="inline shrink-0" />
              </a>
            ),
            hr: () => <hr className="border-border-1 my-3" />,
          }}
        >
          {textToRender}
        </ReactMarkdown>
      </div>

      {/* Structured analysis accordion — only shown when there's an incident result */}
      {hasBoth && (
        <details className="group border border-border-1 rounded-lg">
          <summary className="cursor-pointer px-3 py-2 text-[11px] text-chrome-dim hover:text-plasma flex items-center gap-2 list-none">
            <Network size={12} className="text-plasma shrink-0" />
            <span>View structured analysis</span>
          </summary>
          <div className="px-3 pb-3 pt-1 text-[11px] text-chrome-dim whitespace-pre-wrap border-t border-border-1 mt-2">
            {message.content}
          </div>
        </details>
      )}

      {/* Web citations */}
      {message.citations && message.citations.length > 0 && (
        <div className="border-t border-border-1 pt-3">
          <p className="text-[10px] text-chrome-dim mb-2 uppercase tracking-widest">
            Sources
          </p>
          <ul className="space-y-1">
            {message.citations.map((citation) => (
              <li key={citation.url}>
                <a
                  href={citation.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-[11px] text-plasma hover:underline truncate max-w-full"
                >
                  <ExternalLink size={10} className="shrink-0" />
                  <span className="truncate">{citation.title}</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Scroll control button pair */
function ScrollControls({
  show,
  onTop,
  onBottom,
  topLabel,
  bottomLabel,
  inline,
}: {
  show: boolean;
  onTop: () => void;
  onBottom: () => void;
  topLabel: string;
  bottomLabel: string;
  inline?: boolean;
}) {
  if (!show) return null;

  if (inline) {
    return (
      <div className="flex gap-1">
        <button
          type="button"
          onClick={onTop}
          className="h-8 w-8 rounded-md border border-border-1 text-chrome hover:text-foreground flex items-center justify-center"
          aria-label={topLabel}
        >
          <ArrowUp size={15} />
        </button>
        <button
          type="button"
          onClick={onBottom}
          className="h-8 w-8 rounded-md border border-border-1 text-chrome hover:text-foreground flex items-center justify-center"
          aria-label={bottomLabel}
        >
          <ArrowDown size={15} />
        </button>
      </div>
    );
  }

  return (
    <div className="absolute right-4 bottom-4 z-10 flex flex-col gap-2">
      <button
        type="button"
        onClick={onTop}
        className="h-9 w-9 rounded-full border border-border-1 bg-surface-1/90 text-chrome hover:text-foreground flex items-center justify-center"
        aria-label={topLabel}
      >
        <ArrowUp size={16} />
      </button>
      <button
        type="button"
        onClick={onBottom}
        className="h-9 w-9 rounded-full border border-border-1 bg-surface-1/90 text-chrome hover:text-foreground flex items-center justify-center"
        aria-label={bottomLabel}
      >
        <ArrowDown size={16} />
      </button>
    </div>
  );
}

/** History panel */
function HistoryPanel({
  sessions,
  activeId,
  onSelect,
  onCreate,
  onDelete,
}: {
  sessions: ChatSessionLocal[];
  activeId: string;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const topRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showControls, setShowControls] = useState(false);

  const checkOverflow = useCallback(() => {
    const node = scrollRef.current;
    setShowControls(!!node && node.scrollHeight - node.clientHeight > 8);
  }, []);

  useEffect(() => {
    checkOverflow();
    const obs = new ResizeObserver(checkOverflow);
    if (scrollRef.current) obs.observe(scrollRef.current);
    window.addEventListener("resize", checkOverflow);
    return () => {
      obs.disconnect();
      window.removeEventListener("resize", checkOverflow);
    };
  }, [checkOverflow, sessions.length]);

  return (
    <aside className="bg-surface-1 border border-border-1 rounded-xl p-4 h-[calc(100vh-6.5rem)] flex flex-col overflow-hidden">
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div className="flex items-center gap-2">
          <History size={16} className="text-plasma" />
          <h2 className="font-display font-semibold text-sm">History</h2>
        </div>
        <div className="flex items-center gap-1">
          <ScrollControls
            show={showControls}
            onTop={() =>
              topRef.current?.scrollIntoView({
                behavior: "smooth",
                block: "start",
              })
            }
            onBottom={() =>
              bottomRef.current?.scrollIntoView({
                behavior: "smooth",
                block: "end",
              })
            }
            topLabel="Scroll history to top"
            bottomLabel="Scroll history to bottom"
            inline
          />
          <button
            onClick={onCreate}
            className="p-1.5 rounded border border-border-1 hover:border-plasma text-chrome-dim hover:text-plasma"
          >
            <Plus size={14} />
          </button>
        </div>
      </div>

      <div
        ref={scrollRef}
        onScroll={checkOverflow}
        className="flex-1 overflow-y-auto space-y-2"
      >
        <div ref={topRef} />
        {sessions.map((session) => (
          <button
            key={session.id}
            onClick={() => onSelect(session.id)}
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
                  onDelete(session.id);
                }}
              />
            </div>
            <div className="text-[10px] font-mono opacity-60 mt-1">
              {new Date(session.createdAt).toLocaleString()}
            </div>
          </button>
        ))}
        <div ref={bottomRef} />
      </div>
    </aside>
  );
}

/** Full-screen modal for a single explainability event */
function ExplainabilityModal({
  event: ev,
  onClose,
}: {
  event: ExplainabilityEvent;
  onClose: () => void;
}) {
  const agentInfo = agentTimeline.find((a) => a.key === ev.agent);

  // Close on Escape
  useEffect(() => {
    const handler = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const completedSteps: string[] =
    ev.rawData && Array.isArray(ev.rawData.completed_steps)
      ? (ev.rawData.completed_steps as string[])
      : [];

  const DEDICATED_KEYS = new Set([
    "completed_steps",
    "description",
    "input",
    "output",
    "message",
    "error",
    "query",
    "payload",
    "primary_cause",
    "root_cause",
    "results_count",
    "report_length",
    "characters",
  ]);

  const rawEntries = ev.rawData
    ? Object.entries(ev.rawData).filter(
        ([k, v]) =>
          !DEDICATED_KEYS.has(k) &&
          v !== null &&
          v !== undefined &&
          v !== "" &&
          !(Array.isArray(v) && v.length === 0),
      )
    : [];

  return (
    <AnimatePresence>
      <motion.div
        key="overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.18 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-void/80 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          key="modal"
          initial={{ opacity: 0, scale: 0.88, y: 24 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.92, y: 12 }}
          transition={{ type: "spring", stiffness: 320, damping: 26 }}
          className="relative bg-surface-1 border border-border-2 rounded-2xl p-6 max-w-lg w-full mx-4 shadow-2xl max-h-[85vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Close button */}
          <button
            type="button"
            onClick={onClose}
            className="absolute top-4 right-4 h-8 w-8 rounded-md border border-border-1 text-chrome-dim hover:text-plasma hover:border-plasma flex items-center justify-center transition-colors"
            aria-label="Close"
          >
            <X size={14} />
          </button>

          {/* Agent header */}
          <div className="flex items-center gap-3 mb-5">
            <div
              className="w-10 h-10 rounded-lg border border-border-2 bg-surface-2 flex items-center justify-center"
              style={{
                boxShadow: `0 0 12px 0 ${statusGlowColor(ev.status)}`,
              }}
            >
              {agentInfo ? (
                <agentInfo.icon size={18} style={{ color: agentInfo.color }} />
              ) : (
                <Network size={18} className="text-plasma" />
              )}
            </div>
            <div>
              <p className="text-xs font-mono text-chrome-dim uppercase tracking-widest">
                {ev.agent}
              </p>
              <p className="text-sm font-bold text-chrome mt-0.5">{ev.step}</p>
            </div>
          </div>

          {/* Status badge */}
          <div className="flex items-center gap-2 mb-4">
            <motion.span
              initial={{ scale: 1 }}
              animate={{
                scale: [1, 1.4, 1],
                boxShadow: [
                  `0 0 0 0 ${statusGlowColor(ev.status)}`,
                  "0 0 0 6px transparent",
                  "0 0 0 0 transparent",
                ],
              }}
              transition={{ duration: 1.2, repeat: 2 }}
              className={`h-2.5 w-2.5 rounded-full shrink-0 ${statusDotClass(ev.status)}`}
            />
            <span className="text-xs font-mono text-chrome-dim">
              Status:{" "}
              <span
                className={
                  isSuccessStatus(ev.status)
                    ? "text-emerald-400"
                    : isErrorStatus(ev.status)
                      ? "text-red-400"
                      : "text-plasma"
                }
              >
                {statusLabel(ev.status)}
              </span>
            </span>
          </div>

          {/* Agent description from timeline */}
          {agentInfo && (
            <div className="flex items-center gap-2 mb-4 px-3 py-2 rounded-lg bg-surface-2 border border-border-1">
              <agentInfo.icon size={13} style={{ color: agentInfo.color }} />
              <p className="text-[11px] text-chrome-dim font-mono leading-relaxed">
                {agentInfo.name} — {agentInfo.status}
              </p>
            </div>
          )}

          {/* What this step does — description from backend.
              Hidden when in error state to avoid duplicating the error string. */}
          {ev.detail && !isErrorStatus(ev.status) && (
            <div className="mb-4 border-l-2 border-plasma/40 pl-3">
              <p className="text-[10px] text-plasma font-mono uppercase tracking-widest mb-1">
                What this step does
              </p>
              <p className="text-[11px] text-chrome font-mono leading-relaxed whitespace-pre-wrap">
                {ev.detail}
              </p>
            </div>
          )}

          {/* Error — shown only when status is error; detail suppressed above to prevent repeat */}
          {ev.errorInfo && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-3">
              <p className="text-[11px] text-red-400 font-mono uppercase tracking-widest mb-2">
                ⚠ Error
              </p>
              <p className="text-xs text-red-300 font-mono leading-relaxed whitespace-pre-wrap">
                {ev.errorInfo}
              </p>
            </div>
          )}

          {/* Input */}
          {ev.inputHint && (
            <div className="bg-surface-2 border border-border-1 rounded-lg p-4 mb-3">
              <p className="text-[11px] text-chrome-dim font-mono uppercase tracking-widest mb-2">
                → Input
              </p>
              <p className="text-xs text-chrome font-mono leading-relaxed whitespace-pre-wrap">
                {ev.inputHint}
              </p>
            </div>
          )}

          {/* Output */}
          {ev.outputHint && (
            <div className="bg-surface-2 border border-emerald-500/20 rounded-lg p-4 mb-3">
              <p className="text-[11px] text-emerald-400 font-mono uppercase tracking-widest mb-2">
                ← Output
              </p>
              <p className="text-xs text-chrome font-mono leading-relaxed whitespace-pre-wrap">
                {ev.outputHint}
              </p>
            </div>
          )}

          {/* Completed steps */}
          {completedSteps.length > 0 && (
            <div className="mb-3">
              <p className="text-[11px] text-emerald-400 font-mono uppercase tracking-widest mb-2">
                Pipeline progress
              </p>
              <div className="flex flex-wrap gap-1.5">
                {completedSteps.map((s) => (
                  <span
                    key={s}
                    className="px-2 py-0.5 rounded border border-emerald-500/30 bg-emerald-500/10 text-[10px] font-mono text-emerald-400"
                  >
                    ✓ {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Raw agent data — collapsible, filtered to interesting keys */}
          {rawEntries.length > 0 && (
            <details className="mb-3">
              <summary className="cursor-pointer text-[11px] font-mono text-chrome-dim hover:text-plasma list-none mb-2">
                <span className="text-plasma">&#9658;</span> Raw agent data
              </summary>
              <div className="bg-surface-2 border border-border-1 rounded-lg p-3 space-y-2 max-h-72 overflow-y-auto mt-2">
                {rawEntries.map(([key, value]) => (
                  <div
                    key={key}
                    className="border-b border-border-1/40 pb-2 last:border-0 last:pb-0"
                  >
                    <p className="text-[10px] font-mono text-chrome-dim uppercase tracking-wider mb-0.5">
                      {key.replace(/_/g, " ")}
                    </p>
                    <p className="text-[11px] font-mono text-chrome leading-relaxed break-words whitespace-pre-wrap">
                      {Array.isArray(value)
                        ? value.length === 0
                          ? "—"
                          : value
                              .map((item, i) =>
                                typeof item === "object"
                                  ? `${i + 1}. ${JSON.stringify(item, null, 2).slice(0, 200)}`
                                  : `${i + 1}. ${String(item)}`,
                              )
                              .join("\n")
                        : typeof value === "object" && value !== null
                          ? JSON.stringify(value, null, 2).slice(0, 600)
                          : String(value).slice(0, 400)}
                    </p>
                  </div>
                ))}
              </div>
            </details>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

/** Single explainability event card — with hover tooltip and click-to-open */
function ExplainabilityCard({
  event,
  onOpen,
}: {
  event: ExplainabilityEvent;
  onOpen: (event: ExplainabilityEvent) => void;
}) {
  const [tooltipPos, setTooltipPos] = useState<{
    top: number;
    left: number;
  } | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const agentInfo = agentTimeline.find((a) => a.key === event.agent);

  function handleMouseEnter() {
    if (cardRef.current) {
      const rect = cardRef.current.getBoundingClientRect();
      setTooltipPos({ top: rect.top, left: rect.right + 8 });
    }
  }

  function handleMouseLeave() {
    setTooltipPos(null);
  }

  const tooltip = tooltipPos ? (
    <AnimatePresence>
      <motion.div
        key={event.id + "-tooltip"}
        initial={{ opacity: 0, x: 8, scale: 0.95 }}
        animate={{ opacity: 1, x: 0, scale: 1 }}
        exit={{ opacity: 0, x: 8, scale: 0.95 }}
        transition={{ duration: 0.12 }}
        style={{
          position: "fixed",
          top: tooltipPos.top,
          left: tooltipPos.left,
          zIndex: 9999,
          width: 224,
        }}
        className="pointer-events-none"
      >
        <div className="bg-void border border-border-2 rounded-lg p-3 shadow-2xl">
          <div className="flex items-center gap-2 mb-1">
            {agentInfo ? (
              <agentInfo.icon size={12} style={{ color: agentInfo.color }} />
            ) : (
              <Network size={12} className="text-plasma" />
            )}
            <span className="text-[11px] font-mono text-chrome font-bold">
              {agentInfo?.name ?? event.agent}
            </span>
          </div>
          <p className="text-[10px] font-mono text-chrome-dim leading-relaxed">
            {event.detail.length > 120
              ? event.detail.slice(0, 120) + "…"
              : event.detail}
          </p>
          {event.inputHint && (
            <p className="text-[10px] font-mono text-chrome-dim mt-1.5 leading-relaxed">
              <span className="text-plasma">In:</span>{" "}
              {event.inputHint.slice(0, 80)}
              {event.inputHint.length > 80 ? "…" : ""}
            </p>
          )}
          {event.outputHint && (
            <p className="text-[10px] font-mono text-chrome-dim mt-1 leading-relaxed">
              <span className="text-emerald-400">Out:</span>{" "}
              {event.outputHint.slice(0, 80)}
              {event.outputHint.length > 80 ? "…" : ""}
            </p>
          )}
          <p className="text-[10px] font-mono mt-1.5">
            <span
              className={
                isSuccessStatus(event.status)
                  ? "text-emerald-400"
                  : isErrorStatus(event.status)
                    ? "text-red-400"
                    : "text-plasma"
              }
            >
              {statusLabel(event.status)}
            </span>
          </p>
        </div>
      </motion.div>
    </AnimatePresence>
  ) : null;

  return (
    <>
      {typeof window !== "undefined" &&
        tooltipPos &&
        typeof document !== "undefined" &&
        ReactDOM.createPortal(tooltip, document.body)}
      <div className="relative" ref={cardRef}>
        <motion.div
          key={event.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className={`border rounded-lg p-3 bg-surface-2 ${statusBorderClass(event.status)} cursor-pointer hover:border-plasma/60 transition-colors group`}
          onClick={() => onOpen(event)}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && onOpen(event)}
          aria-label={`Open details for ${event.agent} — ${event.step}`}
        >
          <div className="flex items-center justify-between gap-2 mb-1">
            <div className="flex items-center gap-2 min-w-0">
              <motion.span
                initial={{
                  scale: 1,
                  boxShadow: `0 0 0 0 ${statusGlowColor(event.status)}`,
                }}
                animate={{
                  scale: [1, 1.55, 1],
                  boxShadow: [
                    `0 0 0 0 ${statusGlowColor(event.status)}`,
                    "0 0 0 7px transparent",
                    "0 0 0 0 transparent",
                  ],
                }}
                transition={{ duration: 0.85, ease: "easeOut" }}
                className={`h-2.5 w-2.5 rounded-full shrink-0 ${statusDotClass(event.status)}`}
              />
              <span className="text-xs text-plasma font-mono truncate">
                {event.agent}
              </span>
            </div>
            <span className="text-[10px] text-chrome-dim font-mono">
              {event.status}
            </span>
          </div>
          <div className="text-xs text-chrome font-mono mb-1">{event.step}</div>
          <p className="text-[11px] text-chrome-dim font-mono leading-relaxed line-clamp-2">
            {event.detail}
          </p>
          <p className="text-[10px] text-chrome-dim/50 font-mono mt-1.5 group-hover:text-plasma/70 transition-colors">
            Click to expand ↗
          </p>
        </motion.div>
      </div>
    </>
  );
}

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSessionLocal[]>([]);
  const [activeId, setActiveId] = useState("");
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [running, setRunning] = useState(false);
  const [enabledAgentKeys, setEnabledAgentKeys] = useState<string[]>(
    defaultEnabledAgentKeys,
  );
  const [activeAgentKeys, setActiveAgentKeys] = useState<string[]>([
    "orchestrator",
  ]);

  const [selectedEvent, setSelectedEvent] =
    useState<ExplainabilityEvent | null>(null);

  function setExplainabilityEvents(
    updater:
      | ExplainabilityEvent[]
      | ((prev: ExplainabilityEvent[]) => ExplainabilityEvent[]),
  ) {
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== activeId) return s;
        const next =
          typeof updater === "function"
            ? updater(s.explainabilityEvents ?? [])
            : updater;
        return { ...s, explainabilityEvents: next };
      }),
    );
  }

  const fileRef = useRef<HTMLInputElement>(null);
  const stopStreamRef = useRef<(() => void) | null>(null);
  const messagesScrollRef = useRef<HTMLDivElement>(null);
  const chatTopRef = useRef<HTMLDivElement>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const explainabilityScrollRef = useRef<HTMLDivElement>(null);
  const explainabilityTopRef = useRef<HTMLDivElement>(null);
  const explainabilityBottomRef = useRef<HTMLDivElement>(null);
  const [showChatScrollControls, setShowChatScrollControls] = useState(false);
  const [
    showExplainabilityScrollControls,
    setShowExplainabilityScrollControls,
  ] = useState(false);

  useEffect(() => {
    const loaded = loadSessions();
    setSessions(loaded);
    setActiveId(loaded[0].id);
  }, []);

  useEffect(() => {
    if (sessions.length) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    }
  }, [sessions]);

  useEffect(() => {
    return () => stopStreamRef.current?.();
  }, []);

  const activeSession =
    sessions.find((session) => session.id === activeId) ?? sessions[0];
  const messages = activeSession?.messages ?? [];

  const explainabilityEvents: ExplainabilityEvent[] =
    activeSession?.explainabilityEvents ?? [];

  const latestAgentStatus = useMemo(() => {
    const statuses: Record<string, string> = {};
    for (const event of explainabilityEvents) {
      statuses[event.agent] = event.status;
    }
    return statuses;
  }, [explainabilityEvents]);

  const activeAgents = useMemo(
    () => agentTimeline.filter((agent) => activeAgentKeys.includes(agent.key)),
    [activeAgentKeys],
  );

  const hasOverflow = (node: HTMLDivElement | null) =>
    !!node && node.scrollHeight - node.clientHeight > 8;

  const updateChatScrollControls = useCallback(() => {
    setShowChatScrollControls(hasOverflow(messagesScrollRef.current));
  }, []);

  const updateExplainabilityScrollControls = useCallback(() => {
    setShowExplainabilityScrollControls(
      hasOverflow(explainabilityScrollRef.current),
    );
  }, []);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    updateChatScrollControls();
  }, [messages.length, running, updateChatScrollControls]);

  useEffect(() => {
    explainabilityBottomRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
    updateExplainabilityScrollControls();
  }, [explainabilityEvents.length, updateExplainabilityScrollControls]);

  useEffect(() => {
    const chatNode = messagesScrollRef.current;
    const explainNode = explainabilityScrollRef.current;

    const resizeObserver = new ResizeObserver(() => {
      updateChatScrollControls();
      updateExplainabilityScrollControls();
    });

    if (chatNode) resizeObserver.observe(chatNode);
    if (explainNode) resizeObserver.observe(explainNode);

    window.addEventListener("resize", updateChatScrollControls);
    window.addEventListener("resize", updateExplainabilityScrollControls);

    updateChatScrollControls();
    updateExplainabilityScrollControls();

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", updateChatScrollControls);
      window.removeEventListener("resize", updateExplainabilityScrollControls);
    };
  }, [activeId, updateChatScrollControls, updateExplainabilityScrollControls]);

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
      setEnabledAgentKeys((prev) =>
        prev.includes("document_processor")
          ? prev
          : [...prev, "document_processor"],
      );
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

  function appendAssistant(
    content: string,
    extra?: {
      naturalResponse?: string;
      isIncidentRelevant?: boolean;
      citations?: WebCitation[];
    },
  ) {
    updateActiveSession((session) => {
      const copy = [...session.messages];
      const last = copy[copy.length - 1];

      const updated: Message = {
        role: "assistant",
        content,
        naturalResponse: extra?.naturalResponse,
        isIncidentRelevant: extra?.isIncidentRelevant,
        citations: extra?.citations,
      };

      if (
        last?.role === "assistant" &&
        last.content.startsWith("Running orchestration")
      ) {
        copy[copy.length - 1] = updated;
      } else {
        copy.push(updated);
      }

      return { ...session, messages: copy };
    });
  }

  function recordExplainabilityEvent(event: {
    agent?: string;
    step?: string;
    event: string;
    status?: string;
    detail?: unknown;
    message?: unknown;
    result?: unknown;
    data?: Record<string, unknown> | string | null;
  }) {
    const raw =
      event.data && typeof event.data === "object"
        ? (event.data as Record<string, unknown>)
        : null;

    const isError = ["error", "failed", "failure"].includes(
      (event.status ?? "").toLowerCase(),
    );
    const isComplete = ["complete", "completed", "success", "done"].includes(
      (event.status ?? "").toLowerCase(),
    );

    // Build a synthetic description for orchestrator complete when backend omits it
    const syntheticDescription =
      event.agent === "orchestrator" && event.step === "complete" && isComplete
        ? raw?.is_incident_relevant === false
          ? "Orchestration complete — query was not incident-related; a conversational reply was generated."
          : `Orchestration complete — full multi-agent pipeline finished. Completed steps: ${
              Array.isArray(raw?.completed_steps)
                ? (raw.completed_steps as string[]).join(", ")
                : "see raw data"
            }.`
        : undefined;

    const rawInput =
      (raw?.input as string | undefined) ??
      (raw?.query as string | undefined) ??
      (raw?.payload as string | undefined) ??
      null;
    const inputHint: string | null = rawInput
      ? String(rawInput).slice(0, 600) || null
      : null;

    const effectiveInputHint: string | null =
      inputHint ??
      (event.agent === "orchestrator" &&
      event.step === "complete" &&
      raw?.natural_response
        ? `Session: ${raw.session_id ?? "—"} | Incident relevant: ${raw.is_incident_relevant ?? "—"}`
        : null);

    const rawOutput =
      raw?.output ??
      raw?.primary_cause ??
      raw?.root_cause ??
      (raw?.results_count !== undefined
        ? `Found ${raw.results_count} result(s)`
        : undefined) ??
      (raw?.report_length !== undefined
        ? `Report length: ${raw.report_length} chars`
        : undefined) ??
      null;

    const syntheticOutput =
      !rawOutput &&
      event.agent === "orchestrator" &&
      event.step === "complete" &&
      isComplete
        ? `Natural response: ${String(raw?.natural_response ?? "").slice(0, 300) || "generated"} | Errors: ${
            Array.isArray(raw?.errors) && (raw.errors as unknown[]).length > 0
              ? (raw.errors as unknown[]).join("; ").slice(0, 200)
              : "none"
          }`
        : null;

    const outputHint: string | null = rawOutput
      ? String(rawOutput).slice(0, 600) || null
      : syntheticOutput;

    const detail = String(
      (raw?.description as string | undefined) ??
        syntheticDescription ??
        (raw?.message as string | undefined) ??
        (!isError ? (raw?.error as string | undefined) : undefined) ??
        event.detail ??
        event.message ??
        event.result ??
        (isError ? "Step failed — see error details below." : "Step updated"),
    ).slice(0, 600);

    const errorInfo: string | null = raw?.error
      ? String(raw.error).slice(0, 600)
      : null;

    setExplainabilityEvents((prev: ExplainabilityEvent[]) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        agent: event.agent ?? "system",
        step: event.step ?? event.event,
        status: event.status ?? "running",
        detail,
        rawData: raw,
        inputHint: effectiveInputHint,
        outputHint,
        errorInfo,
      },
    ]);
  }

  function buildStructuredText(data: Record<string, unknown>): string {
    const remediation = Array.isArray(data.remediation_steps)
      ? data.remediation_steps
      : [];
    const rollback = Array.isArray(data.rollback_steps)
      ? data.rollback_steps
      : [];
    const completed = Array.isArray(data.completed_steps)
      ? data.completed_steps
      : [];

    return [
      `Service: ${data.service ?? "unknown"}`,
      `Severity: ${data.severity ?? "unknown"}`,
      `Root cause: ${data.root_cause ?? "No root cause returned"}`,
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

    const sessionUUID = activeSession.backendSessionId ?? activeSession.id;

    updateActiveSession((session) => ({
      ...session,
      title: session.title === "New incident" ? title : session.title,
      backendSessionId: session.backendSessionId ?? session.id,
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
    setExplainabilityEvents([]);
    setActiveAgentKeys([
      "orchestrator",
      ...(documentContext ? ["document_processor"] : []),
    ]);

    if (!documentContext) {
      setEnabledAgentKeys((prev) =>
        prev.filter((k) => k !== "document_processor"),
      );
    }

    stopStreamRef.current?.();
    stopStreamRef.current = streamIncident(
      text || "Analyze uploaded document context.",
      sessionUUID,
      documentContext,
      enabledAgentKeys,
      (event) => {
        const agentKey = event.agent as string | undefined;
        const agentEnabled =
          !agentKey ||
          enabledAgentKeys.includes(agentKey) ||
          requiredAgentKeys.has(agentKey);

        if (agentKey && !agentEnabled) {
          return;
        }

        if (agentKey) {
          setActiveAgentKeys((prev) =>
            Array.from(new Set([...prev, agentKey])),
          );
        }

        if (agentKey || event.step) {
          recordExplainabilityEvent(event);
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

        if (
          event.event === "result" &&
          event.data &&
          typeof event.data === "object"
        ) {
          const data = event.data as Record<string, unknown>;
          const isIncidentRelevant = data.is_incident_relevant !== false;
          const naturalResponse =
            typeof data.natural_response === "string"
              ? data.natural_response
              : undefined;
          const citations = Array.isArray(data.web_citations)
            ? (data.web_citations as WebCitation[])
            : [];

          const structuredText = isIncidentRelevant
            ? buildStructuredText(data)
            : "";

          appendAssistant(
            structuredText || (naturalResponse ?? "Analysis complete."),
            {
              naturalResponse,
              isIncidentRelevant,
              citations: citations.length ? citations : undefined,
            },
          );
        }
      },
      (sessionId) => {
        if (sessionId) {
          updateActiveSession((session) => ({
            ...session,
            backendSessionId: sessionId,
          }));
        }
        setRunning(false);
      },
      (error) => {
        appendAssistant(`Orchestration error: ${error.message}`);
        setRunning(false);
      },
      attachments.map((a) => a.filename),
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
      {/* Explainability detail modal */}
      {selectedEvent && (
        <ExplainabilityModal
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}

      <nav className="border-b border-border-1 bg-void/80 backdrop-blur-md">
        <div className="max-w-[1880px] mx-auto px-6 h-14 flex items-center justify-between">
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
        </div>
      </nav>

      <main className="max-w-[1880px] mx-auto px-6 py-6 grid grid-cols-1 xl:grid-cols-[220px_240px_minmax(0,1fr)] 2xl:grid-cols-[220px_240px_minmax(0,1fr)_300px] gap-5">
        {/* History sidebar */}
        <HistoryPanel
          sessions={sessions}
          activeId={activeId}
          onSelect={setActiveId}
          onCreate={createNewChat}
          onDelete={deleteSession}
        />

        {/* Agents + Starters */}
        <aside className="space-y-4 h-[calc(100vh-6.5rem)] overflow-y-auto">
          <section className="bg-surface-1 border border-border-1 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-4">
              <Workflow size={16} className="text-ice" />
              <h2 className="font-display font-semibold text-sm">Agents</h2>
            </div>

            <div className="space-y-3">
              {agentTimeline.map((agent) => {
                const active = activeAgents.some((a) => a.key === agent.key);
                const enabled = enabledAgentKeys.includes(agent.key);
                const isDocumentAgent = documentOnlyAgentKeys.has(agent.key);
                const toggleDisabled =
                  requiredAgentKeys.has(agent.key) || isDocumentAgent;
                const latestStatus = latestAgentStatus[agent.key];

                return (
                  <motion.div
                    key={agent.name}
                    initial={{ opacity: 0.45 }}
                    animate={{ opacity: active ? 1 : enabled ? 0.82 : 0.38 }}
                    className="flex items-center gap-3"
                  >
                    <div className="w-8 h-8 rounded border border-border-1 bg-surface-2 flex items-center justify-center">
                      <agent.icon
                        size={14}
                        style={{ color: active ? agent.color : "#888888" }}
                      />
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-mono text-chrome truncate">
                        {agent.name}
                      </div>
                      <div className="text-[11px] font-mono text-chrome-dim truncate">
                        {agent.status}
                      </div>
                    </div>

                    {!toggleDisabled && (
                      <button
                        type="button"
                        onClick={() =>
                          setEnabledAgentKeys((prev) =>
                            prev.includes(agent.key)
                              ? prev.filter((key) => key !== agent.key)
                              : [...prev, agent.key],
                          )
                        }
                        className={`w-8 h-4 rounded-full border transition-colors ${
                          enabled
                            ? "border-plasma bg-plasma/20"
                            : "border-border-2 bg-surface-2"
                        }`}
                        title={enabled ? "Enabled" : "Disabled"}
                      >
                        <span
                          className={`block w-3 h-3 rounded-full bg-current transition-transform ${
                            enabled
                              ? "translate-x-4 text-plasma"
                              : "translate-x-0.5 text-chrome-dim"
                          }`}
                        />
                      </button>
                    )}

                    {latestStatus ? (
                      <motion.span
                        key={`${agent.key}-${latestStatus}`}
                        initial={{
                          scale: 1,
                          boxShadow: `0 0 0 0 ${statusGlowColor(latestStatus)}`,
                        }}
                        animate={{
                          scale: [1, 1.55, 1],
                          boxShadow: [
                            `0 0 0 0 ${statusGlowColor(latestStatus)}`,
                            "0 0 0 7px transparent",
                            "0 0 0 0 transparent",
                          ],
                        }}
                        transition={{ duration: 0.85, ease: "easeOut" }}
                        className={`h-2.5 w-2.5 rounded-full shrink-0 ${statusDotClass(latestStatus)}`}
                      />
                    ) : (
                      active && (
                        <CheckCircle2
                          size={13}
                          className="text-plasma shrink-0"
                        />
                      )
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

        {/* Chat panel */}
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

          <div className="relative flex-1 min-h-0">
            <ScrollControls
              show={showChatScrollControls}
              onTop={() =>
                chatTopRef.current?.scrollIntoView({
                  behavior: "smooth",
                  block: "start",
                })
              }
              onBottom={() =>
                chatBottomRef.current?.scrollIntoView({
                  behavior: "smooth",
                  block: "end",
                })
              }
              topLabel="Scroll chat to top"
              bottomLabel="Scroll chat to latest"
            />

            <div
              ref={messagesScrollRef}
              onScroll={updateChatScrollControls}
              className="h-full overflow-y-auto p-5 space-y-4"
            >
              <div ref={chatTopRef} />
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
                  {message.role === "user" ? (
                    <div className="max-w-[82%] rounded-xl bg-plasma text-void p-4 text-sm font-mono whitespace-pre-wrap">
                      {message.content}
                    </div>
                  ) : (
                    <AssistantMessage message={message} />
                  )}
                </motion.div>
              ))}
              <div ref={chatBottomRef} />
            </div>
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
            {running ? (
              <button
                type="button"
                onClick={() => {
                  stopStreamRef.current?.();
                  stopStreamRef.current = null;
                  setRunning(false);
                  updateActiveSession((session) => {
                    const copy = [...session.messages];
                    const last = copy[copy.length - 1];
                    if (
                      last?.role === "assistant" &&
                      last.content.startsWith("Running orchestration")
                    ) {
                      copy[copy.length - 1] = {
                        ...last,
                        content: "⚠ Analysis cancelled.",
                      };
                    }
                    return { ...session, messages: copy };
                  });
                }}
                className="self-end h-[52px] px-5 rounded-lg bg-red-500/20 border border-red-500/50 text-red-400 font-display font-bold hover:bg-red-500/30 transition-colors flex items-center gap-2"
              >
                <Square size={16} />
                Cancel
              </button>
            ) : (
              <button
                type="submit"
                disabled={uploading}
                className="self-end h-[52px] px-5 rounded-lg bg-plasma text-void font-display font-bold hover:bg-plasma-dim transition-colors flex items-center gap-2 disabled:opacity-60"
              >
                <Send size={16} />
                {uploading ? "Uploading" : "Analyze"}
              </button>
            )}
          </form>
        </section>

        {/* Explainability panel */}
        <aside className="hidden 2xl:flex bg-surface-1 border border-border-1 rounded-xl h-[calc(100vh-6.5rem)] flex-col overflow-hidden">
          <div className="border-b border-border-1 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <Network size={16} className="text-plasma" />
                  <h2 className="font-display font-semibold text-sm">
                    Explainability
                  </h2>
                </div>
                <p className="text-[11px] text-chrome-dim font-mono mt-1">
                  Hover for preview · Click to expand
                </p>
              </div>

              <ScrollControls
                show={showExplainabilityScrollControls}
                onTop={() =>
                  explainabilityTopRef.current?.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                  })
                }
                onBottom={() =>
                  explainabilityBottomRef.current?.scrollIntoView({
                    behavior: "smooth",
                    block: "end",
                  })
                }
                topLabel="Scroll explainability to first step"
                bottomLabel="Scroll explainability to latest step"
                inline
              />
            </div>
          </div>

          <div
            ref={explainabilityScrollRef}
            onScroll={updateExplainabilityScrollControls}
            className="flex-1 overflow-y-auto p-4 space-y-3"
          >
            <div ref={explainabilityTopRef} />
            {explainabilityEvents.length === 0 ? (
              <p className="text-xs text-chrome-dim font-mono">
                Run an incident to see graph operations and active agent work.
              </p>
            ) : (
              explainabilityEvents.map((event: ExplainabilityEvent) => (
                <ExplainabilityCard
                  key={event.id}
                  event={event}
                  onOpen={setSelectedEvent}
                />
              ))
            )}
            <div ref={explainabilityBottomRef} />
          </div>
        </aside>
      </main>
    </div>
  );
}
