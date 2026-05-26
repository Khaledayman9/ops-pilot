from .models import IncidentState


def should_skip_graph(state: IncidentState) -> bool:
    """Skip graph traversal if no service was classified."""
    return state.service is None


def should_skip_remediation(state: IncidentState) -> bool:
    """Skip remediation if root cause analysis failed."""
    return state.root_cause is None
