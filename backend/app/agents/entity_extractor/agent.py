from app.core import BaseAgent, build_neo4j_hints, format_prompt

from .models import EntityExtractorInput, EntityExtractorOutput


class EntityExtractorAgent(BaseAgent):
    """
    Extracts structured entities (services, deployments, metrics, error codes)
    from a raw incident description.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("entity_extractor", **kwargs)
        self._chain = self._build_chain(EntityExtractorOutput)

    async def run(self, inp: EntityExtractorInput) -> EntityExtractorOutput:
        self._log(f"Extracting entities for service={inp.service}")
        user_msg = format_prompt(
            self._prompts["user_template"],
            query=inp.query,
            service=inp.service,
            incident_type=inp.incident_type,
        )
        messages = [
            ("system", self._prompts["system"]),
            ("human", user_msg),
        ]
        result: EntityExtractorOutput = await self._chain.ainvoke(messages)
        result.search_queries = build_neo4j_hints(inp.service, result.entities.services)
        self._log(f"Entities: {result.entities.model_dump()}")
        return result
