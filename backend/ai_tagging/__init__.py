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

# Claude provider (Phase D) — imported lazily to avoid a hard dependency on `anthropic`
# for the Gemini-only path.
try:
    from .claude_client import ClaudeClient
    from .claude_tagger_service import ClaudeTaggerService
    __all__ += ["ClaudeClient", "ClaudeTaggerService"]
except ImportError:
    pass
