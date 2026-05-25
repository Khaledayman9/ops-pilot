from app.core import BaseAgent, format_prompt

from .models import RootCauseFinderInput, RootCauseFinderOutput


class RootCauseFinderAgent(BaseAgent):
    def __init__(self, **kwargs) -> None:
        super().__init__("root_cause_finder", **kwargs)
        self._chain = self._build_chain(RootCauseFinderOutput)

    async def run(
        self,
        inp: RootCauseFinderInput,
        web_context: str = "No supplementary web intelligence available.",
    ) -> RootCauseFinderOutput:
        self._log(f"RCA for {inp.service} ({inp.severity})")
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
            runbooks=inp.graph_context.get("runbooks", []),
            ownership=inp.graph_context.get("ownership", []),
            classification=inp.classification,
            web_context=web_context,
        )
        messages = [
            ("system", self._prompts["system"]),
            ("human", user_msg),
        ]
        result: RootCauseFinderOutput = await self._chain.ainvoke(messages)
        self._log(f"cause={result.primary_cause[:60]} conf={result.confidence_score}")
        return result
