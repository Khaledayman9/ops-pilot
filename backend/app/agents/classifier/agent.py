from app.core import BaseAgent, format_prompt
from logger import logger

from .models import ClassificationInput, ClassificationOutput


class ClassifierAgent(BaseAgent):
    def __init__(self, **kwargs) -> None:
        super().__init__("classifier", **kwargs)
        self._chain = self._build_chain(ClassificationOutput)

    async def run(self, inp: ClassificationInput) -> ClassificationOutput:
        self._log(f"Classifying: {inp.query[:80]}...")
        user_msg = format_prompt(self._prompts["user_template"], query=inp.query)
        messages = [
            ("system", self._prompts["system"]),
            ("human", user_msg),
        ]
        result: ClassificationOutput = await self._chain.ainvoke(messages)
        self._log(f"service={result.service} severity={result.severity}")
        return result
