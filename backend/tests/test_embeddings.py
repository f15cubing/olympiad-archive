"""Unit tests for the embeddings helper (Phase C) — mocked, no network."""

import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from ai_tagging import embeddings as emb  # noqa: E402


def test_cosine_identical():
    assert emb.cosine_similarity([1, 0, 0], [1, 0, 0]) == 1.0


def test_cosine_orthogonal():
    assert emb.cosine_similarity([1, 0, 0], [0, 1, 0]) == 0.0


def test_cosine_degenerate():
    assert emb.cosine_similarity([], []) == 0.0
    assert emb.cosine_similarity([1, 2], [1, 2, 3]) == 0.0  # length mismatch
    assert emb.cosine_similarity([0, 0], [1, 1]) == 0.0     # zero vector


def test_embed_texts_batches(monkeypatch):
    fake = SimpleNamespace(models=SimpleNamespace(
        embed_content=lambda model, contents: SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.1, 0.2]) for _ in contents])))
    monkeypatch.setattr(emb, "_get_client", lambda: fake)
    assert emb.embed_texts(["a", "b"]) == [[0.1, 0.2], [0.1, 0.2]]
    assert emb.embed_query("x") == [0.1, 0.2]


def test_embed_empty_is_noop():
    assert emb.embed_texts([]) == []
