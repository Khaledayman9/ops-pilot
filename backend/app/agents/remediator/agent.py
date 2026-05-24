from .models import RemediatorInput, RemediatorOutput
from app.core import llm, load_prompt, format_prompt
from logger import logger

class RemediatorAgent:
    def __init__(self) -> None:
        self._chain = llm.with_structured_output(RemediatorOutput)
        self._prompts = load_prompt[str, str]("root_cause_finder")

    async def run(self, inp: RemediatorInput) -> RemediatorOutput:
        logger.info(f"[RemediationAgent] Remediating {inp.service} cause={inp.primary_cause[:50]}")
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
        result: RemediatorOutput = await self._chain.ainvoke(messages)
        logger.info(f"[RemediationAgent] {len(result.immediate_actions)} immediate actions")
        return result