from __future__ import annotations

import asyncio
import os
import re
from typing import Any, Dict, List

from langchain_mcp_adapters.client import MultiServerMCPClient
from logger import logger


def _interpolate_env(value: Any) -> Any:
    """Recursively replace ${VAR} placeholders with environment variable values."""
    if isinstance(value, str):

        def _replace(match: re.Match) -> str:
            var = match.group(1)
            result = os.environ.get(var, "")
            if not result:
                logger.warning(f"[MCPClientManager] env var '{var}' is not set or empty")
            return result

        return re.sub(r"\$\{([^}]+)\}", _replace, value)
    if isinstance(value, dict):
        return {k: _interpolate_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate_env(item) for item in value]
    return value


class MCPClientManager:
    """Manages MCP client connections without global state."""

    def __init__(self) -> None:
        self._clients: Dict[str, MultiServerMCPClient] = {}
        self._lock = asyncio.Lock()

    async def get_tools(self, mcp_dict: Dict[str, Any]) -> List[Any]:
        """
        Return LangChain-compatible tools from the given MCP server config.

        Supports ${ENV_VAR} interpolation in any string value (e.g. auth tokens).
        Connections are cached by server names so the same process is reused.
        """
        try:
            resolved = _interpolate_env(mcp_dict)
            cache_key = ",".join(sorted(mcp_dict.keys()))

            async with self._lock:
                if cache_key not in self._clients:
                    logger.info(f"[MCPClientManager] Creating client for: {list(resolved.keys())}")
                    self._clients[cache_key] = MultiServerMCPClient(resolved)
                else:
                    logger.debug("[MCPClientManager] Reusing existing client")

                client = self._clients[cache_key]

            tools = await asyncio.wait_for(client.get_tools(), timeout=15.0)
            logger.info(f"[MCPClientManager] Loaded {len(tools)} tools")
            return tools

        except asyncio.TimeoutError:
            logger.error("[MCPClientManager] Timeout loading MCP tools")
            return []
        except Exception as exc:
            logger.error(f"[MCPClientManager] Error loading tools: {exc}")
            return []

    async def cleanup(self) -> None:
        """Close all cached MCP client connections."""
        async with self._lock:
            for key, client in self._clients.items():
                try:
                    closer = getattr(client, "aclose", None) or getattr(client, "close", None)
                    if closer:
                        await closer()
                    logger.debug(f"[MCPClientManager] Closed client: {key}")
                except Exception as exc:
                    logger.warning(f"[MCPClientManager] Error closing client {key}: {exc}")
            self._clients.clear()
