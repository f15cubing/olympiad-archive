"""Tests for the Claude tagging provider (Phase D) — all mocked, no network/spend."""

import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from ai_tagging.claude_client import ClaudeClient, ClaudeCastError, _parse_custom_headers  # noqa: E402
from ai_tagging.schemas import AITagMetadata  # noqa: E402
from ai_tagging.db_integration import save_claude_tagging_result  # noqa: E402
from models import Competition, Problem  # noqa: E402

VALID = {
    "analysis": "A clean structured classification.",
    "field": "Algebra",
    "difficulty": 5,
    "techniques": ["Induction"],
    "topics": ["sequences", "inequalities"],
    "confidence_score": 8,
}


def _resp(blocks, in_tok=100, out_tok=50):
    return types.SimpleNamespace(
        content=blocks,
        usage=types.SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
    )


def _tool_block(data):
    return types.SimpleNamespace(type="tool_use", name="emit_classification", input=data)


def _text_block(text):
    return types.SimpleNamespace(type="text", text=text)


# ---------------------------------------------------------------- _extract_metadata
def test_extract_from_tool_use():
    md = ClaudeClient._extract_metadata(_resp([_tool_block(VALID)]))
    assert isinstance(md, AITagMetadata)
    assert md.field == "Algebra"
    assert md.techniques == ["induction"]  # schema lowercases


def test_extract_coerces_comma_strings():
    # Some responses emit techniques/topics as a comma string instead of a list.
    data = dict(VALID, techniques="induction, construction",
                topics="sequences, inequalities, primes")
    md = ClaudeClient._extract_metadata(_resp([_tool_block(data)]))
    assert md.techniques == ["induction", "construction"]
    assert md.topics == ["sequences", "inequalities", "primes"]


def test_extract_clamps_overlong_lists():
    data = dict(VALID, techniques=[f"t{i}" for i in range(15)],
                topics=[f"topic{i}" for i in range(12)])
    md = ClaudeClient._extract_metadata(_resp([_tool_block(data)]))
    assert len(md.techniques) == 10 and len(md.topics) == 7


def test_extract_json_text_fallback():
    import json
    md = ClaudeClient._extract_metadata(_resp([_text_block("noise " + json.dumps(VALID) + " end")]))
    assert md.confidence_score == 8


def test_extract_raises_on_garbage():
    with pytest.raises(ClaudeCastError):
        ClaudeClient._extract_metadata(_resp([_text_block("no json here")]))


# ------------------------------------------------------------- custom header parsing
def test_parse_custom_headers():
    assert _parse_custom_headers("x-tfy-api-key: abc123") == {"x-tfy-api-key": "abc123"}
    assert _parse_custom_headers("A: 1\nB: 2") == {"A": "1", "B": "2"}
    assert _parse_custom_headers("") == {}
    assert _parse_custom_headers(None) == {}


# --------------------------------------------------------------------- tag_problem
async def test_tag_problem_forces_tool_and_omits_thinking():
    client = ClaudeClient(auth_token="dummy")
    create = AsyncMock(return_value=_resp([_tool_block(VALID)]))
    client.client = types.SimpleNamespace(messages=types.SimpleNamespace(create=create))

    result = await client.tag_problem(problem_id=7, problem_statement="Prove $x>0$.", year=2024)

    assert result.success and result.metadata.field == "Algebra"
    assert result.tokens_used == 150
    kwargs = create.call_args.kwargs
    assert kwargs["tool_choice"] == {"type": "tool", "name": "emit_classification"}
    assert "thinking" not in kwargs          # gateway 403s on thinking
    assert "temperature" not in kwargs       # rejected on 4.7+
    assert kwargs["model"] == "claude-opus-4-8"


async def test_tag_problem_reports_parse_failure():
    client = ClaudeClient(auth_token="dummy")
    create = AsyncMock(return_value=_resp([_text_block("not json")]))
    client.client = types.SimpleNamespace(messages=types.SimpleNamespace(create=create))
    result = await client.tag_problem(problem_id=8, problem_statement="x")
    assert not result.success and "parse" in result.error.lower()


# ------------------------------------------------------------ non-destructive save
async def test_save_claude_is_nondestructive(async_session):
    comp = Competition(name="IMO")
    async_session.add(comp)
    await async_session.flush()
    prob = Problem(
        competition_id=comp.id, year=2024, problem_number=1, statement="x",
        difficulty=4, ai_metadata={"field": "Geometry", "difficulty": 9},
    )
    async_session.add(prob)
    await async_session.flush()

    await save_claude_tagging_result(async_session, prob.id, AITagMetadata(**VALID))

    refreshed = await async_session.get(Problem, prob.id)
    assert refreshed.claude_metadata["field"] == "Algebra"
    assert refreshed.claude_tagged_at is not None
    # Gemini's data and the curated difficulty are untouched
    assert refreshed.difficulty == 4
    assert refreshed.ai_metadata == {"field": "Geometry", "difficulty": 9}
