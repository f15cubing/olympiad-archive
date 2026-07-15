# Project Plans

Grounded, phased plans for the next stages of Olympiad Archive. Each references the
current code (`file:line`) so it stays actionable.

- [01 — Test Suite](01-test-suite.md): unblock `pytest`, mock the tagging pipeline, add
  frontend coverage, gate everything with CI.
- [02 — Deployment](02-deployment.md): env-config the app, add auth on writes, migrate
  to Postgres, containerize, and deploy static frontend + API + managed DB.
- [03 — Populating the Archive](03-populating-the-archive.md): a canonical import format,
  an idempotent KaTeX-validated importer, sourcing/licensing strategy, and AI tagging
  at scale without exploding the tag taxonomy.

Cross-cutting prerequisites that show up in more than one plan: fix the backend import
inconsistency (test plan), fix the UTF-16 `requirements.txt` and hardcoded config
(deploy plan), and add a `(competition, year, problem_number)` unique constraint
(populate plan).
