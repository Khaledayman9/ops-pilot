from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.core import BaseAgent, format_prompt
from mcp_servers.mcp_client_manager import MCPClientManager

from .models import OpsAnalystInput, OpsAnalystOutput

from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig

_MCP_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "mcp_servers" / "servers.json"


class OpsAnalystAgent(BaseAgent):
    """
    Performs operational diagnostics using the custom Ops Inspector MCP server.

    Capabilities (via MCP tools):
      - Stack-trace parsing
      - Error-rate calculation and severity labelling
      - Incident brief formatting
      - Service health checks
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("ops_analyst", **kwargs)
        self._mcp_manager = MCPClientManager()
        self._init_lock = asyncio.Lock()
        self._agent = None
        self._tool_names: list[str] = []
        self._initialized = False

    async def _initialize(self) -> None:
        async with self._init_lock:
            if self._initialized:
                return
            try:
                tools = await self._load_ops_tools()
                self._tools = tools
                self._tool_names = [t.name for t in tools]

                self._agent = create_agent(
                    model=self.llm, tools=tools, system_prompt=self._prompts["system"]
                )
                self._initialized = True
                self._log(f"Initialized with tools: {self._tool_names}")
            except Exception as exc:
                self._log(f"Initialization failed: {exc}", level="error")
                raise

    async def _load_ops_tools(self) -> list:
        if not _MCP_CONFIG_PATH.exists():
            raise FileNotFoundError(f"servers.json not found at {_MCP_CONFIG_PATH}")

        with open(_MCP_CONFIG_PATH) as f:
            config: dict = json.load(f)

        ops_conf = {"ops-inspector": config.get("ops-inspector", {})}
        if not ops_conf["ops-inspector"]:
            raise ValueError("'ops-inspector' not configured in servers.json")

        tools = await self._mcp_manager.get_tools(ops_conf)
        if not tools:
            raise RuntimeError("Ops Inspector MCP returned no tools — check server path.")
        return tools

    async def run(self, inp: OpsAnalystInput) -> OpsAnalystOutput:
        self._log(f"task={inp.task.value} service={inp.service_name}")

        await self._initialize()

        user_message = format_prompt(
            self._prompts["user_template"],
            service_name=inp.service_name,
            task=inp.task.value,
            payload=inp.payload,
        )

        config = RunnableConfig(
            configurable={"thread_id": f"ops_analyst_{inp.service_name}_{inp.task.value}"},
            recursion_limit=15,
        )

        try:
            response = await asyncio.wait_for(
                self._agent.ainvoke(
                    {"messages": [("user", user_message)]},
                    config=config,
                ),
                timeout=45.0,
            )
        except asyncio.TimeoutError:
            self._log("Timed out after 45 s", level="error")
            return OpsAnalystOutput(
                task=inp.task.value,
                service_name=inp.service_name,
                result=(
                    "OpsAnalystAgent timed out. Check that the ops-inspector MCP server is running."
                ),
                tools_used=self._tool_names,
            )

        messages = response.get("messages", [])
        if messages:
            last = messages[-1]
            result = last.content if hasattr(last, "content") else str(last)
        else:
            result = response.get("output", "No output produced.")

        return OpsAnalystOutput(
            task=inp.task.value,
            service_name=inp.service_name,
            result=result,
            tools_used=self._tool_names,
        )

    async def cleanup(self) -> None:
        await self._mcp_manager.cleanup()
