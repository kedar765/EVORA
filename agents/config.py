"""
EVORA Centralized Agent & Model Configuration
=============================================
Manages independent Gemini model assignments for the three EVORA AI agents,
model quota tracking with circuit-breaker protection against endless retries,
and model instantiation helpers.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

# Ensure root .env is loaded
_ROOT_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT_DIR / ".env"
if _ENV_FILE.exists():
    load_dotenv(dotenv_path=_ENV_FILE, override=False)
else:
    load_dotenv(override=False)

logger = logging.getLogger("evora.config")

# -----------------------------------------------------------------------------
# 1. Independent Default Model Identifiers
# -----------------------------------------------------------------------------

ANALYTICS_DEFAULT_MODEL = "gemini-3.5-flash-lite"
RISK_DEFAULT_MODEL = "gemini-3.7-flash"
DECISION_DEFAULT_MODEL = "gemini-3.1-pro-preview"

# Default fallback models for Groq (optional secondary tier)
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"


# -----------------------------------------------------------------------------
# 2. Independent Model Resolvers
# -----------------------------------------------------------------------------

def get_analytics_model() -> str:
    """Returns the configured Gemini model ID for the Analytics Agent."""
    return (
        os.getenv("ANALYTICS_GEMINI_MODEL")
        or os.getenv("GEMINI_ANALYTICS_MODEL")
        or ANALYTICS_DEFAULT_MODEL
    ).strip()


def get_risk_model() -> str:
    """Returns the configured Gemini model ID for the Risk Agent."""
    return (
        os.getenv("RISK_GEMINI_MODEL")
        or os.getenv("GEMINI_RISK_MODEL")
        or RISK_DEFAULT_MODEL
    ).strip()


def get_decision_model() -> str:
    """Returns the configured Gemini model ID for the Decision Optimization Agent."""
    return (
        os.getenv("DECISION_GEMINI_MODEL")
        or os.getenv("GEMINI_DECISION_MODEL")
        or DECISION_DEFAULT_MODEL
    ).strip()


# -----------------------------------------------------------------------------
# 3. Quota Tracker & Circuit Breaker
# -----------------------------------------------------------------------------

@dataclass
class ModelExhaustionRecord:
    model_name: str
    error_message: str
    exhausted_at: float
    retry_after_seconds: Optional[float] = None


class ModelQuotaManager:
    """
    Thread-safe circuit breaker that tracks daily/rate-limit quota exhaustion
    per model ID to prevent redundant failed requests when quotas are exhausted.
    """

    _lock = threading.Lock()
    _exhausted_models: Dict[str, ModelExhaustionRecord] = {}

    @classmethod
    def is_exhausted(cls, model_name: str) -> Tuple[bool, Optional[str]]:
        """
        Checks whether a given model is currently marked as quota-exhausted.
        Returns (is_exhausted, reason_message).
        """
        if not model_name:
            return False, None

        with cls._lock:
            record = cls._exhausted_models.get(model_name)
            if not record:
                return False, None

            # Check if a retry-after timer was provided and has elapsed
            if record.retry_after_seconds is not None:
                elapsed = time.time() - record.exhausted_at
                if elapsed >= record.retry_after_seconds:
                    del cls._exhausted_models[model_name]
                    logger.info("Quota retry-after period elapsed for model %s; re-enabling.", model_name)
                    return False, None

            return True, record.error_message

    @classmethod
    def mark_exhausted(
        cls,
        model_name: str,
        error_message: str,
        retry_after_seconds: Optional[float] = None,
    ) -> None:
        """Marks a specific model ID as quota-exhausted."""
        if not model_name:
            return

        with cls._lock:
            cls._exhausted_models[model_name] = ModelExhaustionRecord(
                model_name=model_name,
                error_message=error_message,
                exhausted_at=time.time(),
                retry_after_seconds=retry_after_seconds,
            )
            logger.warning(
                "Circuit breaker tripped: Model %s marked quota-exhausted. Reason: %s",
                model_name,
                error_message,
            )

    @classmethod
    def reset(cls, model_name: Optional[str] = None) -> None:
        """Resets the circuit breaker for testing or after quota refresh."""
        with cls._lock:
            if model_name:
                cls._exhausted_models.pop(model_name, None)
            else:
                cls._exhausted_models.clear()

    @classmethod
    def get_exhausted_models(cls) -> Dict[str, str]:
        """Returns a snapshot of currently exhausted models and error messages."""
        with cls._lock:
            return {name: rec.error_message for name, rec in cls._exhausted_models.items()}

    @staticmethod
    def is_quota_error(error: Exception | str) -> bool:
        """Determines if an exception or error string represents a quota or rate-limit error."""
        msg = str(error).upper()
        return (
            "RESOURCE_EXHAUSTED" in msg
            or "429" in msg
            or "QUOTA EXCEEDED" in msg
            or "RATE LIMIT" in msg
            or "RATELIMIT" in msg
        )


# -----------------------------------------------------------------------------
# 4. LLM Factory Helper
# -----------------------------------------------------------------------------

def create_gemini_chat_model(
    model_name: str,
    api_key: str,
    temperature: float = 0.1,
    timeout: float = 25.0,
) -> Any:
    """
    Creates a ChatGoogleGenerativeAI instance targeting the v1beta API endpoint
    required for preview and latest generation models (e.g. gemini-3.1-pro-preview).
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temperature,
        timeout=timeout,
        api_version="v1beta",
    )
