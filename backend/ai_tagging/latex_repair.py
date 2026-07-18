"""Hard-LaTeX repair (Work item D.2).

Route LaTeX that fails KaTeX validation through Claude to get a KaTeX-safe
rewrite, then re-validate. The frontend renders math only as inline ``$...$``
(scripts/katex_check.mjs), so the repaired text must:

- put ALL math in single ``$...$`` (no ``$$...$$``, no ``\\[...\\]``),
- keep each ``$...$`` on one line, and
- use ``\\begin{aligned}`` rather than ``\\begin{align}``.

The Claude call reuses :class:`ClaudeClient` for the gateway/auth wiring and,
like tagging, omits the ``thinking`` parameter and any sampling params — the
gateway 403s on the former and rejects the latter on 4.7+ models.
"""

import logging
import sys
from pathlib import Path

from .claude_client import ClaudeClient
from .config import CLAUDE_MODEL

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]

REPAIR_SYSTEM_PROMPT = (
    "You convert LaTeX to a KaTeX-safe subset for a frontend that renders only "
    "inline `$...$` math. Rewrite the given text so ALL math is inline `$...$` "
    "(convert `$$...$$` and `\\[...\\]` to `$...$`, keep each `$...$` on one "
    "line, replace `align` with `aligned`), preserving the exact mathematical "
    "meaning and wording. Return ONLY the rewritten text."
)


def _build_user_message(text: str, errors: list[str] | None) -> str:
    """Compose the user turn: the KaTeX errors (if any) plus the text to fix."""
    parts: list[str] = []
    if errors:
        parts.append("The KaTeX validator reported these errors:")
        parts.extend(f"- {e}" for e in errors)
        parts.append("")
    parts.append(
        "Rewrite the following text so all math is KaTeX-safe inline `$...$`, "
        "preserving the meaning and wording exactly:"
    )
    parts.append("")
    parts.append(text)
    return "\n".join(parts)


def _extract_text(resp) -> str:
    """Concatenate the text blocks of an Anthropic message response."""
    return "".join(
        getattr(block, "text", "") or ""
        for block in (getattr(resp, "content", None) or [])
        if getattr(block, "type", None) == "text"
    )


async def repair_latex(text: str, errors: list[str] | None = None) -> str:
    """Ask Claude to rewrite ``text`` into KaTeX-safe inline ``$...$`` math.

    Reuses :class:`ClaudeClient` for the gateway/auth wiring and returns the
    rewritten text pulled from the response's text blocks. Callers should
    re-validate the result with KaTeX (see scripts/repair_latex.py).
    """
    client = ClaudeClient()
    resp = await client.client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=REPAIR_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_message(text, errors)}],
        # NB: no `thinking` (gateway 403s) and no sampling params (rejected on 4.7+).
    )
    repaired = _extract_text(resp).strip()
    logger.debug("repaired latex (%d -> %d chars)", len(text), len(repaired))
    return repaired


def find_katex_failures(items: list[dict]) -> dict[str, list[dict]]:
    """Return ``{id: [error, ...]}`` for the failing ``[{"id","text"}]`` items.

    Thin, defensive wrapper over ``scripts/import_problems.run_katex_check`` — the
    same validator the importer and frontend use. The scripts module is imported
    lazily via a sys.path insert (mirroring backend/tests/test_import_problems.py)
    because it pulls in the backend package. Returns ``{}`` if the scripts module
    or Node/KaTeX is unavailable, so "no checker" reads as "nothing to repair"
    rather than raising.
    """
    try:
        scripts_dir = REPO_ROOT / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from import_problems import katex_available, run_katex_check
    except Exception as exc:  # import awkward / scripts not importable
        logger.warning("KaTeX helpers unavailable: %s", exc)
        return {}
    if not katex_available():
        logger.warning("Node/KaTeX not available; skipping KaTeX check")
        return {}
    return run_katex_check(items)
