"""
Security guardrails applied to all user-supplied input before it reaches an LLM.

Protections:
  1. Length capping              — prevents prompt-length attacks
  2. Prompt injection detection  — blocks common jailbreak patterns
  3. PII scrubbing               — removes emails, IPs, phone numbers via Presidio
  4. Input sanitisation          — strips null bytes and control characters
"""

from __future__ import annotations

import re
from typing import Any

from logger import logger
from settings import settings

_analyzer: Any | None = None
_anonymizer: Any | None = None
_PRESIDIO_AVAILABLE = True


def _get_presidio_engines() -> tuple[Any | None, Any | None]:
    global _analyzer, _anonymizer, _PRESIDIO_AVAILABLE

    if not settings.ENABLE_PII_SCRUBBING:
        return None, None

    if not _PRESIDIO_AVAILABLE:
        return None, None

    if _analyzer is not None and _anonymizer is not None:
        return _analyzer, _anonymizer

    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
    except ImportError:
        _PRESIDIO_AVAILABLE = False
        logger.warning("[Guardrails] presidio not installed - using regex PII fallback")
        return None, None

    _analyzer = AnalyzerEngine()
    _anonymizer = AnonymizerEngine()
    return _analyzer, _anonymizer


_INJECTION_PATTERNS = [
    # Classic jailbreaks
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(everything|all|prior)",
    r"you\s+are\s+now\s+(?:a|an)\s+",
    r"act\s+as\s+(?:if\s+you\s+(?:are|were)\s+)?(?:a|an)\s+",
    r"pretend\s+(you\s+are|to\s+be)",
    r"roleplay\s+as",
    r"simulate\s+(?:a|an)\s+",
    # Instruction overrides
    r"new\s+instruction[s]?\s*:",
    r"system\s*prompt\s*:",
    r"\[INST\]",
    r"<\|im_start\|>",
    r"<\|system\|>",
    # Data exfiltration
    r"reveal\s+(your\s+)?(system\s+)?prompt",
    r"print\s+(your\s+)?(system\s+)?prompt",
    r"show\s+(me\s+)?(your\s+)?(instructions|prompt)",
]

_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE | re.MULTILINE)


class GuardrailViolation(ValueError):
    """Raised when user input fails a security guardrail check."""


def enforce_length(text: str) -> str:
    max_len = settings.MAX_QUERY_LENGTH
    if len(text) > max_len:
        logger.warning(f"[Guardrails] Input truncated from {len(text)} to {max_len} chars")
        return text[:max_len]
    return text


def sanitise_input(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def check_prompt_injection(text: str) -> None:
    if not settings.ENABLE_PROMPT_INJECTION_PROTECTION:
        return

    match = _INJECTION_RE.search(text)
    if match:
        logger.warning(f"[Guardrails] Prompt injection detected: '{match.group()}'")
        raise GuardrailViolation(
            "Input contains disallowed instruction patterns. "
            "Please describe the incident without attempting to override system behaviour."
        )


def _regex_scrub_pii(text: str) -> str:
    text = re.sub(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "<EMAIL>", text)
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<IP_ADDRESS>", text)
    text = re.sub(r"\+?[\d\s\-\(\)]{10,15}", "<PHONE>", text)
    return text


def scrub_pii(text: str) -> str:
    if not settings.ENABLE_PII_SCRUBBING:
        return text

    analyzer, anonymizer = _get_presidio_engines()

    if analyzer is None or anonymizer is None:
        return _regex_scrub_pii(text)

    results = analyzer.analyze(
        text=text,
        entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "IP_ADDRESS", "PERSON", "CREDIT_CARD"],
        language="en",
    )

    if not results:
        return text

    anonymised = anonymizer.anonymize(text=text, analyzer_results=results)
    return anonymised.text


def apply_all(text: str) -> str:
    text = sanitise_input(text)
    text = enforce_length(text)
    check_prompt_injection(text)
    text = scrub_pii(text)
    return text
