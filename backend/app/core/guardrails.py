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

from settings import settings
from logger import logger

# ── Optional Presidio import ──────────────────────────────────────────────────
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine

    _analyzer = AnalyzerEngine()
    _anonymizer = AnonymizerEngine()
    _PRESIDIO_AVAILABLE = True
except ImportError:
    _PRESIDIO_AVAILABLE = False
    logger.warning("[Guardrails] presidio not installed — PII scrubbing disabled")


# ── Prompt injection patterns ─────────────────────────────────────────────────
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

_INJECTION_RE = re.compile(
    "|".join(_INJECTION_PATTERNS),
    re.IGNORECASE | re.MULTILINE,
)


class GuardrailViolation(ValueError):
    """Raised when user input fails a security guardrail check."""


def enforce_length(text: str) -> str:
    """Truncate input to the configured maximum length."""
    max_len = settings.MAX_QUERY_LENGTH
    if len(text) > max_len:
        logger.warning(f"[Guardrails] Input truncated from {len(text)} to {max_len} chars")
        return text[:max_len]
    return text


def sanitise_input(text: str) -> str:
    """Remove null bytes and non-printable control characters."""
    text = text.replace("\x00", "")
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def check_prompt_injection(text: str) -> None:
    """
    Raise GuardrailViolation if prompt injection patterns are detected.

    Only active when ENABLE_PROMPT_INJECTION_PROTECTION=true.
    """
    if not settings.ENABLE_PROMPT_INJECTION_PROTECTION:
        return
    match = _INJECTION_RE.search(text)
    if match:
        logger.warning(f"[Guardrails] Prompt injection detected: '{match.group()}'")
        raise GuardrailViolation(
            "Input contains disallowed instruction patterns. "
            "Please describe the incident without attempting to override system behaviour."
        )


def scrub_pii(text: str) -> str:
    """
    Replace PII (emails, phone numbers, IP addresses, etc.) with placeholders.

    Only active when ENABLE_PII_SCRUBBING=true and Presidio is installed.
    Falls back to regex-based scrubbing if Presidio is unavailable.
    """
    if not settings.ENABLE_PII_SCRUBBING:
        return text

    if _PRESIDIO_AVAILABLE:
        results = _analyzer.analyze(
            text=text,
            entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "IP_ADDRESS", "PERSON", "CREDIT_CARD"],
            language="en",
        )
        if results:
            anonymised = _anonymizer.anonymize(text=text, analyzer_results=results)
            return anonymised.text
        return text

    # Regex fallback
    # Email
    text = re.sub(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "<EMAIL>", text)
    # IPv4
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<IP_ADDRESS>", text)
    # Phone (simple international format)
    text = re.sub(r"\+?[\d\s\-\(\)]{10,15}", "<PHONE>", text)
    return text


def apply_all(text: str) -> str:
    """
    Apply the full guardrail pipeline to user input.

    Order:
      1. Sanitise control characters
      2. Enforce length cap
      3. Prompt injection check
      4. PII scrubbing

    Args:
        text: Raw user input.

    Returns:
        Cleaned text safe to pass to an LLM.

    Raises:
        GuardrailViolation: on injection detection.
    """
    text = sanitise_input(text)
    text = enforce_length(text)
    check_prompt_injection(text)
    text = scrub_pii(text)
    return text
