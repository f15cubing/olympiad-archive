"""Tests for the semantic /problems/search endpoint (Phase C) — mocked embeddings."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from ai_tagging import embeddings as emb  # noqa: E402
from models import Competition, Problem  # noqa: E402


async def _seed(session, rows):
    comp = Competition(name="IMO")
    session.add(comp)
    await session.flush()
    for i, (statement, vec) in enumerate(rows, 1):
        session.add(Problem(competition_id=comp.id, year=2000 + i, problem_number=1,
                            statement=statement, embedding=vec,
                            embedding_model="test" if vec else None))
    await session.flush()
    return comp


async def test_semantic_search_ranks_by_similarity(client, async_session, monkeypatch):
    await _seed(async_session, [
        ("problem about alpha", [1.0, 0.0, 0.0]),
        ("problem about beta", [0.0, 1.0, 0.0]),
        ("problem about gamma", [0.0, 0.0, 1.0]),
    ])
    monkeypatch.setattr(emb, "embed_query", lambda q, model=None: [0.9, 0.1, 0.0])

    resp = await client.get("/problems/search?q=anything")
    assert resp.status_code == 200
    results = resp.json()
    assert results[0]["statement"] == "problem about alpha"  # closest to the query vector


async def test_semantic_search_falls_back_to_keyword_on_error(client, async_session, monkeypatch):
    # a problem WITH an embedding, but the embed call errors -> keyword fallback path
    await _seed(async_session, [("a unique pigeonhole problem", [1.0, 0.0, 0.0])])

    def boom(*a, **k):
        raise RuntimeError("embeddings down")
    monkeypatch.setattr(emb, "embed_query", boom)

    resp = await client.get("/problems/search?q=pigeonhole")
    assert resp.status_code == 200
    assert any("pigeonhole" in p["statement"] for p in resp.json())


async def test_search_no_query_returns_all(client, async_session):
    await _seed(async_session, [("problem one", None), ("problem two", None)])
    resp = await client.get("/problems/search")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_problem_response_exposes_claude_metadata(client, async_session):
    comp = Competition(name="IMO")
    async_session.add(comp)
    await async_session.flush()
    p = Problem(competition_id=comp.id, year=2024, problem_number=1, statement="x",
                claude_metadata={"analysis": "reasoning here", "field": "Algebra",
                                 "difficulty": 5, "techniques": ["induction"],
                                 "topics": ["sequences", "inequalities"], "confidence_score": 7})
    async_session.add(p)
    await async_session.flush()
    resp = await client.get(f"/problems/{p.id}")
    assert resp.status_code == 200
    cm = resp.json()["claude_metadata"]
    assert cm["field"] == "Algebra" and cm["techniques"] == ["induction"]
