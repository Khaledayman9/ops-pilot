"""
Centralised URI constants for all API endpoints.

Import from routes to avoid magic strings scattered across the codebase.
"""


class AuthURIs:
    REGISTER = "/register"
    LOGIN = "/login"
    REFRESH = "/refresh"
    ME = "/me"


class IncidentURIs:
    ANALYZE = "/analyze"


class ChatURIs:
    ROOT = "/"
    SESSION = "/{session_id}"
    MESSAGES = "/{session_id}/messages"
    EXECUTIONS = "/{session_id}/executions"


class StreamURIs:
    INCIDENT = "/incident"


__all__ = ["AuthURIs", "IncidentURIs", "ChatURIs", "StreamURIs"]
