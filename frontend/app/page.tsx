"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Brain,
  Cpu,
  FileSearch,
  GitBranch,
  HelpCircle,
  Mail,
  Network,
  Radar,
  ScanSearch,
  FileText,
  Shield,
  Sparkles,
  Terminal,
  Workflow,
  Wrench,
} from "lucide-react";
import NavBar from "./components/NavBar";
import PageFooter from "./components/PageFooter";

type AnimeInstance = { pause: () => void };
type AnimeStatic = { (params: Record<string, unknown>): AnimeInstance };

let anime: AnimeStatic | null = null;

async function loadAnime() {
  if (typeof window === "undefined") return;
  const mod = await import("animejs");
  anime = (mod.default ?? mod) as unknown as AnimeStatic;
}

const graphNodes = [
  { id: "api", x: 80, y: 80, label: "api-gateway", status: "healthy" },
  { id: "checkout", x: 240, y: 50, label: "checkout", status: "critical" },
  {
    id: "payment",
    x: 400,
    y: 80,
    label: "payment-service",
    status: "degraded",
  },
  {
    id: "inventory",
    x: 400,
    y: 170,
    label: "inventory-service",
    status: "healthy",
  },
  { id: "redis", x: 240, y: 180, label: "redis-cache", status: "degraded" },
  {
    id: "postgres",
    x: 550,
    y: 125,
    label: "postgres-primary",
    status: "healthy",
  },
];

const graphEdges = [
  ["api", "checkout"],
  ["checkout", "payment"],
  ["checkout", "redis"],
  ["checkout", "inventory"],
  ["payment", "postgres"],
  ["inventory", "postgres"],
];

const statusColor: Record<string, string> = {
  healthy: "#00ff88",
  degraded: "#ffaa00",
  critical: "#ff4444",
};

const simLines = [
  {
    t: 0,
    txt: "$ ops-pilot analyze --query 'checkout latency spike'",
    color: "#00ff88",
  },
  {
    t: 450,
    txt: "> [orchestrator] route=incident_graph priority=P1",
    color: "#00ccff",
  },
  {
    t: 900,
    txt: "> [classifier] service=checkout-service severity=P1",
    color: "#e0e0e0",
  },
  {
    t: 1350,
    txt: "> [entity_extractor] entities=6 deployment=v2.3.1",
    color: "#e0e0e0",
  },
  {
    t: 1850,
    txt: "> [repo_scanner] suspect_commit=9f32c1 owner=payments",
    color: "#ffaa00",
  },
  {
    t: 2350,
    txt: "> [terraform_scanner] drift=iam_policy workspace=prod-us",
    color: "#00ccff",
  },
  {
    t: 2850,
    txt: "> [ops_analyst] cpu=91% latency_p95=4.8s error_rate=12%",
    color: "#ffaa00",
  },
  {
    t: 3350,
    txt: "> [web_intelligence] provider_status=nominal advisories=1",
    color: "#ff4444",
  },
  {
    t: 3850,
    txt: "> [graph_analyzer] blast_radius=4 upstream=api-gateway",
    color: "#ffaa00",
  },
  {
    t: 4450,
    txt: "> [root_cause_analyzer] cause='memory leak plus config drift' confidence=0.91",
    color: "#00ff88",
  },
  {
    t: 5100,
    txt: "> [remediator] rollback=v2.3.0 runbook=RB-001",
    color: "#e0e0e0",
  },
  { t: 5700, txt: "Analysis complete in 5.7s", color: "#00ff88" },
];

const stats = [
  {
    label: "Agents Coordinated",
    value: "12",
    sub: "orchestrator plus specialists",
  },
  {
    label: "Mean Time to Detect",
    value: "< 30s",
    sub: "from signal to triage",
  },
  {
    label: "Root Cause Confidence",
    value: "91%",
    sub: "evidence weighted output",
  },
  {
    label: "Graph Nodes Traversed",
    value: "inf",
    sub: "bounded by blast radius",
  },
];

