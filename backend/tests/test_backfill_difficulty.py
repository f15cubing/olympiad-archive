"""Unit tests for the difficulty backfill helper (scripts/backfill_difficulty.py).

These exercise ``choose_backfill_difficulty`` in isolation with fake problem objects
(SimpleNamespace) — no DB, no network. They cover source selection, the auto
precedence rule (Claude before Gemini), and defensive metadata reads.
"""

import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import backfill_difficulty as bd  # noqa: E402


def _problem(ai=None, claude=None):
    """A stand-in Problem carrying only the two AI metadata dicts we read."""
    return types.SimpleNamespace(ai_metadata=ai, claude_metadata=claude)


def test_claude_only():
    p = _problem(claude={"difficulty": 8})
    assert bd.choose_backfill_difficulty(p) == 8
    assert bd.choose_backfill_difficulty(p, source="claude") == 8


def test_gemini_only():
    p = _problem(ai={"difficulty": 5})
    assert bd.choose_backfill_difficulty(p) == 5
    assert bd.choose_backfill_difficulty(p, source="gemini") == 5


def test_auto_prefers_claude_when_both_present():
    p = _problem(ai={"difficulty": 5}, claude={"difficulty": 8})
    assert bd.choose_backfill_difficulty(p, source="auto") == 8


def test_neither_returns_none():
    p = _problem()
    assert bd.choose_backfill_difficulty(p) is None


def test_source_overrides_pick_the_named_model():
    p = _problem(ai={"difficulty": 5}, claude={"difficulty": 8})
    assert bd.choose_backfill_difficulty(p, source="gemini") == 5
    assert bd.choose_backfill_difficulty(p, source="claude") == 8


def test_named_source_does_not_fall_back():
    # asking for claude when only gemini has a value must NOT use gemini (and vice versa)
    assert bd.choose_backfill_difficulty(_problem(ai={"difficulty": 5}), source="claude") is None
    assert bd.choose_backfill_difficulty(_problem(claude={"difficulty": 8}), source="gemini") is None


def test_metadata_none_is_defensive():
    p = _problem(ai=None, claude=None)
    assert bd.choose_backfill_difficulty(p) is None
    assert bd.choose_backfill_difficulty(p, source="claude") is None
    assert bd.choose_backfill_difficulty(p, source="gemini") is None


def test_missing_difficulty_key_returns_none():
    # metadata present but without a "difficulty" key (e.g. only topics/confidence)
    p = _problem(claude={"topics": ["algebra"]}, ai={"confidence_score": 0.9})
    assert bd.choose_backfill_difficulty(p, source="claude") is None
    assert bd.choose_backfill_difficulty(p, source="gemini") is None
    assert bd.choose_backfill_difficulty(p, source="auto") is None


def test_auto_falls_back_to_gemini_when_claude_has_no_difficulty():
    p = _problem(ai={"difficulty": 6}, claude={"topics": ["nt"]})
    assert bd.choose_backfill_difficulty(p, source="auto") == 6


def test_non_int_difficulty_is_ignored():
    # a string / bool is bad data, not a difficulty -> None (never hits the Integer column)
    assert bd.choose_backfill_difficulty(_problem(claude={"difficulty": "hard"}), source="claude") is None
    assert bd.choose_backfill_difficulty(_problem(ai={"difficulty": True}), source="gemini") is None


def test_missing_attributes_are_tolerated():
    # a fake object lacking the metadata attributes entirely still yields None
    assert bd.choose_backfill_difficulty(types.SimpleNamespace()) is None
