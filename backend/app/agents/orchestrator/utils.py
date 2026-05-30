import json
from typing import Any

from ..conversationalist.models import ChatTurn
from .models import IncidentState

_MAX_HISTORY_TURNS = 10


def should_skip_graph(state: IncidentState) -> bool:
    """Skip graph traversal if no service was classified."""
    return state.service is None


def should_skip_remediation(state: IncidentState) -> bool:
    """Skip remediation if root cause analysis failed."""
    return state.root_cause is None


def build_analysis_context(state: IncidentState) -> str:
    """Flatten key pipeline outputs into a single text block for the conversationalist."""
    parts: list[str] = []

    if state.service:
        parts.append(f"Service: {state.service}")
    if state.severity:
        parts.append(f"Severity: {state.severity}")
    if state.incident_type:
        parts.append(f"Incident type: {state.incident_type}")
    if state.root_cause:
        parts.append(f"Root cause: {state.root_cause}")
    if state.causal_chain:
        chain = "; ".join(f["factor"] for f in state.causal_chain if "factor" in f)
        parts.append(f"Causal chain: {chain}")
    if state.remediation_steps:
        steps = "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(state.remediation_steps))
        parts.append(f"Remediation steps:\n{steps}")
    if state.rollback_steps:
        steps = "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(state.rollback_steps))
        parts.append(f"Rollback steps:\n{steps}")
    if state.timeline:
        parts.append(f"Timeline: {'; '.join(state.timeline)}")
    if state.repo_scout_summary:
        parts.append(f"Repo scout: {state.repo_scout_summary[:400]}")
    if state.terraform_scout_summary:
        parts.append(f"Terraform scout: {state.terraform_scout_summary[:400]}")
    if state.ops_analyst_result:
        parts.append(f"Ops diagnostics: {state.ops_analyst_result[:400]}")

    return "\n".join(parts)


def compact_history(raw_history: list[dict]) -> list[ChatTurn]:
    """
    Convert raw stored message dicts into ChatTurn objects.
    Keeps the most recent _MAX_HISTORY_TURNS turns to stay within context limits.
    If a message contains a compacted summary marker, prefer that over the raw content.
    """
    turns: list[ChatTurn] = []
    for msg in raw_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "assistant":
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "conversation_summary" in parsed:
                    content = parsed["conversation_summary"]
                elif isinstance(parsed, list):
                    content = content[:300]
            except (json.JSONDecodeError, ValueError):
                content = content[:300]
        turns.append(ChatTurn(role=role, content=content))

    return turns[-_MAX_HISTORY_TURNS:]


def _safe_str(value: Any) -> str:
    """Convert any value into a safe string representation."""
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return str(value)


def _safe_join(value: Any) -> str:
    """Safely join lists/tuples or fallback to string."""
    if not value:
        return ""
    if isinstance(value, (list, tuple, set)):
        return ", ".join(_safe_str(v) for v in value if v is not None)
    return _safe_str(value)


def form_orchestrator_output(state: "IncidentState") -> str:
    parts = ["Orchestration Done"]

    fields = {
        "Session": state.session_id,
        "Incident Relevant": state.is_incident_relevant,
        "Classification": state.classification,
        "Severity": state.severity,
        "Service": state.service,
        "Root Cause": state.root_cause,
        "Causal Chain": state.causal_chain,
        "Conversation Summary": state.conversation_summary,
        "Natural Response": state.natural_response,
        "Document Context Chars": state.document_context_chars,
        "Repo Scout": state.repo_scout_summary,
        "Terraform Scout": state.terraform_scout_summary,
        "Ops Diagnostics": state.ops_analyst_result,
        "Remediation Steps": state.remediation_steps,
        "Rollback Steps": state.rollback_steps,
        "Escalation Paths": state.escalation_paths,
        "Runbooks": state.runbook_references,
        "Timeline": state.timeline,
        "Web Citations": state.web_citations,
        "Completed Steps": state.completed_steps,
        "Errors": state.errors,
    }

    for label, value in fields.items():
        if value in (None, "", [], {}, ()):
            continue

        formatted = _safe_join(value)

        if formatted:
            parts.append(f"{label}: {formatted}")
        else:
            parts.append(f"{label}: {_safe_str(value)}")

    graph = state.graph_context or {}

    blast_count = graph.get("blast_radius_count")
    upstream = graph.get("upstream_services")
    downstream = graph.get("downstream_services")

    if blast_count not in (None, 0, "", []):
        parts.append(f"Blast Radius: {blast_count}")

    upstream_joined = _safe_join(upstream)
    if upstream_joined:
        parts.append(f"Upstream: {upstream_joined}")

    downstream_joined = _safe_join(downstream)
    if downstream_joined:
        parts.append(f"Downstream: {downstream_joined}")

    return "\n".join(parts)
