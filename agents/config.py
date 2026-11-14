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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import certifi
from dotenv import load_dotenv

# Configure Windows certificate verification using truststore and certifi CA bundle
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

if "SSL_CERT_FILE" not in os.environ:
    os.environ["SSL_CERT_FILE"] = certifi.where()
if "REQUESTS_CA_BUNDLE" not in os.environ:
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# Load root .env without overriding system/deployment environment variables (override=False preserves deployment precedence)
_ROOT_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT_DIR / ".env"
if _ENV_FILE.exists():
    load_dotenv(dotenv_path=_ENV_FILE, override=False)
else:
    load_dotenv(override=False)

logger = logging.getLogger("evora.config")

# -----------------------------------------------------------------------------
# 1. Independent Default Model Identifiers (Gemini 4 Family)
# -----------------------------------------------------------------------------

SAFE_GEMINI_4_DEFAULT = "gemini-4-hydrogen"
ANALYTICS_DEFAULT_MODEL = "gemini-4-hydrogen"
RISK_DEFAULT_MODEL = "gemini-4-carbon"
DECISION_DEFAULT_MODEL = "gemini-4-argon"

# Default fallback models for Groq (optional secondary tier)
GROQ_DEFAULT_MODEL = "openai/gpt-oss-120b"


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


def resolve_active_gemini_model(model_name: str) -> str:
    """
    Resolves the active Gemini model identifier.
    If Carbon or Argon are requested but unavailable (e.g. Free Tier limit 0 or marked exhausted),
    returns the safe default Gemini 4 model (gemini-4-hydrogen).
    """
    clean_model = (model_name or SAFE_GEMINI_4_DEFAULT).strip()
    is_exhausted, _ = ModelQuotaManager.is_exhausted(clean_model)
    if is_exhausted and clean_model in {"gemini-4-carbon", "gemini-4-argon"}:
        return SAFE_GEMINI_4_DEFAULT
    return clean_model


def get_groq_model() -> str:
    """
    Returns the configured Groq model ID, normalizing deprecated or removed model IDs
    (e.g. legacy llama-3.1-70b-versatile which was deprecated on Groq).
    """
    raw_model = (os.getenv("GROQ_MODEL") or GROQ_DEFAULT_MODEL).strip()
    if "llama-3.1" in raw_model.lower():
        return GROQ_DEFAULT_MODEL
    return raw_model


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
        """Determines if an exception or error string represents a quota, rate-limit, or service exhaustion error."""
        msg = str(error).upper()
        return (
            "RESOURCE_EXHAUSTED" in msg
            or "429" in msg
            or "QUOTA EXCEEDED" in msg
            or "RATE LIMIT" in msg
            or "RATELIMIT" in msg
            or "503" in msg
            or "UNAVAILABLE" in msg
            or "HIGH DEMAND" in msg
            or "504" in msg
            or "DEADLINE_EXCEEDED" in msg
            or "DEADLINE EXPIRED" in msg
            or "TIMED OUT" in msg
            or "TIMEOUT" in msg
        )


# -----------------------------------------------------------------------------
# 4. LLM Factory Helpers
# -----------------------------------------------------------------------------

def create_gemini_chat_model(
    model_name: str,
    api_key: str,
    temperature: float = 0.1,
    timeout: float = 15.0,
) -> Any:
    """
    Creates a ChatGoogleGenerativeAI instance targeting the v1beta API endpoint
    required for preview and latest generation models.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temperature,
        timeout=timeout,
        api_version="v1beta",
    )


def create_groq_chat_model(
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = 0.1,
    timeout: float = 15.0,
) -> Any:
    """
    Creates a resilient ChatGroq instance with valid TLS certificate verification
    using the certifi trusted CA bundle and normalizes deprecated model names.
    """
    import ssl
    import certifi
    import httpx
    from langchain_groq import ChatGroq

    model = model_name or get_groq_model()
    if "llama-3.1" in str(model).lower():
        model = GROQ_DEFAULT_MODEL

    key = api_key or os.getenv("GROQ_API_KEY")

    # Secure HTTP client with trusted CA certificate verification
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    http_client = httpx.Client(verify=ssl_context, timeout=timeout)

    return ChatGroq(
        model=model,
        groq_api_key=key,
        temperature=temperature,
        timeout=timeout,
        http_client=http_client,
    )
