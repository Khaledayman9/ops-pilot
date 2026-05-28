"""
BaseAgent — abstract base class for all Ops-Pilot agents.

Every agent (LangChain-based or CrewAI-based) inherits from this class
and implements the ``run`` coroutine.  The base class provides:

  - Centralised LLM access via ``self.llm``
  - Prompt loading via ``self._load_prompts()``
  - Structured logging with agent name prefix
  - A ``_build_chain`` helper for structured-output chains
"""

from __future__ import annotations

import abc
from typing import Any, TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

from app.core.llm import get_llm
from app.core.utils import load_prompt
from logger import logger

TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)


class BaseAgent(abc.ABC):
    """
    Abstract base for all agents.

    Subclass and implement ``run``.

    Args:
        agent_name:  Matches the agent's folder under ``app/agents/``.
                     Used to load ``prompts.yaml`` and prefix log messages.
        provider:    LLM provider override (``"openai"``, ``"anthropic"``, ``"google"``).
        model_name:  Model override.
        temperature: Temperature override.
        streaming:   Streaming override.
        max_retries: Retry override.
    """

    def __init__(
        self,
        agent_name: str,
        *,
        provider: str | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
        streaming: bool | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.agent_name = agent_name
        self.llm: BaseChatModel = get_llm(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            streaming=streaming,
            max_retries=max_retries,
        )
        self._prompts: dict[str, str] = self._load_prompts()

    # Prompt helpers
    def _load_prompts(self) -> dict[str, str]:
        """Load and cache prompts.yaml for this agent."""
        try:
            return load_prompt(self.agent_name)
        except FileNotFoundError:
            logger.warning(f"[{self.agent_name}] prompts.yaml not found — using empty prompts")
            return {"system": "", "user_template": ""}

    # LLM chain helpers
    def _build_chain(self, output_schema: type[BaseModel]) -> Any:
        """
        Return a chain that forces the LLM to output a validated Pydantic model.

        Usage:
            chain = self._build_chain(MyOutputSchema)
            result: MyOutputSchema = await chain.ainvoke(messages)
        """
        return self.llm.with_structured_output(output_schema, method="function_calling")

    # Logging───────────
    def _log(self, msg: str, level: str = "info") -> None:
        fn = getattr(logger, level, logger.info)
        fn(f"[{self.agent_name}] {msg}")

    # Abstract interface
    @abc.abstractmethod
    async def run(self, inp: Any) -> Any:
        """
        Execute the agent.

        Args:
            inp: Agent-specific Pydantic input model.

        Returns:
            Agent-specific Pydantic output model.
        """
