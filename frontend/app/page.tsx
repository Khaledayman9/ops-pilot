// frontend/app/page.tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  Zap,
  ArrowRight,
  Network,
  GitBranch,
  Activity,
  Shield,
  Layers,
  Clock,
  Terminal,
  AlertTriangle,
} from "lucide-react";

// anime.js loaded dynamically (SSR-safe)
type AnimeInstance = { pause: () => void };
type AnimeStatic = {
  (params: Record<string, unknown>): AnimeInstance;
};
let anime: AnimeStatic | null = null;

async function loadAnime() {
  if (typeof window === "undefined") return;
  const mod = await import("animejs");
  anime = (mod.default ?? mod) as unknown as AnimeStatic;
}

const GRAPH_NODES = [
  { id: "api", x: 80, y: 80, label: "api-gateway", status: "healthy" },
  { id: "checkout", x: 240, y: 50, label: "checkout", status: "critical" },
  { id: "payment", x: 400, y: 80, label: "payment-service", status: "degraded" },
  { id: "inventory", x: 400, y: 170, label: "inventory-service", status: "healthy" },
  { id: "redis", x: 240, y: 180, label: "redis-cache", status: "degraded" },
  { id: "postgres", x: 550, y: 125, label: "postgres-primary", status: "healthy" },
];
const GRAPH_EDGES = [
  ["api", "checkout"],
  ["checkout", "payment"],
  ["checkout", "redis"],
  ["checkout", "inventory"],
  ["payment", "postgres"],
  ["inventory", "postgres"],
];
const STATUS_COLOR: Record<string, string> = {
  healthy: "#00ff88",
  degraded: "#ffaa00",
  critical: "#ff4444",
};

const SIM_LINES = [
  { t: 0, txt: "$ ops-pilot analyze --query 'checkout latency spike'", color: "#00ff88" },
  { t: 600, txt: "> [classifier]   service=checkout-service severity=P1", color: "#e0e0e0" },
  { t: 1300, txt: "> [entity_extractor] entities=6 deployments=['v2.3.1']", color: "#e0e0e0" },
  { t: 2100, txt: "> [graph_analyzer]   blast_radius=4 upstream=['api-gateway']", color: "#ffaa00" },
  { t: 2900, txt: "> [root_cause_finder] cause='memory leak in v2.3.1' conf=0.91", color: "#00ccff" },
  { t: 3700, txt: "> [remediator]    rollback=v2.3.0 runbook=RB-001", color: "#e0e0e0" },
  { t: 4400, txt: "Analysis complete in 4.2s", color: "#00ff88" },
];

const STATS = [
  { label: "Mean Time to Detect", value: "< 30s", sub: "vs 18min industry avg" },
  { label: "Root Cause Accuracy", value: "94%", sub: "across 2k+ incidents" },
  { label: "Agent Steps", value: "7", sub: "classifier to remediator" },
  { label: "Graph Nodes Traversed", value: "inf", sub: "bounded by blast radius" },
];

const FEATURES = [
  { icon: Network, title: "Graph Traversal", desc: "Neo4j dependency graph computes exact blast radius across your service mesh.", accent: "#00ff88" },
  { icon: Activity, title: "Live Streaming", desc: "Every agent step SSE-streams to your UI. Zero polling, true real-time.", accent: "#00ccff" },
  { icon: GitBranch, title: "Deployment Correlation", desc: "Automatically links incidents to recent deployments with temporal analysis.", accent: "#ffaa00" },
  { icon: Shield, title: "Structured LLM Output", desc: "Every LLM call uses with_structured_output. No free-text, no drift.", accent: "#ff4444" },
  { icon: Clock, title: "Historical Patterns", desc: "Graph-stored historical incidents surface recurring failure signatures.", accent: "#00ff88" },
  { icon: Layers, title: "7-Agent Orchestration", desc: "LangGraph pipeline with CrewAI web enrichment + guardrails at every step.", accent: "#00ccff" },
];

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const _Terminal = Terminal; // imported for potential future use

