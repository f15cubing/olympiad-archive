"""Controlled tag vocabulary and normalization.

Bulk AI tagging creates a `tags` row for the field, each ``technique: <x>``, and each
raw topic string, deduped only by exact name match. Without normalization that explodes
the taxonomy into near-duplicates ("number theory" vs "Number Theory" vs "NT"). Every
tag name is funneled through :func:`normalize_tag` before it is looked up or created so
the stored vocabulary stays canonical.

Naming scheme:
- **Field tags** are one of the four canonical Title-Case fields (``Algebra``,
  ``Geometry``, ``Number Theory``, ``Combinatorics``). A topic that names a field
  collapses into the field tag so there is exactly one row for it.
- **Technique tags** are namespaced ``technique: <lowercase>`` so they never collide
  with a same-named topic.
- **Topic tags** are lowercased, whitespace-collapsed plain strings.
"""

import re

# The four canonical fields, in Title Case, exactly as the frontend expects.
CANONICAL_FIELDS = ("Algebra", "Geometry", "Number Theory", "Combinatorics")

TECHNIQUE_PREFIX = "technique:"

# Aliases mapping a normalized (lowercased, stripped) form to a canonical field.
_FIELD_ALIASES = {
    "algebra": "Algebra",
    "alg": "Algebra",
    "geometry": "Geometry",
    "geo": "Geometry",
    "number theory": "Number Theory",
    "numbertheory": "Number Theory",
    "nt": "Number Theory",
    "combinatorics": "Combinatorics",
    "combinatorial": "Combinatorics",
    "combo": "Combinatorics",
    "combi": "Combinatorics",
    "comb": "Combinatorics",
}

# Aliases mapping a normalized technique/topic form to its preferred spelling.
# Keep entries lowercase; values are the canonical lowercase form.
_ALIASES = {
    # techniques
    "php": "pigeonhole",
    "pigeonhole principle": "pigeonhole",
    "pigeon hole": "pigeonhole",
    "mod arithmetic": "modular arithmetic",
    "modular arith": "modular arithmetic",
    "modulo arithmetic": "modular arithmetic",
    "vieta": "vieta's formulas",
    "vietas formulas": "vieta's formulas",
    "vieta's formula": "vieta's formulas",
    "induction proof": "induction",
    "proof by induction": "induction",
    "strong induction": "induction",
    "proof by contradiction": "contradiction",
    "bary": "barycentric coordinates",
    "barycentrics": "barycentric coordinates",
    "gen functions": "generating functions",
    "generating function": "generating functions",
    "graphs": "graph theory",
    "cauchy schwarz": "cauchy-schwarz",
    "cauchy-schwarz inequality": "cauchy-schwarz",
    "am gm": "am-gm",
    "am-gm inequality": "am-gm",
    "amgm": "am-gm",
    # topics
    "functional equation": "functional equations",
    "fe": "functional equations",
    "cyclic quadrilateral": "cyclic quadrilaterals",
    "inequality": "inequalities",
    "polynomial": "polynomials",
    "sequence": "sequences",
    "prime": "primes",
    "divisibility rules": "divisibility",
}

_WS = re.compile(r"\s+")


def _clean(raw: str) -> str:
    """Lowercase, strip, and collapse internal whitespace."""
    return _WS.sub(" ", raw.strip().lower())


def canonical_field(raw: str):
    """Return the canonical Title-Case field for ``raw``, or ``None`` if it isn't one."""
    return _FIELD_ALIASES.get(_clean(raw))


def _apply_alias(cleaned: str) -> str:
    """Resolve a cleaned technique/topic string through the alias map."""
    return _ALIASES.get(cleaned, cleaned)


def normalize_technique(raw: str) -> str:
    """Return the canonical, namespaced technique tag for ``raw``.

    Accepts either a bare technique ("induction") or an already-prefixed one
    ("technique: induction") and always returns ``technique: <canonical>``.
    """
    cleaned = _clean(raw)
    if cleaned.startswith(TECHNIQUE_PREFIX):
        cleaned = cleaned[len(TECHNIQUE_PREFIX):].strip()
    return f"{TECHNIQUE_PREFIX} {_apply_alias(cleaned)}"


def normalize_topic(raw: str) -> str:
    """Return the canonical topic tag for ``raw`` (lowercased, aliased)."""
    return _apply_alias(_clean(raw))


def normalize_tag(raw: str) -> str:
    """Normalize an arbitrary tag name to its canonical stored form.

    Dispatches by shape:
    - ``technique: ...`` -> canonical namespaced technique.
    - a field name/alias (in any casing, whether it arrived as a field or a topic)
      -> the canonical Title-Case field.
    - anything else -> a canonical topic.
    """
    cleaned = _clean(raw)
    if cleaned.startswith(TECHNIQUE_PREFIX):
        return normalize_technique(raw)
    field = _FIELD_ALIASES.get(cleaned)
    if field is not None:
        return field
    return _apply_alias(cleaned)
