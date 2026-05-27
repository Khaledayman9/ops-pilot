from __future__ import annotations

import asyncio
import json
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig

from app.core import BaseAgent, format_prompt
from mcp_servers.mcp_client_manager import MCPClientManager

from .models import TerraformScoutInput, TerraformScoutOutput

_MCP_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "mcp_servers" / "servers.json"


class TerraformScoutAgent(BaseAgent):
    def __init__(self, **kwargs) -> None:
        super().__init__("terraform_scouter", **kwargs)
        self._mcp_manager = MCPClientManager()
        self._init_lock = asyncio.Lock()
        self._agent = None
        self._tool_names: list[str] = []
        self._initialized = False

    async def _initialize(self) -> None:
        async with self._init_lock:
            if self._initialized:
                return

            with open(_MCP_CONFIG_PATH) as f:
                config: dict = json.load(f)

            terraform_conf = {"terraform": config.get("terraform", {})}
            if not terraform_conf["terraform"]:
                raise ValueError("'terraform' not configured in servers.json")

            tools = await self._mcp_manager.get_tools(terraform_conf)
            if not tools:
                raise RuntimeError("Terraform MCP returned no tools")

            self._tool_names = [tool.name for tool in tools]
            prompt = PromptTemplate.from_template(self._prompts["react_template"])
            self._agent = create_agent(model=self.llm, tools=tools, system_prompt=prompt)
            self._initialized = True

    async def run(self, inp: TerraformScoutInput) -> TerraformScoutOutput:
        await self._initialize()

        user_message = format_prompt(
            self._prompts["user_template"],
            task=inp.task,
            workspace=inp.workspace or "default",
            extra_context=inp.extra_context or "No incident context provided.",
        )

        config = RunnableConfig(
            configurable={"thread_id": f"terraform_scout_{inp.workspace}_{inp.task}"},
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
            return TerraformScoutOutput(
                task=inp.task,
                workspace=inp.workspace,
                summary="TerraformScoutAgent timed out. Check Terraform MCP configuration.",
                tools_used=self._tool_names,
            )

        messages = response.get("messages", [])
        summary = (
            messages[-1].content if messages and hasattr(messages[-1], "content") else str(response)
        )

        return TerraformScoutOutput(
            task=inp.task,
            workspace=inp.workspace,
            summary=summary,
            tools_used=self._tool_names,
        )

    async def cleanup(self) -> None:
        await self._mcp_manager.cleanup()