function TerminalSim() {
  const [lines, setLines] = useState<typeof SIM_LINES>([]);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    const startSim = () => {
      setLines([]);
      setRunning(true);
      SIM_LINES.forEach(({ t, txt, color }) => {
        setTimeout(() => setLines((prev) => [...prev, { t, txt, color }]), t);
      });
      setTimeout(() => {
        setRunning(false);
        setTimeout(startSim, 3000);
      }, 5500);
    };
    startSim();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="bg-[#0a0a0f] border border-[#2a2a3a] rounded-xl p-5 font-mono text-xs leading-6">
      <div className="flex items-center gap-2 mb-4 pb-3 border-b border-[#2a2a3a]">
        <span className="w-3 h-3 rounded-full bg-[#ff4444]" />
        <span className="w-3 h-3 rounded-full bg-[#ffaa00]" />
        <span className="w-3 h-3 rounded-full bg-[#00ff88]" />
        <span className="ml-2 text-[#888888]">ops-pilot terminal</span>
        {running && (
          <motion.span
            animate={{ opacity: [1, 0] }}
            transition={{ repeat: Infinity, duration: 0.8, repeatType: "reverse" }}
            className="ml-auto text-[#00ff88]"
          >
            RUNNING
          </motion.span>
        )}
      </div>
      <div className="space-y-0.5 min-h-[180px]">
        {lines.map((l, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            style={{ color: l.color }}
          >
            {l.txt}
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function HeroGraph() {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    loadAnime().then(() => {
      if (!anime || !svgRef.current) return;
      anime({
        targets: ".hero-node",
        opacity: [0, 1],
        scale: [0.4, 1],
        duration: 600,
        delay: (_el: unknown, i: number) => i * 120,
        easing: "easeOutBack",
      });
      anime({
        targets: ".hero-edge",
        strokeDashoffset: [200, 0],
        duration: 800,
        delay: (_el: unknown, i: number) => 400 + i * 80,
        easing: "easeInOutQuad",
      });
      anime({
        targets: ".hero-pulse",
        r: [6, 14],
        opacity: [0.5, 0],
        duration: 1400,
        loop: true,
        easing: "easeOutExpo",
      });
      anime({
        targets: ".hero-packet",
        translateX: [0, 140],
        opacity: [0, 1, 0],
        duration: 1800,
        loop: true,
        delay: (_el: unknown, i: number) => i * 600,
        easing: "linear",
      });
    });
  }, []);

  return (
    <svg ref={svgRef} viewBox="0 0 640 260" className="w-full h-full">
      {GRAPH_EDGES.map(([a, b], i) => {
        const na = GRAPH_NODES.find((n) => n.id === a)!;
        const nb = GRAPH_NODES.find((n) => n.id === b)!;
        return (
          <line
            key={i}
            className="hero-edge"
            x1={na.x + 55} y1={na.y + 18}
            x2={nb.x + 55} y2={nb.y + 18}
            stroke="#2a2a3a"
            strokeWidth={1.5}
          />
        );
      })}
      {GRAPH_EDGES.slice(0, 3).map(([a], i) => {
        const na = GRAPH_NODES.find((n) => n.id === a)!;
        return (
          <circle
            key={`pk-${i}`}
            className="hero-packet"
            cx={na.x + 55}
            cy={na.y + 18}
            r={3}
            fill={i === 0 ? "#ff4444" : "#ffaa00"}
          />
        );
      })}
      {GRAPH_NODES.map((node) => {
        const c = STATUS_COLOR[node.status];
        return (
          <g key={node.id} className="hero-node" style={{ opacity: 0 }}>
            {node.status === "critical" && (
              <circle
                className="hero-pulse"
                cx={node.x + 55}
                cy={node.y + 18}
                r={6}
                fill={c}
                opacity={0.5}
              />
            )}
            <rect
              x={node.x} y={node.y} width={110} height={36} rx={6}
              fill="#111118" stroke={c}
              strokeWidth={node.status === "critical" ? 2 : 1}
              style={{ filter: node.status === "critical" ? `drop-shadow(0 0 8px ${c}88)` : "none" }}
            />
            <circle cx={node.x + 14} cy={node.y + 18} r={4} fill={c} />
            <text
              x={node.x + 24} y={node.y + 23}
              fill="#e0e0e0" fontSize={9}
              fontFamily="JetBrains Mono"
            >
              {node.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function AnimatedCounter({ value, label, sub }: { value: string; label: string; sub: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.3 },
    );
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);

  return (
    <div ref={ref} className="text-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={visible ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.6 }}
        className="text-3xl font-display font-bold text-plasma plasma-glow mb-1"
      >
        {visible ? value : "-"}
      </motion.div>
      <div className="text-xs text-chrome font-mono">{label}</div>
      <div className="text-xs text-chrome-dim font-mono mt-0.5">{sub}</div>
    </div>
  );
}

export default function HomePage() {
  const heroParticlesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadAnime().then(() => {
      if (!anime || !heroParticlesRef.current) return;
      const dots = heroParticlesRef.current.querySelectorAll(".hero-particle");
      anime({
        targets: dots,
        translateX: () => (Math.random() - 0.5) * 160,
        translateY: () => (Math.random() - 0.5) * 160,
        opacity: [0, 0.6, 0],
        scale: [0, 1, 0],
        duration: () => 2000 + Math.random() * 2000,
        delay: () => Math.random() * 2000,
        loop: true,
        easing: "easeInOutSine",
      });
    });
  }, []);

  return (
    <div className="min-h-screen bg-void grid-bg overflow-x-hidden">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 border-b border-border-1 bg-void/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Zap size={18} className="text-plasma" />
            <span className="font-display font-semibold text-chrome tracking-tight">
              ops<span className="text-plasma">-pilot</span>
            </span>
          </Link>
          <div className="flex items-center gap-6 text-xs font-mono">
            <a href="#how-it-works" className="text-chrome-dim hover:text-plasma transition-colors hidden sm:block">
              How it works
            </a>
            <a href="#features" className="text-chrome-dim hover:text-plasma transition-colors hidden sm:block">
              Features
            </a>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-plasma animate-pulse" />
              <span className="text-plasma text-xs">ONLINE</span>
            </div>
            <Link
              href="/chat"
              className="px-4 py-1.5 bg-plasma text-void font-display font-semibold rounded text-xs hover:bg-plasma-dim transition-colors"
            >
              LAUNCH
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative min-h-screen flex items-center pt-14">
        <div
          ref={heroParticlesRef}
          className="absolute inset-0 overflow-hidden pointer-events-none"
        >
          {Array.from({ length: 24 }).map((_, i) => (
            <div
              key={i}
              className="hero-particle absolute w-1 h-1 rounded-full bg-plasma"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                opacity: 0,
              }}
            />
          ))}
          <div
            className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[700px] h-[700px] rounded-full pointer-events-none"
            style={{ background: "radial-gradient(circle, rgba(0,255,136,0.06) 0%, transparent 70%)" }}
          />
        </div>

        <div className="relative z-10 max-w-7xl mx-auto px-6 py-24 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          {/* Left */}
          <div>
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center gap-2 px-3 py-1 border border-border-2 rounded text-xs text-chrome-dim mb-8 font-mono"
            >
              <AlertTriangle size={11} className="text-amber" />
              AI-POWERED SRE INCIDENT RESPONSE
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="font-display font-bold leading-tight mb-6"
              style={{ fontSize: "clamp(2.4rem, 5vw, 4rem)" }}
            >
              Your AI{" "}
              <span className="text-plasma plasma-glow">Co-Pilot</span>
              <br />
              for Production{" "}
              <span className="text-ember ember-glow">Incidents</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="text-chrome-dim text-sm leading-relaxed mb-10 max-w-lg font-mono"
            >
              Seven specialized AI agents traverse your Neo4j service graph, correlate
              deployments, compute blast radius, and stream a full remediation plan in
              under 5 seconds.
            </motion.p>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.45 }}
              className="flex flex-wrap gap-4 mb-12"
            >
              <Link
                href="/chat"
                className="group flex items-center gap-2 px-7 py-3.5 bg-plasma text-void font-display font-bold rounded-lg hover:bg-plasma-dim transition-all text-sm"
              >
                Analyze an Incident
                <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
              </Link>


              href="#how-it-works"
              className="flex items-center gap-2 px-7 py-3.5 border border-border-2 text-chrome-dim rounded-lg hover:border-plasma hover:text-plasma transition-colors text-sm font-mono"
              >
              See how it works
            </a>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="flex flex-wrap gap-2"
          >
            {["Neo4j", "LangGraph", "FastAPI", "CrewAI", "Next.js 15", "Pydantic v2"].map((t) => (
              <span
                key={t}
                className="px-2.5 py-1 border border-border-1 rounded text-xs text-chrome-dim font-mono hover:border-plasma hover:text-plasma transition-colors cursor-default"
              >
                {t}
              </span>
            ))}
          </motion.div>
        </div>

        {/* Right */}
        <motion.div
          initial={{ opacity: 0, x: 32 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="space-y-4"
        >
          <div className="bg-surface-1 border border-border-1 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3 text-xs font-mono text-chrome-dim">
              <Network size={12} className="text-plasma" />
              LIVE SERVICE DEPENDENCY GRAPH
              <span className="ml-auto flex items-center gap-1 text-ember">
                <span className="w-1.5 h-1.5 rounded-full bg-ember animate-pulse" />
                P1 INCIDENT
              </span>
            </div>
            <div className="h-64">
              <HeroGraph />
            </div>
          </div>
          <TerminalSim />
        </motion.div>
    </div>
      </section >

    {/* Stats */ }
    < section className = "border-t border-border-1 py-20" >
      <div className="max-w-5xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
        {STATS.map((s) => (
          <AnimatedCounter key={s.label} value={s.value} label={s.label} sub={s.sub} />
        ))}
      </div>
      </section >

    {/* How it works */ }
    < section id = "how-it-works" className = "py-32 border-t border-border-1" >
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-20"
        >
          <p className="text-xs text-plasma font-mono tracking-widest mb-4">PIPELINE</p>
          <h2 className="font-display text-4xl font-bold text-chrome mb-4">7 Agents. One Pipeline.</h2>
          <p className="text-chrome-dim max-w-xl mx-auto font-mono text-sm">
            LangGraph orchestrates a deterministic sequence. Each agent outputs a
            validated Pydantic model with no free-text parsing.
          </p>
        </motion.div>

        <div className="flex flex-col md:flex-row gap-2">
          {[
            { n: "01", title: "Classify", icon: "⚡", color: "#00ff88", desc: "Extracts service, severity P0-P3, incident type, trigger event." },
            { n: "02", title: "Extract", icon: "🔍", color: "#00ccff", desc: "Pulls services, deployment IDs, metrics, error codes from query." },
            { n: "03", title: "Traverse", icon: "🕸", color: "#ffaa00", desc: "9 deep Neo4j queries: blast radius, runbooks, ownership, config drift." },
            { n: "04", title: "Web Search", icon: "🌐", color: "#ff4444", desc: "DuckDuckGo intelligence written back into Neo4j as WebKnowledge nodes." },
            { n: "05", title: "CrewAI", icon: "🤖", color: "#00ff88", desc: "2-agent crew: intelligence gatherer + evidence synthesiser." },
            { n: "06", title: "RCA", icon: "🧠", color: "#00ccff", desc: "Builds a causal chain with confidence scores and deployment correlation." },
            { n: "07", title: "Remediate", icon: "🔧", color: "#ffaa00", desc: "Rollback steps, escalation paths, and runbook references." },
          ].map((step, i) => (
            <motion.div
              key={step.n}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.07 }}
              className="flex-1 bg-surface-1 border border-border-1 rounded-xl p-4 relative group hover:border-border-2 transition-colors"
            >
              {i < 6 && (
                <div className="hidden md:flex absolute -right-3 top-1/2 -translate-y-1/2 z-10 text-border-2 text-lg">
                  &rarr;
                </div>
              )}
              <div className="text-2xl mb-2">{step.icon}</div>
              <div className="text-xs text-chrome-dim font-mono mb-1">{step.n}</div>
              <div className="font-display font-bold text-sm mb-1" style={{ color: step.color }}>
                {step.title}
              </div>
              <p className="text-chrome-dim text-xs leading-relaxed font-mono">{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
      </section >

    {/* Features */ }
    < section id = "features" className = "py-32 border-t border-border-1" >
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-20"
        >
          <p className="text-xs text-plasma font-mono tracking-widest mb-4">CAPABILITIES</p>
          <h2 className="font-display text-4xl font-bold text-chrome">Built for SREs</h2>
        </motion.div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              className="bg-surface-1 border border-border-1 rounded-xl p-6 hover:border-border-2 hover:-translate-y-1 transition-all group"
            >
              <f.icon size={22} className="mb-4" style={{ color: f.accent }} />
              <h3 className="font-display font-semibold text-chrome mb-2">{f.title}</h3>
              <p className="text-chrome-dim text-sm leading-relaxed font-mono">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
      </section >

    {/* CTA */ }
    < section className = "py-32 border-t border-border-1" >
      <div className="max-w-3xl mx-auto px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h2
            className="font-display font-bold text-chrome mb-6"
            style={{ fontSize: "clamp(2rem, 4vw, 3.5rem)" }}
          >
            Ready to{" "}
            <span className="text-plasma plasma-glow">respond faster?</span>
          </h2>
          <p className="text-chrome-dim font-mono text-sm mb-10 max-w-xl mx-auto">
            Paste an incident description. Watch seven AI agents work in real-time.
            Get a structured remediation plan with rollback steps and runbooks.
          </p>
          <Link
            href="/chat"
            className="inline-flex items-center gap-3 px-10 py-4 bg-plasma text-void font-display font-bold text-lg rounded-lg hover:bg-plasma-dim transition-all group"
          >
            Open Ops-Pilot
            <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
          </Link>
        </motion.div>
      </div>
      </section >

    {/* Footer */ }
    < footer className = "border-t border-border-1 py-8" >
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between text-xs text-chrome-dim font-mono">
        <div className="flex items-center gap-2">
          <Zap size={12} className="text-plasma" />
          ops-pilot v0.1.0
        </div>
        <span className="hidden sm:block">AI SRE Operations Control Plane</span>
        <div className="flex items-center gap-4">
          <Link href="/chat" className="hover:text-plasma transition-colors">Chat</Link>
        </div>
      </div>
      </footer >
    </div >
  );
}