const agents = [
  {
    name: "Orchestrator",
    icon: Workflow,
    color: "#00ccff",
    role: "Owns the run, chooses the next agent, merges evidence, and stops loops when confidence is high enough.",
  },
  {
    name: "Conversationalist",
    icon: Sparkles,
    color: "#c084fc",
    role: "Produces the natural-language reply for every turn — synthesising structured pipeline output into an empathetic, actionable explanation for non-incident queries too.",
  },
  {
    name: "Classifier",
    icon: Radar,
    color: "#00ff88",
    role: "Classifies severity, service, incident type, and urgency from the incoming incident text.",
  },
  {
    name: "Entity Extractor",
    icon: ScanSearch,
    color: "#00ccff",
    role: "Extracts services, deployments, logs, metric names, owners, runbooks, and timestamps.",
  },
  {
    name: "Document Processor",
    icon: FileText,
    color: "#00ff88",
    role: "Converts PDF, DOCX, PPTX, HTML, Excel, CSV, Markdown, and text",
  },
  {
    name: "Graph Analyzer",
    icon: Network,
    color: "#ffaa00",
    role: "Queries Neo4j for dependencies, upstream/downstream blast radius, owners, and known runbooks.",
  },
  {
    name: "Repo Scanner",
    icon: GitBranch,
    color: "#00ff88",
    role: "Inspects recent commits, PRs, releases, and deployment metadata for suspicious changes.",
  },
  {
    name: "Terraform Scanner",
    icon: Wrench,
    color: "#00ccff",
    role: "Uses Terraform MCP context to inspect workspaces, plans, drift, state signals, and infrastructure changes.",
  },
  {
    name: "Ops Analyst",
    icon: Activity,
    color: "#ffaa00",
    role: "Reads operational telemetry patterns such as latency, saturation, error rate, and resource pressure.",
  },
  {
    name: "Web Intelligence",
    icon: FileSearch,
    color: "#ff4444",
    role: "Collects external signals such as provider incidents, CVEs, and dependency advisories.",
  },
  {
    name: "Crew Intelligence",
    icon: Sparkles,
    color: "#00ccff",
    role: "Synthesizes external intelligence and supporting evidence into a concise incident enrichment report.",
  },
  {
    name: "Root Cause Analyzer",
    icon: Brain,
    color: "#00ccff",
    role: "Builds the causal chain. This is what RCA means: root cause analysis, not a separate product.",
  },
  {
    name: "Remediator",
    icon: Shield,
    color: "#00ff88",
    role: "Generates rollback steps, mitigation commands, owner escalation, validation checks, and runbook links.",
  },
];

const features = [
  {
    icon: Workflow,
    title: "Orchestrated Agent Routing",
    desc: "The orchestrator decides which specialist runs next and carries forward structured state.",
    accent: "#00ccff",
  },
  {
    icon: Network,
    title: "Service Graph Reasoning",
    desc: "Neo4j dependency traversal explains blast radius instead of guessing from logs alone.",
    accent: "#00ff88",
  },
  {
    icon: GitBranch,
    title: "Repo and Deployment Correlation",
    desc: "Repo Scanner connects recent code changes to incident symptoms and owners.",
    accent: "#ffaa00",
  },
  {
    icon: Wrench,
    title: "Terraform MCP Inspection",
    desc: "Terraform Scanner checks infrastructure context, drift, plans, workspaces, and IaC changes alongside app signals.",
    accent: "#00ccff",
  },
  {
    icon: Activity,
    title: "Ops Telemetry Analysis",
    desc: "Ops Analyst compares latency, errors, saturation, and resource pressure against the incident timeline.",
    accent: "#ff4444",
  },
  {
    icon: Terminal,
    title: "Live Agent Streaming",
    desc: "Each step can stream to the UI so operators see evidence while the system reasons.",
    accent: "#00ccff",
  },
  {
    icon: Shield,
    title: "Actionable Remediation",
    desc: "The final answer includes rollback, mitigation, escalation, and verification steps.",
    accent: "#00ff88",
  },
  {
    icon: Cpu,
    title: "Runtime LLM Settings",
    desc: "Operators can switch providers, models, API keys, and compatible base URLs without rebuilding the backend.",
    accent: "#7c5cff",
  },
];

const orchestrationSteps = [
  "Incident enters the Orchestrator",
  "Classifier and Entity Extractor normalize the request",
  "Document Processor adds uploaded evidence when files exist",
  "Repo Scanner, Terraform Scanner, Graph Analyzer, Ops Analyst, and Web Intelligence collect evidence",
  "Root Cause Analyzer weighs evidence, Remediator produces the action plan, and Conversationalist narrates the final operator-ready response",
];

const particlePositions = [
  { left: "8%", top: "18%" },
  { left: "14%", top: "72%" },
  { left: "21%", top: "34%" },
  { left: "28%", top: "84%" },
  { left: "33%", top: "12%" },
  { left: "39%", top: "59%" },
  { left: "45%", top: "27%" },
  { left: "51%", top: "76%" },
  { left: "57%", top: "16%" },
  { left: "63%", top: "45%" },
  { left: "69%", top: "88%" },
  { left: "74%", top: "23%" },
  { left: "79%", top: "63%" },
  { left: "84%", top: "38%" },
  { left: "89%", top: "79%" },
  { left: "94%", top: "14%" },
];

