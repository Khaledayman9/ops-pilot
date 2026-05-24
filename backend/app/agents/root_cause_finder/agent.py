from __future__ import annotations

from app.core import llm, format_prompt, load_prompt
from logger import logger

from .models import RootCauseFinderInput, RootCauseFinderOutput


class RootCauseFinderAgent:
    def __init__(self) -> None:
        self._llm = llm.with_structured_output(RootCauseFinderOutput)
        self._prompts = load_prompt("root_cause_finder")

    async def run(
        self,
        inp: RootCauseFinderInput,
        web_context: str = "No supplementary web intelligence available.",
    ) -> RootCauseFinderOutput:
        logger.info(f"[RootCauseFinderAgent] RCA for {inp.service} ({inp.severity})")
        user_msg = format_prompt(
            self._prompts["user_template"],
            incident=inp.query,
            service=inp.service,
            severity=inp.severity,
            incident_type=inp.incident_type,
            affected_services=inp.graph_context.get("affected_services", []),
            recent_deployments=inp.graph_context.get("recent_deployments", []),
            related_incidents=inp.graph_context.get("related_incidents", []),
            upstream_services=inp.graph_context.get("upstream_services", []),
            downstream_services=inp.graph_context.get("downstream_services", []),
            classification=inp.classification,
            web_context=web_context,
        )
        messages = [
            ("system", self._prompts["system"]),
            ("human", user_msg),
        ]
        result: RootCauseFinderOutput = await self._llm.ainvoke(messages)
        logger.info(
            f"[RootCauseFinderAgent] cause={result.primary_cause[:60]} "
            f"conf={result.confidence_score}"
        )
        return result
