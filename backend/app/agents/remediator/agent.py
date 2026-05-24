from __future__ import annotations

from app.core.llm import llm, format_prompt, load_prompt
from logger import logger

from .models import RemediatorInput, RemediatorOutput


class RemediatorAgent:
    def __init__(self) -> None:
        self._llm = llm.with_structured_output(RemediatorOutput)
        self._prompts = load_prompt("remediator")

    async def run(self, inp: RemediatorInput) -> RemediatorOutput:
        logger.info(
            f"[RemediatorAgent] Remediating {inp.service} "
            f"cause={inp.primary_cause[:50]}"
        )
        user_msg = format_prompt(
            self._prompts["user_template"],
            service=inp.service,
            severity=inp.severity,
            primary_cause=inp.primary_cause,
            causal_chain=inp.causal_chain,
            blast_radius=inp.blast_radius,
            deployment_correlation=inp.deployment_correlation,
            deployment_version=inp.deployment_version or "N/A",
        )
        messages = [
            ("system", self._prompts["system"]),
            ("human", user_msg),
        ]
        result: RemediatorOutput = await self._llm.ainvoke(messages)
        logger.info(
            f"[RemediatorAgent] {len(result.immediate_actions)} immediate actions"
        )
        return result
