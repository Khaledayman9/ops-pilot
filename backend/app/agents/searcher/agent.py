from app.core.llm import format_prompt, llm, load_prompt
from logger import logger

from .models import SearchInput, SearchOutput
from .utils import build_neo4j_hints


class SearcherAgent:
    def __init__(self) -> None:
        self._llm = llm.with_structured_output(SearchOutput)
        self._prompts = load_prompt("searcher")

    async def run(self, inp: SearchInput) -> SearchOutput:
        logger.info(f"[SearcherAgent] Extracting entities for service={inp.service}")
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
        result: SearchOutput = await self._llm.ainvoke(messages)
        # Enrich with query hints
        result.search_queries = build_neo4j_hints(inp.service, result.entities.services)
        logger.info(f"[SearcherAgent] Entities: {result.entities.model_dump()}")
        return result
