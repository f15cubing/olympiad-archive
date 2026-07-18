"""Claude API client for AI tagging — parallel provider to Gemini (Phase D).

Talks to Claude through the TrueFoundry gateway (or any Anthropic-compatible endpoint)
via the official Anthropic SDK. Two deliberate choices, per the gateway's quirks:

- Auth is a Bearer token (``ANTHROPIC_AUTH_TOKEN``), not ``ANTHROPIC_API_KEY``.
- The ``thinking`` parameter is NOT sent — on this gateway it routes to a Bedrock backend
  and 403s. Classification doesn't need it.

Structured output is forced with tool-use (a tool whose schema mirrors AITagMetadata), so
the result validates against the same Pydantic schema Gemini uses.
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    from anthropic import AsyncAnthropic, APIStatusError, RateLimitError
except ImportError:  # anthropic not installed
    AsyncAnthropic = None
    APIStatusError = RateLimitError = Exception

from .config import (
    ANTHROPIC_AUTH_TOKEN,
    ANTHROPIC_BASE_URL,
    CLAUDE_MODEL,
    CLAUDE_REQUESTS_PER_MINUTE,
    SYSTEM_PROMPT,
)
from .schemas import AITagMetadata, TaggingResult
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Tool schema mirroring AITagMetadata. Forcing this tool makes the model emit a
# well-formed classification object we can validate directly.
TAG_TOOL = {
    "name": "emit_classification",
    "description": "Emit the structured classification for the math olympiad problem.",
    "input_schema": {
        "type": "object",
        "properties": {
            "analysis": {"type": "string", "description": "1-2 sentence reasoning for the tags."},
            "field": {"type": "string",
                      "enum": ["Algebra", "Geometry", "Number Theory", "Combinatorics"]},
            "difficulty": {"type": "integer", "minimum": 1, "maximum": 10},
            "techniques": {"type": "array", "items": {"type": "string"},
                           "minItems": 1, "maxItems": 10,
                           "description": "1-10 specific techniques used."},
            "topics": {"type": "array", "items": {"type": "string"},
                       "minItems": 2, "maxItems": 7,
                       "description": "2-7 specific topic keywords."},
            "confidence_score": {"type": "integer", "minimum": 1, "maximum": 10},
        },
        "required": ["analysis", "field", "difficulty", "techniques", "topics", "confidence_score"],
    },
}


def _parse_custom_headers(raw: Optional[str]) -> dict:
    """Parse newline/comma-separated 'Name: Value' pairs into a header dict."""
    headers = {}
    for line in re.split(r"[\r\n,]", raw or ""):
        if ":" in line:
            name, value = line.split(":", 1)
            if name.strip():
                headers[name.strip()] = value.strip()
    return headers


class ClaudeCastError(Exception):
    """Raised when the Claude response can't be parsed into AITagMetadata."""


