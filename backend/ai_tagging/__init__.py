"""AI Tagging Module - Automated problem classification using Gemini API."""

from .gemini_client import GeminiClient
from .tagging_service import AITaggerService, main
from .schemas import AITagMetadata, TaggingResult, TaggingBatchResult, ProblemWithSolution

__all__ = [
    "GeminiClient",
    "AITaggerService",
    "AITagMetadata",
    "TaggingResult",
    "TaggingBatchResult",
    "ProblemWithSolution",
    "main",
]
