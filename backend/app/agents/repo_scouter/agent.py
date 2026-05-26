from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.core import BaseAgent, format_prompt
from mcp_servers.mcp_client_manager import MCPClientManager

from .models import RepoScoutInput, RepoScoutOutput
from langchain.agents import create_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig

_MCP_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "mcp_servers" / "servers.json"


class RepoScoutAgent(BaseAgent):
    """
    Fetches live GitHub repository data (branches, issues, PRs, commits)
    using the official GitHub MCP server and produces an ops-focused summary.

    Authentication: set GITHUB_TOKEN in .env — the MCPClientManager
    substitutes it automatically from servers.json via ${GITHUB_TOKEN}.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("repo_scout", **kwargs)
        self._mcp_manager = MCPClientManager()
        self._init_lock = asyncio.Lock()
        self._agent = None
        self._initialized = False

    # Initialisation                                                       #
    async def _initialize(self) -> None:
        async with self._init_lock:
            if self._initialized:
                return
            try:
                tools = await self._load_github_tools()
                self._tools = tools
                self._tool_names = [t.name for t in tools]

                prompt = PromptTemplate.from_template(self._prompts["react_template"])
                self._agent = create_agent(
                    model=self.llm,
                    tools=tools,
                    system_prompt=prompt,
                )
                self._initialized = True
                self._log(f"Initialized with {len(tools)} GitHub tools: {self._tool_names}")
            except Exception as exc:
                self._log(f"Initialization failed: {exc}", level="error")
                raise

    async def _load_github_tools(self) -> list:
        if not _MCP_CONFIG_PATH.exists():
            raise FileNotFoundError(f"servers.json not found at {_MCP_CONFIG_PATH}")

        with open(_MCP_CONFIG_PATH) as f:
            config: dict = json.load(f)

        github_conf = {"github": config.get("github", {})}
        if not github_conf["github"]:
            raise ValueError("'github' not configured in servers.json")

        tools = await self._mcp_manager.get_tools(github_conf)
        if not tools:
            raise RuntimeError(
                "GitHub MCP returned no tools — is GITHUB_TOKEN set and mcp-server-github installed?"
            )
        return tools

    async def run(self, inp: RepoScoutInput) -> RepoScoutOutput:
        self._log(f"task='{inp.task}' repo={inp.owner}/{inp.repo}")

        await self._initialize()

        user_message = format_prompt(
            self._prompts["user_template"],
            owner=inp.owner,
            repo=inp.repo,
            task=inp.task,
            extra_context=inp.extra_context or "No additional context.",
        )

        config = RunnableConfig(
            configurable={"thread_id": f"repo_scout_{inp.owner}_{inp.repo}_{inp.task}"},
            recursion_limit=20,
        )

        try:
            response = await asyncio.wait_for(
                self._agent.ainvoke(
                    {"messages": [("user", user_message), ("system", self._prompts["system"])]},
                    config=config,
                ),
                timeout=60,
            )
        except asyncio.TimeoutError:
            self._log("Timed out after 60 s", level="error")
            return RepoScoutOutput(
                owner=inp.owner,
                repo=inp.repo,
                task=inp.task,
                summary="RepoScoutAgent timed out. The GitHub MCP server may be unreachable.",
                tools_used=self._tool_names,
            )

        messages = response.get("messages", [])
        if messages:
            last = messages[-1]
            summary = last.content if hasattr(last, "content") else str(last)
        else:
            summary = response.get("output", "No output produced.")

        return RepoScoutOutput(
            owner=inp.owner,
            repo=inp.repo,
            task=inp.task,
            summary=summary,
            tools_used=self._tool_names,
        )

    async def cleanup(self) -> None:
        await self._mcp_manager.cleanup()
