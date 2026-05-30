import json

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
