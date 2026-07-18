"""Tests for hard-LaTeX repair (Work item D.2) — Claude fully mocked, no network/spend."""

import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ai_tagging import latex_repair  # noqa: E402
from ai_tagging.latex_repair import repair_latex  # noqa: E402
from ai_tagging.config import CLAUDE_MODEL  # noqa: E402

# The KaTeX validator (Node) is optional; gate the real-validation assertions on it.
try:
    from import_problems import katex_available, run_katex_check  # noqa: E402
except Exception:  # pragma: no cover - scripts import awkward
    run_katex_check = None

    def katex_available() -> bool:
        return False


def _resp(text: str):
    """A fake Anthropic message response with a single text block (see test_claude_tagging)."""
    return types.SimpleNamespace(
        content=[types.SimpleNamespace(type="text", text=text)],
        usage=types.SimpleNamespace(input_tokens=10, output_tokens=10),
    )


def _mock_claude(monkeypatch, reply: str) -> AsyncMock:
    """Patch latex_repair.ClaudeClient so repair_latex talks to an AsyncMock, not the network."""
    create = AsyncMock(return_value=_resp(reply))
    fake_client = types.SimpleNamespace(
        client=types.SimpleNamespace(messages=types.SimpleNamespace(create=create))
    )
    monkeypatch.setattr(latex_repair, "ClaudeClient", MagicMock(return_value=fake_client))
    return create


# ------------------------------------------------------------------- repair_latex (mocked)
async def test_repair_latex_returns_mocked_fix(monkeypatch):
    create = _mock_claude(monkeypatch, "Then $x^2+y^2=z^2$ holds")

    out = await repair_latex("Then $$x^2+y^2=z^2$$ holds")

    assert out == "Then $x^2+y^2=z^2$ holds"     # returns the mocked repaired text
    assert create.await_count == 1                # and actually made the Claude call
    kwargs = create.call_args.kwargs
    assert kwargs["model"] == CLAUDE_MODEL
    assert kwargs["max_tokens"] == 2048
    assert "thinking" not in kwargs               # gateway 403s on thinking
    assert "temperature" not in kwargs            # rejected on 4.7+
    # the original text is handed to the model
    assert "Then $$x^2+y^2=z^2$$ holds" in kwargs["messages"][0]["content"]


async def test_repair_latex_includes_errors_in_prompt(monkeypatch):
    create = _mock_claude(monkeypatch, "$a+b$")

    out = await repair_latex("$a+b", errors=["1 unbalanced or multiline '$' delimiter(s)"])

    assert out == "$a+b$"
    content = create.call_args.kwargs["messages"][0]["content"]
    assert "$a+b" in content                       # original text present
    assert "unbalanced or multiline" in content    # supplied errors present


# ----------------------------------------------------------- real KaTeX round-trip (gated)
requires_katex = pytest.mark.skipif(
    not katex_available(), reason="node/katex not installed (run npm install in scripts/)"
)


@requires_katex
def test_synthetic_bad_latex_fails_then_repaired_passes():
    # NB: this checker only validates math inside `$...$` (plus stray `$`), so an inline
    # `$$a+b$$` degenerates to valid empty-math and does NOT fail. Use genuinely-broken
    # synthetic LaTeX that exercises the documented repair rules instead.
    # 1) `\begin{align}` is rejected by KaTeX; `\begin{aligned}` is the safe form.
    assert "bad" in run_katex_check([{"id": "bad", "text": r"$\begin{align} x&=1 \end{align}$"}])
    assert "ok" not in run_katex_check(
        [{"id": "ok", "text": r"$\begin{aligned} x&=1 \end{aligned}$"}]
    )
    # 2) an unbalanced single `$` fails; balancing it (a repair output) passes.
    assert "bad" in run_katex_check([{"id": "bad", "text": "$a+b"}])
    assert "ok" not in run_katex_check([{"id": "ok", "text": "$a+b$"}])
