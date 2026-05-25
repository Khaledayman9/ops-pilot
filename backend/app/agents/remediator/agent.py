from app.core import BaseAgent, format_prompt

from .models import RemediatorInput, RemediatorOutput


class RemediatorAgent(BaseAgent):
    def __init__(self, **kwargs) -> None:
        super().__init__("remediator", **kwargs)
        self._chain = self._build_chain(RemediatorOutput)

    async def run(self, inp: RemediatorInput) -> RemediatorOutput:
        self._log(f"Remediating {inp.service} cause={inp.primary_cause[:50]}")
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
        self._log(f"{len(result.immediate_actions)} immediate actions generated")
        return result
