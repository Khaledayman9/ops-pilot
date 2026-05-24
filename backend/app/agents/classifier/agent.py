from app.core import format_prompt, llm, load_prompt
from logger import logger

from .models import ClassificationInput, ClassificationOutput


class ClassifierAgent:
    def __init__(self) -> None:
        self._llm = llm.with_structured_output(ClassificationOutput)
        self._prompts = load_prompt("classifier")

    async def run(self, inp: ClassificationInput) -> ClassificationOutput:
        logger.info(f"[ClassifierAgent] Classifying: {inp.query[:80]}...")
        user_msg = format_prompt(self._prompts["user_template"], query=inp.query)
        messages = [
            ("system", self._prompts["system"]),
            ("human", user_msg),
        ]
        result: ClassificationOutput = await self._llm.ainvoke(messages)
        logger.info(
            f"[ClassifierAgent] service={result.service} severity={result.severity}"
        )
        return result
