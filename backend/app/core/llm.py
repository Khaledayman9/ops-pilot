from langchain_openai import ChatOpenAI

from settings import settings

llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
    temperature=0,
    streaming=True,
)