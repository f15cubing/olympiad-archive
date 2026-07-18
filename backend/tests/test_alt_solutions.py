"""Tests for the Claude alternate-solution feature (Work item D.3) — all mocked, no spend.

Covers ClaudeSolutionClient.generate_solution (fake Anthropic response, no network) and the
scripts/generate_alt_solutions.py per-problem flow (idempotency, KaTeX gate, AI-author label).
"""

import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT))

from ai_tagging.claude_solution import ClaudeSolutionClient  # noqa: E402
from import_problems import run_katex_check, katex_available  # noqa: E402
import generate_alt_solutions as gas  # noqa: E402
# Use the same class registry the script uses so ORM identity is consistent; the fixture's
# tables (created from top-level models.Base) share the table names, so writes work.
import backend.models as bm  # noqa: E402

# A KaTeX-safe solution: all math is single-line inline $...$.
SOLUTION_TEXT = "By AM-GM, $a+b \\ge 2\\sqrt{ab}$, so the result follows."

katex_needed = pytest.mark.skipif(
    not katex_available(), reason="Node/katex not installed in scripts/"
)


# ------------------------------------------------------------------- mock plumbing
def _resp(blocks, stop_reason="end_turn"):
    return types.SimpleNamespace(
        content=blocks,
        stop_reason=stop_reason,
        usage=types.SimpleNamespace(input_tokens=10, output_tokens=20),
    )


def _text_block(text):
    return types.SimpleNamespace(type="text", text=text)


def _client_returning(*blocks, stop_reason="end_turn"):
    """A ClaudeSolutionClient whose messages.create is a fake returning `blocks`."""
    client = ClaudeSolutionClient(auth_token="dummy")
    create = AsyncMock(return_value=_resp(list(blocks), stop_reason=stop_reason))
    client.client = types.SimpleNamespace(messages=types.SimpleNamespace(create=create))
    return client, create


# ----------------------------------------------------------------- generate_solution
async def test_generate_solution_returns_text_and_omits_thinking():
    client, create = _client_returning(_text_block(SOLUTION_TEXT))

    out = await client.generate_solution("Prove $a+b \\ge 2\\sqrt{ab}$ for $a,b>0$.", year=2021)

    assert out == SOLUTION_TEXT
    kwargs = create.call_args.kwargs
    assert kwargs["model"] == "claude-opus-4-8"
    assert kwargs["max_tokens"] == 2048
    assert kwargs["system"]                  # a system prompt was sent
    assert "thinking" not in kwargs          # gateway 403s on thinking
    assert "temperature" not in kwargs       # no sampling params (rejected on 4.7+)


@katex_needed
async def test_generated_solution_is_katex_valid():
    client, _ = _client_returning(_text_block(SOLUTION_TEXT))
    out = await client.generate_solution("Prove $a+b \\ge 2\\sqrt{ab}$.")
    assert gas.katex_errors(out) == []           # renders cleanly the way the frontend does
    assert run_katex_check([{"id": "s", "text": out}]) == {}


async def test_generate_solution_none_on_empty():
    client, _ = _client_returning(_text_block("   "))
    assert await client.generate_solution("x") is None


async def test_generate_solution_none_on_refusal():
    client, _ = _client_returning(_text_block("I can't help with that."), stop_reason="refusal")
    assert await client.generate_solution("x") is None


# --------------------------------------------------------------- process_problem (save)
async def _make_problem(session, number, statement="x"):
    comp = bm.Competition(name="IMO")
    session.add(comp)
    await session.flush()
    prob = bm.Problem(
        competition_id=comp.id, year=2021, problem_number=number, statement=statement
    )
    session.add(prob)
    await session.flush()
    return prob


async def test_process_problem_saves_ai_authored_solution(async_session):
    prob = await _make_problem(async_session, 1, "Prove $a+b \\ge 2\\sqrt{ab}$ for $a,b>0$.")
    client, create = _client_returning(_text_block(SOLUTION_TEXT))

    outcome = await gas.process_problem(async_session, client, prob.id, check_katex=False)

    assert outcome == "generated"
    create.assert_awaited_once()
    sol = (
        await async_session.execute(
            select(bm.Solution).where(bm.Solution.problem_id == prob.id)
        )
    ).scalars().first()
    assert sol is not None
    assert sol.author == "AI (Claude)"
    assert sol.content == SOLUTION_TEXT


async def test_process_problem_is_idempotent(async_session):
    prob = await _make_problem(async_session, 2)
    async_session.add(bm.Solution(problem_id=prob.id, content="prior", author="AI (Claude)"))
    await async_session.flush()

    client, create = _client_returning(_text_block(SOLUTION_TEXT))
    outcome = await gas.process_problem(async_session, client, prob.id, check_katex=False)

    assert outcome == "skipped"
    create.assert_not_called()  # already present → no API call, no spend
    rows = (
        await async_session.execute(
            select(bm.Solution).where(
                bm.Solution.problem_id == prob.id, bm.Solution.author == "AI (Claude)"
            )
        )
    ).scalars().all()
    assert len(rows) == 1  # not duplicated


async def test_process_problem_skips_missing(async_session):
    client, create = _client_returning(_text_block(SOLUTION_TEXT))
    outcome = await gas.process_problem(async_session, client, 9999, check_katex=False)
    assert outcome == "skipped"
    create.assert_not_called()


@katex_needed
async def test_process_problem_skips_broken_katex(async_session):
    prob = await _make_problem(async_session, 3)
    bad = "The value is $x + 1 which is positive."  # unbalanced '$' → KaTeX error
    client, _ = _client_returning(_text_block(bad))

    outcome = await gas.process_problem(async_session, client, prob.id, check_katex=True)

    assert outcome == "failed"
    rows = (
        await async_session.execute(
            select(bm.Solution).where(bm.Solution.problem_id == prob.id)
        )
    ).scalars().all()
    assert rows == []  # broken math is never saved
