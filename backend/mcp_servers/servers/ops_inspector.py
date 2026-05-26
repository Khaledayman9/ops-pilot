"""
Ops Inspector MCP Server.

Custom tools for incident diagnostics:
  - parse_stack_trace      : extract key frames from raw exception text
  - calculate_error_rate   : compute error rate % and severity label
  - format_incident_brief  : produce a structured on-call brief
  - check_service_health   : return mock health status for a service
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Ops Inspector")


@mcp.tool()
async def parse_stack_trace(stack_trace: str) -> str:
    """Extract the most relevant frames and root exception from a stack trace.

    Args:
        stack_trace: Raw exception / stack trace text.

    Returns:
        JSON with exception message, top frames, and affected files.
    """
    lines = stack_trace.strip().splitlines()

    exception_line = ""
    for line in reversed(lines):
        s = line.strip()
        if s and not s.startswith("at ") and not s.startswith("File "):
            exception_line = s
            break

    frames: list[dict] = []
    for line in lines:
        # Python: File "path", line N, in func
        m = re.match(r'\s*File "(.+)", line (\d+), in (.+)', line)
        if m:
            frames.append(
                {"file": m.group(1), "line": int(m.group(2)), "function": m.group(3).strip()}
            )
            continue
        # Java / JS: at pkg.Class.method(File.java:42)
        m = re.match(r"\s*at ([\w.$<>]+)\((.+):(\d+)\)", line)
        if m:
            frames.append({"function": m.group(1), "file": m.group(2), "line": int(m.group(3))})

    return json.dumps(
        {
            "exception": exception_line,
            "total_frames": len(frames),
            "top_frames": frames[:5],
            "unique_files": list({f["file"] for f in frames}),
        },
        indent=2,
    )


@mcp.tool()
async def calculate_error_rate(
    error_count: int,
    total_requests: int,
    time_window_minutes: int = 5,
) -> str:
    """Compute error rate and return a severity label with a recommended action.

    Args:
        error_count: Number of errors in the window.
        total_requests: Total requests in the same window.
        time_window_minutes: Length of the observation window in minutes.

    Returns:
        JSON with rate, errors/min, severity, and recommendation.
    """
    if total_requests <= 0:
        return json.dumps({"error": "total_requests must be > 0"})

    rate = (error_count / total_requests) * 100

    if rate >= 50:
        severity, recommendation = "critical", "Immediate rollback or circuit-breaker required."
    elif rate >= 20:
        severity, recommendation = "high", "Alert on-call and prepare rollback plan."
    elif rate >= 5:
        severity, recommendation = "medium", "Investigate root cause; watch for escalation."
    else:
        severity, recommendation = "low", "Log for review; no immediate action needed."

    return json.dumps(
        {
            "error_rate_percent": round(rate, 2),
            "errors_per_minute": round(error_count / max(time_window_minutes, 1), 2),
            "severity": severity,
            "recommendation": recommendation,
            "window_minutes": time_window_minutes,
        },
        indent=2,
    )


@mcp.tool()
async def format_incident_brief(
    service: str,
    incident_type: str,
    severity: str,
    description: str,
    affected_users: int = 0,
) -> str:
    """Produce a structured on-call incident brief ready for Slack / PagerDuty.

    Args:
        service: Affected service name.
        incident_type: Incident category (e.g. latency, crash, data_loss).
        severity: critical / high / medium / low.
        description: Short human-readable description.
        affected_users: Estimated impacted user count.

    Returns:
        Plain-text incident brief.
    """
    emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
        severity.lower(), "⚪"
    )
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return f"""{emoji} INCIDENT BRIEF
{"=" * 44}
Time       : {ts}
Service    : {service}
Type       : {incident_type}
Severity   : {severity.upper()}
Affected   : {affected_users:,} users

{description}

Next steps:
1. Acknowledge in your on-call tool.
2. Assess blast radius and gather metrics.
3. Apply the AI-generated runbook remediation steps.
4. Post a status update every 15 minutes until resolved.
{"=" * 44}"""


@mcp.tool()
async def check_service_health(service_name: str, environment: str = "production") -> str:
    """Return health status for a named service (mock — replace with real HTTP calls).

    Args:
        service_name: Service to inspect.
        environment: Target environment (production / staging / dev).

    Returns:
        JSON health record.
    """
    registry: dict[str, dict] = {
        "api-gateway": {"status": "healthy", "latency_ms": 42, "uptime_pct": 99.98},
        "auth-service": {"status": "healthy", "latency_ms": 18, "uptime_pct": 99.99},
        "payment-service": {"status": "degraded", "latency_ms": 850, "uptime_pct": 97.20},
        "notification-service": {"status": "healthy", "latency_ms": 30, "uptime_pct": 99.95},
        "database": {"status": "healthy", "latency_ms": 5, "uptime_pct": 100.0},
    }
    key = service_name.lower().replace(" ", "-")
    record = registry.get(key, {"status": "unknown", "latency_ms": None, "uptime_pct": None})

    return json.dumps(
        {
            "service": service_name,
            "environment": environment,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            **record,
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
