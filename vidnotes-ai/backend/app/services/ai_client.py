"""Single entry point for AI generation: Gemini first, Groq as optional backup."""

import logging
from typing import TypeVar

from pydantic import BaseModel

from app.core.config import get_settings
from app.core.errors import ExternalServiceError
from app.services.gemini_client import GeminiClient
from app.services.groq_client import GroqClient

logger = logging.getLogger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)

# Gemini failures that Groq may cover: quota/rate limits, overload, timeouts.
# Configuration problems such as an invalid Gemini key are reported instead.
_BACKUP_STATUS_CODES = {429, 503, 504}


class AIClient:
    def __init__(self):
        self._gemini = GeminiClient()
        self._groq = GroqClient() if get_settings().groq_api_key else None

    def generate_text(self, prompt: str, system_instruction: str) -> str:
        try:
            return self._gemini.generate_text(prompt, system_instruction)
        except ExternalServiceError as exc:
            return self._backup(exc).generate_text(prompt, system_instruction)

    def generate_structured(self, prompt: str, system_instruction: str, schema: type[SchemaT]) -> SchemaT:
        try:
            return self._gemini.generate_structured(prompt, system_instruction, schema)
        except ExternalServiceError as exc:
            return self._backup(exc).generate_structured(prompt, system_instruction, schema)

    def _backup(self, gemini_error: ExternalServiceError) -> GroqClient:
        """Return the Groq client, or re-raise the Gemini error if Groq cannot help."""
        if self._groq is None or gemini_error.status_code not in _BACKUP_STATUS_CODES:
            raise gemini_error
        logger.warning("Gemini unavailable (%s); using Groq backup", gemini_error.message)
        return self._groq
