# Plan: Test Suite

Goal: a fast, reliable, CI-gated test suite covering the backend API, the AI-tagging
pipeline (without hitting the real Gemini API), and the frontend, so changes can be
merged with confidence.

## Where we are today

**Backend** (`backend/tests/`)
- `test_api.py` — solid CRUD coverage over competitions, problems, tags, solutions
  via an httpx `AsyncClient` against an in-memory SQLite DB (`conftest.py`).
- `test_ai_client.py` — 2 tests for `GeminiClient` construction.

**Frontend** (`frontend/src/__tests__/`)
- Vitest + React Testing Library + MSW + jsdom.
- Tests for `ProblemList`, `YearList`, `CompetitionList` (render, admin add/delete, forms).

**Not covered:** search, tag lookup, the whole `/tagging` pipeline and `ai_tagging/`
module, `ProblemDetail`, `Search`, `taggingService`, and error/loading states.
There is **no CI** running any of this.

## Problems to fix first (these block a clean `pytest`)

1. **Inconsistent import roots.** `conftest.py:6-8`, `main.py`, and the routers use
   bare imports (`from models import ...`), so they require `backend/` on `sys.path`.
   But `tests/test_ai_client.py:3` uses `from backend.ai_tagging...`, which requires
   the repo root. No single working directory satisfies both — today it only collects
   with `PYTHONPATH=repo_root:backend`.
   **Fix:** standardize on the backend-rooted convention (matches `main.py` and
   `tag_problems.py`'s runtime assumptions). Change `test_ai_client.py` to
   `from ai_tagging.gemini_client import GeminiClient`, and pin the path in config so
   no `PYTHONPATH` juggling is needed:
   ```ini
   # backend/pytest.ini
   [pytest]
   asyncio_mode = auto
   pythonpath = .        # run from backend/, so `models`, `ai_tagging`, etc. resolve
   ```
   Then `cd backend && pytest` "just works". (Alternative: make `backend` a real
   package with `__init__.py` and use `backend.` everywhere — larger diff, touches
   every router's imports and `main.py`. Prefer the `pythonpath` fix.)

2. **`test_gemini_client_accepts_env_key` is broken by import-time config.**
   `ai_tagging/config.py:7` reads `GEMINI_API_KEY` at import, so setting the env var
   inside the test (after the module is already imported) has no effect and the client
   still raises "not provided". **Fix:** either have `GeminiClient` read
   `os.getenv("GEMINI_API_KEY")` at init instead of importing the cached constant, or
   `monkeypatch.setattr("ai_tagging.config.GEMINI_API_KEY", "fake-key")` in the test.
   Prefer the runtime-read fix — it also makes the app pick up the key correctly.

3. **Missing test dependencies.** `pytest`, `pytest-asyncio`, and (frontend already has
   it) MSW are not in any manifest. Add `backend/requirements-dev.txt`:
   ```
   pytest
   pytest-asyncio
   httpx            # already runtime, but pin here too for clarity
   coverage[toml]
   ```

4. **Test DB isolation is leaky.** `conftest.py:18-25` uses one **session-scoped**
   in-memory engine and creates the schema once. The API endpoints call
   `commit()`, so rows committed in one test persist into later tests (the per-test
   `session.rollback()` in `async_session` doesn't undo committed data). Tests pass
   today only because they create their own fixtures, but this is order-dependent and
   will bite. **Fix:** drop+recreate tables per test (function-scoped) or wrap each
   test in an outer transaction with a savepoint that's rolled back in teardown.

## Coverage to add

### Backend — API (extend `test_api.py` or split by resource)
- `GET /problems/search`: by `q`, by `tag`, by both, and empty result.
- `GET /problems/tag/{tag_name}` and `GET /problems/` list shape.
- 404s: get/update/delete non-existent problem; delete non-existent solution.
- 422 validation: missing required fields (`year`, `statement`), bad `difficulty` type.
- Duplicate tag → 400 (already covered) + competition delete behavior/cascade.
- `ai_metadata` round-trips through `ProblemResponse` serialization (schema test).

### Backend — AI tagging (new `tests/test_tagging.py`) — the biggest gap
Mock the network at the `GeminiClient` boundary so **no real API calls** happen:
- Patch `GeminiClient.tag_problem` to return a canned `AITagMetadata`.
- Assert `save_tagging_result` writes `ai_metadata`, sets `tagged_at`, updates
  `difficulty`, and creates/links `tags` rows (`db_integration.py:34,85`).
- `_get_or_create_tag` dedup: tagging two problems with the same topic yields one row.
- `get_untagged_problems` returns only rows with `ai_metadata IS NULL`.
- Router tests: `POST /tagging/{id}` → 404 for missing problem; `POST /tagging/batch`
  → 400 on empty and on >50 IDs; 404 if any ID missing (all with the client mocked).
- `rate_limiter.py` sliding-window unit test (fake clock / injected time source).

### Frontend (extend `__tests__/`)
- `ProblemDetail` — render problem + solutions, PUT edit, add/delete solution,
  auto-tag button calling `/tagging/{id}` (MSW-mocked).
- `Search` — query + tag filter, empty state.
- `services/taggingService.js` — `tagSingleProblem` / batch success + error paths.
- Loading and error states for at least one list component.

## CI (new `.github/workflows/ci.yml`)
Run on push + PR:
- **backend job**: setup Python 3.13 → `pip install -r backend/requirements.txt -r
  backend/requirements-dev.txt` → `cd backend && pytest --cov` → upload coverage.
- **frontend job**: setup Node → `npm ci` in `frontend/` → `npm run lint` →
  `npm run test -- --run --coverage`.
- Fail the PR on test failure; publish coverage summary.
- Mark any test that needs a real network/API with `@pytest.mark.skipif(not
  GEMINI_API_KEY)` so CI stays hermetic.

## Suggested phasing
1. **Unblock** — fix imports (#1), the env-key test (#2), add dev deps (#3), test DB
   isolation (#4). Outcome: `pytest` green from a clean checkout, no `PYTHONPATH` hacks.
2. **CI** — add the workflow so everything above is enforced.
3. **Backend coverage** — search/tag/validation/404s, then the tagging pipeline suite.
4. **Frontend coverage** — ProblemDetail, Search, taggingService, error states.
5. **Stretch** — Playwright end-to-end (browse → open problem → render KaTeX → search),
   coverage thresholds as a merge gate.

## Definition of done
- `pytest` and `npm test` both pass from a clean clone with documented commands.
- CI blocks merges on failure.
- The `/tagging` pipeline is tested with the Gemini client fully mocked.
- Backend line coverage ≥ ~80% on routers + `ai_tagging`; frontend components covered.
