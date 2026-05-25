"""
Centralised LLM factory.

Supports OpenAI (default), Anthropic, and Google Generative AI.
Select provider via the LLM_PROVIDER env var.

Usage:
    from app.core.llm import get_llm, llm
    # llm is the default singleton
    # get_llm() lets you request a specific provider/model/temperature
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from settings import settings
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI


def get_llm(
    provider: str | None = None,
    model_name: str | None = None,
    temperature: float | None = None,
    streaming: bool | None = None,
    max_retries: int | None = None,
) -> BaseChatModel:
    """
    Build and return a chat LLM instance.

    Args:
        provider:    "openai" | "anthropic" | "google". Defaults to settings.LLM_PROVIDER.
        model_name:  Model identifier. Defaults to settings.LLM_MODEL.
        temperature: Sampling temperature. Defaults to settings.LLM_TEMPERATURE.
        streaming:   Enable streaming. Defaults to settings.LLM_STREAMING.
        max_retries: Retry count on transient failures. Defaults to settings.LLM_MAX_RETRIES.

    Returns:
        A LangChain-compatible BaseChatModel instance.

    Raises:
        ValueError: for unsupported providers.
    """
    _provider = (provider or settings.LLM_PROVIDER).lower()
    _model = model_name or settings.LLM_MODEL
    _temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
    _streaming = streaming if streaming is not None else settings.LLM_STREAMING
    _retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES

    if _provider == "openai":
        return ChatOpenAI(
            model=_model,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=_temp,
            streaming=_streaming,
            max_retries=_retries,
        )

    if _provider == "anthropic":
        return ChatAnthropic(
            model=_model or settings.ANTHROPIC_MODEL,
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=_temp,
            streaming=_streaming,
            max_retries=_retries,
        )

    if _provider == "google":
        return ChatGoogleGenerativeAI(
            model=_model or settings.GOOGLE_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=_temp,
            streaming=_streaming,
            max_retries=_retries,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{_provider}'. Choose one of: openai, anthropic, google."
    )


# Module-level singleton — used by all agents unless they request a specific model
llm: BaseChatModel = get_llm()
