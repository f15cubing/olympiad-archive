# Plan: Populating the Archive

Goal: move from one hand-written sample problem (`backend/seed.py`) to a real, sizable,
well-tagged corpus of olympiad problems and solutions — without corrupting the tag
taxonomy or the data model along the way.

## Data model recap (what we're filling)
`Competition (name, country, url)` → `Problem (year, problem_number, statement[LaTeX],
author?, difficulty 1–10, source_url, ai_metadata JSON, tagged_at)` → `Solution
(content[LaTeX], author)`, plus a many-to-many `Tag` via `problem_tags`
(`backend/models.py`). Ingest happens through `POST /problems` etc., or directly in a
script using the ORM.

## ⚠️ Licensing / copyright — decide up front
Competition **problem statements** are generally freely reproducible (they're published
facts), but **solutions** — especially write-ups from AoPS, books, or handouts — are
often copyrighted. Before scraping/importing solutions at scale, decide the policy:
official solutions only, link-outs instead of copies, original write-ups, or explicit
permission. This choice drives which sources are usable. Store `source_url` for
attribution on everything.

## Code gaps to close before bulk loading
1. **No uniqueness constraint** on `(competition_id, year, problem_number)`. Re-running
   an import would duplicate problems. Add a unique constraint (+ Alembic migration) and
   make the importer **upsert** on that key.
2. **Tag taxonomy explosion.** AI tagging (`db_integration.py:85`) creates a `tags` row
   for the field, each `technique:{x}`, and each raw topic string, deduped only by exact
   name match. Bulk-tagging thousands of problems will produce hundreds of near-duplicate
   tags ("number theory" vs "Number Theory" vs "NT"). Add a **controlled vocabulary +
   normalization map** (lowercase, alias table) applied before writing tags.
3. **Difficulty is overwritten** by AI tagging (`db_integration.py`). If you import a
   curated difficulty, decide precedence (keep human value, or store AI difficulty only
   in `ai_metadata`). Don't let bulk tagging silently clobber curated ratings.
4. **No bulk import script.** `seed.py` is a one-off. Build a real importer (below).

## The importer (new `scripts/import_problems.py`)
- **Input:** a canonical, reviewable format — one JSON/YAML file per competition-year:
  ```yaml
  competition: {name: IMO, country: International, url: https://imo-official.org}
  year: 2024
  problems:
    - number: 1
      statement: "Let $a,b,c$ be positive reals ..."   # KaTeX-safe LaTeX
      author: "..."
      difficulty: 3
      source_url: "..."
      solutions:
        - author: "Official"
          content: "..."
  ```
- **Behavior:** get-or-create competition and tags; upsert problems by
  `(competition, year, number)`; attach solutions; idempotent and resumable; logs a
  summary (created/updated/skipped). Runs against the ORM directly (bypasses the 50-ID
  API caps).
- **Dry-run mode** that validates without writing.

## LaTeX validation (must-have for a KaTeX frontend)
The frontend renders with **KaTeX**, which supports only a subset of LaTeX. Add a
validation step in the importer that renders each `statement`/`content` with `katex`
(headless, `throwOnError`) and flags anything that won't render — otherwise problems
silently show as broken math in the UI. Maintain a small macro/normalization pass for
common constructs KaTeX rejects.

## Sourcing strategies (pick per licensing decision)
1. **Curated structured files (highest quality, slowest).** Hand-author the YAML per
   contest-year. Best for a flagship set (e.g., IMO 2000–2024, Putnam, USAMO).
2. **Existing open datasets (fastest coverage).** Several public math-olympiad datasets
   exist (e.g., OlympiadBench, and MATH/miniF2F-style collections on Hugging Face).
   Write per-dataset adapters that map their fields → the canonical import format.
   Verify license compatibility for each.
3. **Scraping (medium).** AoPS contest collections store fairly clean LaTeX; official
   sites (IMO, national olympiads) publish PDFs/pages. Scraping needs an extractor +
   heavy LaTeX cleanup + the licensing check above. Highest effort, most fragile.

Recommended: start with (1) for a curated core, layer in (2) for breadth, treat (3) as
a last resort per source.

## AI tagging at scale
- After import, tag with the **CLI** `tag_problems.py`, not the API. The CLI reuses one
  `AITaggerService`/rate limiter; the API rebuilds the limiter per request, so
  cross-request throttling isn't enforced (`tagging_service.py`, `rate_limiter.py`).
- Throughput: `REQUESTS_PER_MINUTE=25`, `BATCH_SIZE=10` (`config.py`) → ~1,500
  problems/hour, bounded by the Gemini free-tier quota. Plan runs accordingly; the CLI
  re-queries untagged each loop so it's resumable.
- Apply the tag-normalization layer (gap #2) either inside `_get_or_create_tag` or as a
  post-tagging cleanup pass that merges alias tags.
- Spot-check a sample of AI difficulty/topics against known values before trusting them.

## Quality control
- Dedup check (relies on the new unique constraint).
- Render-validation report (KaTeX failures) reviewed before publish.
- Coverage report: problems per competition/year, % with ≥1 solution, % tagged.
- Flag problems missing solutions or difficulty for follow-up.

## Suggested phasing / DoD
1. **Schema + importer** — add the unique constraint + migration; build
   `import_problems.py` with dry-run, upsert, and KaTeX validation.
2. **Pilot** — import one flagship set (e.g., IMO 2015–2024), run tagging with the
   normalization layer, review rendering and tags end-to-end in the UI.
3. **Normalize taxonomy** — lock a controlled tag vocabulary from the pilot's output.
4. **Scale** — add dataset adapters and/or more curated files; back up the DB before
   each bulk run; import into staging first.
5. **Ongoing** — a documented "add a contest-year" workflow (drop a YAML file, run the
   importer, run tagging).

**Done when:** the importer is idempotent and KaTeX-validated, a pilot corpus renders
and searches correctly in the UI, tags are normalized (no near-duplicates), and adding a
new contest-year is a single documented command.