function TerminalSim() {
  const [lines, setLines] = useState<typeof simLines>([]);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    let restartTimer: ReturnType<typeof setTimeout>;
    const lineTimers: ReturnType<typeof setTimeout>[] = [];

    const startSim = () => {
      setLines([]);
      setRunning(true);

      simLines.forEach(({ t, txt, color }) => {
        lineTimers.push(
          setTimeout(() => setLines((p) => [...p, { t, txt, color }]), t),
        );
      });

      restartTimer = setTimeout(() => {
        setRunning(false);
        restartTimer = setTimeout(startSim, 3000);
      }, 6200);
    };

    startSim();

    return () => {
      lineTimers.forEach(clearTimeout);
      clearTimeout(restartTimer);
    };
  }, []);

  return (
    <div className="bg-[#0a0a0f] border border-[#2a2a3a] rounded-xl p-5 font-mono text-xs leading-6">
      <div className="flex items-center gap-2 mb-4 pb-3 border-b border-[#2a2a3a]">
        <span className="w-3 h-3 rounded-full bg-[#ff4444]" />
        <span className="w-3 h-3 rounded-full bg-[#ffaa00]" />
        <span className="w-3 h-3 rounded-full bg-[#00ff88]" />
        <span className="ml-2 text-[#888888]">orchestrator stream</span>
        {running && (
          <span className="ml-auto text-[#00ff88] animate-pulse">RUNNING</span>
        )}
      </div>

      <div className="space-y-0.5 min-h-[230px]">
        {lines.map((line, i) => (
          <motion.div
            key={`${line.t}-${i}`}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            style={{ color: line.color }}
          >
            {line.txt}
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
    });
  }, []);

  return (
    <svg ref={svgRef} viewBox="0 0 640 260" className="w-full h-full">
      {graphEdges.map(([a, b], i) => {
        const na = graphNodes.find((n) => n.id === a)!;
        const nb = graphNodes.find((n) => n.id === b)!;

        return (
          <line
            key={`${a}-${b}-${i}`}
            className="hero-edge"
            x1={na.x + 55}
            y1={na.y + 18}
            x2={nb.x + 55}
            y2={nb.y + 18}
            stroke="#2a2a3a"
            strokeWidth={1.5}
          />
        );
      })}

      {graphNodes.map((node) => {
        const color = statusColor[node.status];

        return (
          <g key={node.id} className="hero-node" style={{ opacity: 0 }}>
            {node.status === "critical" && (
              <circle
                className="hero-pulse"
                cx={node.x + 55}
                cy={node.y + 18}
                r={6}
                fill={color}
                opacity={0.5}
              />
            )}
            <rect
              x={node.x}
              y={node.y}
              width={110}
              height={36}
              rx={6}
              fill="#111118"
              stroke={color}
              strokeWidth={node.status === "critical" ? 2 : 1}
              style={{
                filter:
                  node.status === "critical"
                    ? `drop-shadow(0 0 8px ${color}88)`
                    : "none",
              }}
            />
            <circle cx={node.x + 14} cy={node.y + 18} r={4} fill={color} />
            <text
              x={node.x + 24}
              y={node.y + 23}
              fill="#e0e0e0"
              fontSize={9}
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

function AnimatedCounter({
  value,
  label,
  sub,
}: {
  value: string;
  label: string;
  sub: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setVisible(true);
      },
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
      <NavBar variant="home" />

      <section className="relative min-h-screen flex items-center pt-14">
        <div
          ref={heroParticlesRef}
          className="absolute inset-0 overflow-hidden pointer-events-none"
        >
          {particlePositions.map((particle, i) => (
            <div
              key={i}
              className="hero-particle absolute w-1 h-1 rounded-full bg-plasma"
              style={{ left: particle.left, top: particle.top, opacity: 0 }}
            />
          ))}
          <div
            className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[700px] h-[700px] rounded-full pointer-events-none"
            style={{
              background:
                "radial-gradient(circle, rgba(0,255,136,0.06) 0%, transparent 70%)",
            }}
          />
        </div>

        <div className="relative z-10 max-w-7xl mx-auto px-6 py-24 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
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
              Your AI <span className="text-plasma plasma-glow">Co-Pilot</span>
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
              Ops-Pilot uses an orchestrator plus eleven specialist agents to
              classify incidents, process documents, scan repositories, inspect
              Terraform context, read telemetry, traverse the service graph,
              explain root cause, produce remediation steps, and narrate the
              final response conversationally.
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
                <ArrowRight
                  size={16}
                  className="group-hover:translate-x-1 transition-transform"
                />
              </Link>

              <a
                href="#capabilities"
                className="flex items-center gap-2 px-7 py-3.5 border border-border-2 text-chrome-dim rounded-lg hover:border-plasma hover:text-plasma transition-colors text-sm font-mono"
              >
                See capabilities
              </a>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
              className="flex flex-wrap gap-2"
            >
              {[
                "Orchestrator",
                "Repo Scanner",
                "Terraform Scanner",
                "Ops Analyst",
                "Neo4j",
                "LangGraph",
                "FastAPI",
                "Next.js 15",
              ].map((t) => (
                <span
                  key={t}
                  className="px-2.5 py-1 border border-border-1 rounded text-xs text-chrome-dim font-mono hover:border-plasma hover:text-plasma transition-colors cursor-default"
                >
                  {t}
                </span>
              ))}
            </motion.div>
          </div>

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
      </section>

      <section className="border-t border-border-1 py-20">
        <div className="max-w-5xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((s) => (
            <AnimatedCounter
              key={s.label}
              value={s.value}
              label={s.label}
              sub={s.sub}
            />
          ))}
        </div>
      </section>

      <section
        id="orchestration"
        className="py-32 border-t border-border-1 scroll-mt-16"
      >
        <div className="max-w-7xl mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <p className="text-xs text-plasma font-mono tracking-widest mb-4">
              ORCHESTRATION
            </p>
            <h2 className="font-display text-4xl font-bold text-chrome mb-4">
              Orchestrator-led incident workflow
            </h2>
            <p className="text-chrome-dim max-w-2xl mx-auto font-mono text-sm">
              The orchestrator is the control plane. It creates the plan, calls
              specialist agents, merges their evidence, and decides when the
              answer is ready.
            </p>
          </motion.div>

          <div className="space-y-6">
            <motion.div
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="bg-surface-1 border border-border-1 rounded-xl p-6"
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-lg border border-ice/50 bg-ice/10 flex items-center justify-center">
                  <Workflow size={22} className="text-ice" />
                </div>
                <div>
                  <h3 className="font-display font-bold text-chrome">
                    Orchestrator
                  </h3>
                  <p className="text-xs text-chrome-dim font-mono">
                    state router and evidence merger
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                {orchestrationSteps.map((step, i) => (
                  <div
                    key={step}
                    className="border border-border-1 bg-surface-2 rounded-lg p-4 min-h-[112px]"
                  >
                    <span className="w-7 h-7 rounded border border-border-2 text-plasma text-xs font-mono flex items-center justify-center mb-3">
                      {i + 1}
                    </span>
                    <p className="text-xs text-chrome-dim font-mono leading-relaxed">
                      {step}
                    </p>
                  </div>
                ))}
              </div>
            </motion.div>

            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
              {agents
                .filter((a) => a.name !== "Orchestrator")
                .map((agent, i) => (
                  <motion.div
                    key={agent.name}
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.04 }}
                    className="bg-surface-1 border border-border-1 rounded-xl p-5 hover:border-border-2 transition-colors min-h-[220px] flex flex-col"
                  >
                    <agent.icon
                      size={22}
                      className="mb-4 shrink-0"
                      style={{ color: agent.color }}
                    />
                    <h3 className="font-display font-semibold text-chrome mb-2 min-h-[44px]">
                      {agent.name}
                    </h3>
                    <p className="text-chrome-dim text-xs leading-relaxed font-mono">
                      {agent.role}
                    </p>
                  </motion.div>
                ))}
            </div>
          </div>
        </div>
      </section>

      <section
        id="capabilities"
        className="py-32 border-t border-border-1 scroll-mt-16"
      >
        <div className="max-w-7xl mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-20"
          >
            <p className="text-xs text-plasma font-mono tracking-widest mb-4">
              CAPABILITIES
            </p>
            <h2 className="font-display text-4xl font-bold text-chrome">
              Built for SREs and incident commanders
            </h2>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                className="bg-surface-1 border border-border-1 rounded-xl p-6 hover:border-border-2 hover:-translate-y-1 transition-all"
              >
                <feature.icon
                  size={22}
                  className="mb-4"
                  style={{ color: feature.accent }}
                />
                <h3 className="font-display font-semibold text-chrome mb-2">
                  {feature.title}
                </h3>
                <p className="text-chrome-dim text-sm leading-relaxed font-mono">
                  {feature.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-24 border-t border-border-1">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            {
              icon: HelpCircle,
              title: "Need setup help?",
              href: "/help",
              text: "View the operator guide and troubleshooting notes.",
            },
            {
              icon: Mail,
              title: "Contact the team",
              href: "/contact",
              text: "Share integration details, support requests, or feedback.",
            },
            {
              icon: Sparkles,
              title: "Start analysis",
              href: "/chat",
              text: "Open the chat workspace and run an incident through the pipeline.",
            },
          ].map((item) => (
            <Link
              key={item.title}
              href={item.href}
              className="bg-surface-1 border border-border-1 rounded-xl p-6 hover:border-plasma transition-colors group"
            >
              <item.icon size={22} className="text-plasma mb-4" />
              <h3 className="font-display font-semibold text-chrome mb-2">
                {item.title}
              </h3>
              <p className="text-chrome-dim text-sm font-mono leading-relaxed">
                {item.text}
              </p>
            </Link>
          ))}
        </div>
      </section>

      <PageFooter />
    </div>
  );
}