class ClaudeClient:
    """Client for tagging problems with Claude via an Anthropic-compatible gateway."""

    def __init__(self, auth_token: Optional[str] = None, base_url: Optional[str] = None,
                 model: Optional[str] = None):
        if AsyncAnthropic is None:
            raise ImportError("The 'anthropic' package is required for Claude tagging "
                              "(pip install anthropic).")
        # Re-read env at construction so a token set after import is honored.
        self.auth_token = auth_token or ANTHROPIC_AUTH_TOKEN or os.getenv("ANTHROPIC_AUTH_TOKEN")
        if not self.auth_token:
            raise ValueError("ANTHROPIC_AUTH_TOKEN not provided or set in environment")
        self.base_url = base_url or ANTHROPIC_BASE_URL
        self.model = model or CLAUDE_MODEL
        # Forward ANTHROPIC_CUSTOM_HEADERS if set (e.g. the TrueFoundry gateway's
        # x-tfy-api-key). Parsed as newline/comma-separated "Name: Value"; no-op if unset.
        self.client = AsyncAnthropic(
            auth_token=self.auth_token, base_url=self.base_url,
            default_headers=_parse_custom_headers(os.getenv("ANTHROPIC_CUSTOM_HEADERS")) or None,
        )
        self.rate_limiter = RateLimiter(CLAUDE_REQUESTS_PER_MINUTE)
        logger.info(f"Initialized ClaudeClient (model={self.model}, base_url={self.base_url})")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APIStatusError)),
        reraise=True,
    )
    async def tag_problem(
        self,
        problem_id: int,
        problem_statement: str,
        solution_content: Optional[str] = None,
        year: Optional[int] = None,
    ) -> TaggingResult:
        """Tag a single problem with Claude. Returns a TaggingResult (mirrors GeminiClient)."""
        try:
            await self.rate_limiter.check_limit()
        except asyncio.TimeoutError:
            return TaggingResult(problem_id=problem_id, success=False,
                                 error="Rate limit exceeded - please try again later")

        prompt = self._build_prompt(problem_statement, solution_content, year)
        try:
            logger.info(f"[claude] Tagging problem {problem_id}...")
            resp = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=[TAG_TOOL],
                tool_choice={"type": "tool", "name": TAG_TOOL["name"]},
                messages=[{"role": "user", "content": prompt}],
                # NB: no `thinking` (gateway 403s) and no sampling params (rejected on 4.7+).
            )
        except (RateLimitError, APIStatusError):
            raise  # let tenacity retry
        except Exception as e:
            logger.error(f"[claude] error tagging {problem_id}: {e}")
            return TaggingResult(problem_id=problem_id, success=False,
                                 error=f"Claude request failed: {e}")

        try:
            metadata = self._extract_metadata(resp)
        except ClaudeCastError as e:
            return TaggingResult(problem_id=problem_id, success=False,
                                 error=f"Failed to parse Claude response: {e}")

        tokens = 0
        usage = getattr(resp, "usage", None)
        if usage is not None:
            tokens = (getattr(usage, "input_tokens", 0) or 0) + (getattr(usage, "output_tokens", 0) or 0)
        logger.info(f"[claude] tagged {problem_id} (field={metadata.field}, conf={metadata.confidence_score})")
        return TaggingResult(problem_id=problem_id, success=True, metadata=metadata,
                             tokens_used=tokens, tagged_at=datetime.utcnow())

    @staticmethod
    def _build_prompt(problem_statement, solution_content=None, year=None) -> str:
        prompt = f"Problem:\n{problem_statement}\n"
        if solution_content:
            prompt += f"\nSolution:\n{solution_content}\n"
        if year:
            prompt += f"\nContext: This problem is from {year}.\n"
        prompt += "\nCall emit_classification with the structured classification."
        return prompt

    @staticmethod
    def _extract_metadata(resp) -> AITagMetadata:
        """Pull the forced tool_use input (or a JSON text fallback) into AITagMetadata."""
        data = None
        for block in getattr(resp, "content", []) or []:
            if getattr(block, "type", None) == "tool_use":
                data = block.input
                break
        if data is None:
            # Fallback: some gateways may return JSON text instead of a tool call.
            text = "".join(getattr(b, "text", "") for b in (resp.content or [])
                           if getattr(b, "type", None) == "text")
            start, end = text.find("{"), text.rfind("}") + 1
            if start == -1 or end == 0:
                raise ClaudeCastError("no tool_use block or JSON found in response")
            try:
                data = json.loads(text[start:end])
            except json.JSONDecodeError as e:
                raise ClaudeCastError(f"invalid JSON in response: {e}")
        # Coerce + clamp common malformations so a near-miss response still validates:
        # models sometimes emit techniques/topics as a comma string instead of a list,
        # or over-generate past the schema bounds, or exceed the analysis length.
        if isinstance(data, dict):
            for key in ("techniques", "topics"):
                v = data.get(key)
                if isinstance(v, str):
                    data[key] = [t.strip() for t in re.split(r"[;,]", v) if t.strip()]
            if isinstance(data.get("techniques"), list):
                data["techniques"] = data["techniques"][:10]
            if isinstance(data.get("topics"), list):
                data["topics"] = data["topics"][:7]
            if isinstance(data.get("analysis"), str) and len(data["analysis"]) > 500:
                data["analysis"] = data["analysis"][:500]
        try:
            return AITagMetadata(**data)
        except Exception as e:
            raise ClaudeCastError(f"invalid classification structure: {e}")
