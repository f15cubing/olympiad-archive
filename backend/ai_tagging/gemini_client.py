"""Gemini API client for AI tagging."""

import json
import logging
import asyncio
from typing import Optional
from datetime import datetime, timedelta
import re

# load .env before reading environment variables
from dotenv import load_dotenv
load_dotenv()

# prefer the newer google.genai package; fall back to deprecated google.generativeai
try:
    import google.genai as genai
    USE_GENAI = True
except ImportError:
    import google.generativeai as genai
    USE_GENAI = False

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import GEMINI_API_KEY, GEMINI_MODEL, SYSTEM_PROMPT
from .schemas import AITagMetadata, TaggingResult
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)


class GeminiCastError(Exception):
    """Raised when Gemini response cannot be parsed."""
    pass


class GeminiRateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    pass


class GeminiClient:
    """Client for interacting with Google's Gemini API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini client with API key."""
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not provided or set in environment")

        # initialize service depending on library
        self.rate_limiter = RateLimiter()
        if USE_GENAI:
            # new package: create a client object
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = GEMINI_MODEL
            logger.info(f"Initialized genai.Client with model: {GEMINI_MODEL}")
        else:
            # old package: configure globally
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=SYSTEM_PROMPT)
            logger.warning("Using deprecated google.generativeai package; consider migrating")
            logger.info(f"Initialized deprecated generativeai model: {GEMINI_MODEL}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((GeminiRateLimitError, Exception)),
        reraise=True
    )
    async def tag_problem(
        self,
        problem_id: int,
        problem_statement: str,
        solution_content: Optional[str] = None,
        year: Optional[int] = None,
    ) -> TaggingResult:
        """
        Tag a single problem using Gemini AI.

        Args:
            problem_id: ID of the problem in the database
            problem_statement: The problem text
            solution_content: The solution text (optional)
            year: Year the problem was from (optional, for context)

        Returns:
            TaggingResult with metadata or error information
        """
        try:
            # Check rate limit
            await self.rate_limiter.check_limit()
        except asyncio.TimeoutError:
            return TaggingResult(
                problem_id=problem_id,
                success=False,
                error="Rate limit exceeded - please try again later"
            )

        try:
            # Construct the prompt
            prompt = self._build_prompt(problem_statement, solution_content, year)

            # Call Gemini API
            logger.info(f"Tagging problem {problem_id}...")
            response_text = await self._call_gemini(prompt)

            # Parse response
            metadata = self._parse_response(response_text)

            logger.info(f"Successfully tagged problem {problem_id} with confidence {metadata.confidence_score}")

            return TaggingResult(
                problem_id=problem_id,
                success=True,
                metadata=metadata,
                tokens_used=self._estimate_tokens(prompt, response_text),
                tagged_at=datetime.utcnow()
            )

        except GeminiCastError as e:
            logger.error(f"Failed to parse response for problem {problem_id}: {str(e)}")
            return TaggingResult(
                problem_id=problem_id,
                success=False,
                error=f"Failed to parse AI response: {str(e)}"
            )
        except GeminiRateLimitError as e:
            logger.warning(f"Rate limit for problem {problem_id}: {str(e)}")
            return TaggingResult(
                problem_id=problem_id,
                success=False,
                error="Rate limit exceeded"
            )
        except Exception as e:
            logger.error(f"Unexpected error tagging problem {problem_id}: {str(e)}")
            return TaggingResult(
                problem_id=problem_id,
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    def _build_prompt(
        self,
        problem_statement: str,
        solution_content: Optional[str] = None,
        year: Optional[int] = None
    ) -> str:
        """Build the user prompt for the AI."""
        prompt = f"Problem:\n{problem_statement}\n"

        if solution_content:
            prompt += f"\nSolution:\n{solution_content}\n"

        if year:
            prompt += f"\nContext: This problem is from {year}.\n"

        prompt += "\nProvide the structured JSON classification."
        return prompt

    async def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API and return the raw text output."""
        try:
            if USE_GENAI:
                # using new google.genai client - run in executor to avoid blocking event loop
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config={
                            "system_instruction": SYSTEM_PROMPT,
                            "response_mime_type": "application/json",  # forces JSON output
                        }
                    )
                )
                if not response.text:
                    raise GeminiCastError("Empty response from Gemini")
                return response.text
            else:
                response = self.model.generate_content(prompt)
                if not response.text:
                    raise GeminiCastError("Empty response from Gemini")
                return response.text
        except Exception as e:
            if "429" in str(e) or "RATE_LIMIT" in str(e) or "503" in str(e):
                raise GeminiRateLimitError(f"Rate limit exceeded: {str(e)}")
            raise

    def _parse_response(self, response_text: str) -> AITagMetadata:
        """Parse JSON response from Gemini."""
        try:
            # Extract JSON from response (in case there's extra text)
            # Find the first { and last }
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise GeminiCastError(f"No JSON found in response: {response_text[:100]}")

            json_str = response_text[start_idx:end_idx]
            json_str = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', json_str)
            data = json.loads(json_str)

            # Validate against schema
            metadata = AITagMetadata(**data)
            return metadata

        except json.JSONDecodeError as e:
            raise GeminiCastError(f"Invalid JSON in response: {str(e)}")
        except ValueError as e:
            raise GeminiCastError(f"Invalid data structure: {str(e)}")

    def _estimate_tokens(self, prompt: str, response: str) -> int:
        """Rough estimation of tokens used."""
        # Gemini charges per 1K tokens
        # Average: ~4 characters per token
        total_chars = len(prompt) + len(response)
        return max(1, total_chars // 4)  # Minimum 1 token
