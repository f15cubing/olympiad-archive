"""Generate an original alternate solution for a competition problem with Claude.

Companion to :mod:`ai_tagging.claude_client` (Work item D.3). It reuses that client's
Anthropic connection — same TrueFoundry-gateway quirks: Bearer ``ANTHROPIC_AUTH_TOKEN``,
forwarded ``ANTHROPIC_CUSTOM_HEADERS``, and NO ``thinking`` param (the gateway 403s on it)
— but asks for prose + inline-math *solution text* instead of a structured tool call.

The system prompt constrains every bit of math to single-line inline ``$...$`` so the
result passes the same KaTeX gate the importer and frontend use (scripts/katex_check.mjs):
no ``$$``/``\\[ \\]`` display math, one ``$...$`` per line, ``\\begin{aligned}`` never
``align``.
"""

import logging
from typing import Optional

from .claude_client import ClaudeClient
from .config import CLAUDE_MODEL

logger = logging.getLogger(__name__)

# Max tokens for one written-out solution. Generous enough for a full olympiad write-up
# without inviting runaway spend.
MAX_SOLUTION_TOKENS = 2048

SOLUTION_SYSTEM_PROMPT = """Role: You are an expert Math Olympiad problem-solver and author.

Write ONE clear, correct, and ORIGINAL solution to the competition problem provided. The
solution must be self-contained and rigorous: explain the key ideas in prose and justify
every step, the way a well-written olympiad solution reads. Do not merely restate the
problem or give only an answer.

Formatting rules (STRICT — the write-up is rendered with KaTeX):
- Write ALL mathematics as inline math delimited by single dollar signs, e.g. $a^2 + b^2$.
- Do NOT use display math: no $$ ... $$, no \\[ ... \\], no \\( ... \\).
- Keep each $...$ span on a SINGLE line; never let one wrap across lines.
- For multi-step derivations use $\\begin{aligned} ... \\end{aligned}$ (NEVER `align`),
  kept on one line, or split the work into several separate inline-math expressions.
- Everything that is not mathematics should be plain prose; no Markdown headings needed.

Output ONLY the solution text — no preamble, no restatement of the problem, no meta commentary."""


class ClaudeSolutionClient:
    """Generates original, KaTeX-safe alternate solutions via Claude.

    Composes a :class:`ClaudeClient` purely to borrow its Anthropic client (and the
    gateway auth/header handling); the tagging tool schema is not used here.
    """

    def __init__(self, auth_token: Optional[str] = None, base_url: Optional[str] = None,
                 model: Optional[str] = None):
        # Reuse ClaudeClient's constructor for the AsyncAnthropic client + gateway headers.
        self._tagging_client = ClaudeClient(auth_token=auth_token, base_url=base_url, model=model)
        self.client = self._tagging_client.client
        self.model = model or CLAUDE_MODEL
        logger.info(f"Initialized ClaudeSolutionClient (model={self.model})")

    async def generate_solution(
        self,
        problem_statement: str,
        year: Optional[int] = None,
    ) -> Optional[str]:
        """Ask Claude for one original, KaTeX-safe solution to ``problem_statement``.

        Returns the solution text, or ``None`` if the model returns nothing usable
        (empty response or a refusal) so the caller can skip it rather than save junk.
        """
        prompt = self._build_prompt(problem_statement, year)
        resp = await self.client.messages.create(
            model=self.model,
            max_tokens=MAX_SOLUTION_TOKENS,
            system=SOLUTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            # NB: no `thinking` (gateway 403s) and no sampling params (rejected on 4.7+),
            # mirroring ClaudeClient.tag_problem.
        )

        if getattr(resp, "stop_reason", None) == "refusal":
            logger.warning("Claude refused to produce a solution")
            return None

        text = self._extract_text(resp)
        if not text:
            logger.warning("Claude returned an empty solution")
            return None
        return text

    @staticmethod
    def _build_prompt(problem_statement: str, year: Optional[int] = None) -> str:
        prompt = f"Competition problem:\n{problem_statement}\n"
        if year:
            prompt += f"\nContext: this problem is from {year}.\n"
        prompt += "\nWrite one original, self-contained solution following the formatting rules."
        return prompt

    @staticmethod
    def _extract_text(resp) -> str:
        """Concatenate the text blocks of a messages response (ignores non-text blocks)."""
        parts = [
            getattr(block, "text", "") or ""
            for block in (getattr(resp, "content", None) or [])
            if getattr(block, "type", None) == "text"
        ]
        return "".join(parts).strip()
