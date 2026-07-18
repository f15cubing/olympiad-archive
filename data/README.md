# Archive source data

Canonical, reviewable problem data — **one YAML file per competition-year**. These files
are the source of truth for the corpus; the database is built from them by the importer,
so a bad edit shows up in review (a git diff) rather than as silently broken data.

Layout: `data/<competition>/<year>.yaml`, e.g. `data/imo/2024.yaml`.

## File format

```yaml
competition:
  name: IMO                       # get-or-created by name
  country: International           # optional
  url: https://www.imo-official.org   # optional
  description: ...                # optional
year: 2024
problems:
  - number: 1                     # required, unique within the file
    statement: |                  # required, KaTeX-safe LaTeX (see below)
      Determine all real numbers $\alpha$ such that ...
    difficulty: 4                 # optional 1-10; curated value WINS over AI tagging
    author: "..."                 # optional
    source_url: https://...       # attribution; always set
    tags: [Algebra, "technique: induction"]   # optional; normalized on import
    solutions:                    # optional (see licensing)
      - author: Official
        content: |
          ...
```

## Writing math (KaTeX rules)

The frontend renders inline math wrapped in single `$...$` delimiters and nothing else
(`frontend/src/components/ProblemDetail.jsx`). So:

- Wrap **every** piece of math in `$...$`. Bare LaTeX outside `$...$` renders literally.
- **No** `$$...$$`, `\[...\]`, or `\(...\)` — they are not supported by the renderer.
- Keep each `$...$` span on a single line (the renderer's regex won't match across newlines).
- Use `aligned`, not `align`, inside math (KaTeX rejects `align`).

The importer validates all math with `scripts/katex_check.mjs` before writing, so anything
that won't render is caught up front.

## Licensing

Problem **statements** are published facts and are reproduced here with a `source_url`.
**Solutions** are official-only or link-outs — do not copy AoPS/book write-ups. Original
AI-generated alternate solutions are stored labeled `author: "AI (Claude)"`.

## Add a contest-year (the one command)

1. Drop a new `data/<competition>/<year>.yaml` (KaTeX-safe, format above).
2. Dry-run to validate: `python scripts/import_problems.py data/<competition>/<year>.yaml --dry-run`
3. Import: `python scripts/import_problems.py data/<competition>/<year>.yaml`
4. Tag (Gemini): `python tag_problems.py`

Re-running the importer is safe — it upserts on `(competition, year, problem_number)`.
