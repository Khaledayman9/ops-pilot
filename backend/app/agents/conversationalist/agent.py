from __future__ import annotations

import json

from app.core import BaseAgent, format_prompt

from .models import ConversationalistInput, ConversationalistOutput


class ConversationalistAgent(BaseAgent):
    """
    Produces the natural-language conversational reply for every turn.

    For incident-relevant queries it synthesises the structured pipeline output
    (root cause, remediation, timeline, blast radius) plus the compacted
    conversation history into an empathetic, actionable explanation.

    For off-topic / irrelevant queries it responds helpfully without fabricating
    any incident analysis.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("conversationalist", **kwargs)
        self._chain = self._build_chain(ConversationalistOutput)

    async def run(self, inp: ConversationalistInput) -> ConversationalistOutput:  # type: ignore[override]
        self._log(f"Generating natural response (incident={inp.is_incident_query})")

        history_text = (
            "\n".join(f"[{turn.role.upper()}]: {turn.content}" for turn in inp.history)
            if inp.history
            else "No prior conversation."
        )

        citations_text = (
            "\n".join(
                f"- [{r.get('title', 'Source')}]({r.get('url', '')})" for r in inp.web_citations
            )
            if inp.web_citations
            else "None"
        )

        user_msg = format_prompt(
            self._prompts["user_template"],
            query=inp.query,
            is_incident_query=str(inp.is_incident_query),
            history=history_text,
            incident_structured=(
                json.dumps(inp.incident_structured, indent=2) if inp.incident_structured else "null"
            ),
            analysis_context=inp.analysis_context or "Not available.",
            web_citations=citations_text,
        )

        result: ConversationalistOutput = await self._chain.ainvoke(
            [
                ("system", self._prompts["system"]),
                ("human", user_msg),
            ]
        )
        self._log("Natural response generated")
        return result
