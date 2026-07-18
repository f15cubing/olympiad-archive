"""Base class + shared helpers for dataset adapters.

An adapter subclasses :class:`Adapter` and implements :meth:`parse`, returning a list of
:class:`YearFile` (one per competition-year). :meth:`emit` then validates each against the
importer schema, KaTeX-checks the math, and writes canonical YAML into ``data/``.

The shared :func:`normalize_statement` performs the "normalization pass" the archive plan
calls for: it turns common dataset LaTeX/markdown into the KaTeX-safe, inline-``$...$``-only
form the frontend renders (see data/README.md).
"""

import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

# import the importer's schema + KaTeX helpers (scripts/ is one level up)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from import_problems import FileSpec, katex_available, run_katex_check  # noqa: E402


# --------------------------------------------------------------------------- model
@dataclass
class CanonicalProblem:
    number: int
    statement: str
    difficulty: Optional[int] = None
    author: Optional[str] = None
    source_url: Optional[str] = None
    tags: list = field(default_factory=list)
    solutions: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {"number": self.number, "statement": self.statement}
        if self.difficulty is not None:
            d["difficulty"] = self.difficulty
        if self.author:
            d["author"] = self.author
        if self.source_url:
            d["source_url"] = self.source_url
        if self.tags:
            d["tags"] = self.tags
        if self.solutions:
            d["solutions"] = self.solutions
        return d


@dataclass
class YearFile:
    competition: dict  # {name, country?, url?, description?}
    year: int
    problems: list  # list[CanonicalProblem]
    header: Optional[str] = None  # provenance/license note, written as a leading comment

    def to_dict(self) -> dict:
        return {
            "competition": self.competition,
            "year": self.year,
            "problems": [p.to_dict() for p in sorted(self.problems, key=lambda x: x.number)],
        }


# -------------------------------------------------------------------- normalization
_DISPLAY_DD = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
_DISPLAY_BR = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)
_INLINE_PAREN = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
_INLINE_SPLIT = re.compile(r"(\$[^$]*\$)")
_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_ITALIC = re.compile(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", re.DOTALL)
_BULLET = re.compile(r"(?m)^([ \t]*)\*[ \t]+")
_MULTINEWLINE = re.compile(r"\n{3,}")


def _flatten(inner: str) -> str:
    return re.sub(r"\s*\n\s*", " ", inner.strip())


def _strip_markdown(text: str) -> str:
    """Remove markdown emphasis / normalize bullets in non-math text."""
    text = _BOLD.sub(r"\1", text)
    text = _ITALIC.sub(r"\1", text)
    text = _BULLET.sub(r"\1- ", text)  # "* item" -> "- item"
    return text


def normalize_statement(text: str) -> str:
    """Convert dataset LaTeX/markdown to the KaTeX-safe, inline-``$...$`` form.

    - ``$$...$$`` / ``\\[...\\]`` / ``\\(...\\)`` -> inline ``$...$`` (newlines flattened),
    - markdown ``**bold**`` / ``*italic*`` stripped, ``* bullets`` -> ``- bullets``,
      only outside math spans,
    - ``align`` environments -> ``aligned`` (KaTeX rejects bare ``align``).
    """
    text = _DISPLAY_DD.sub(lambda m: f"${_flatten(m.group(1))}$", text)
    text = _DISPLAY_BR.sub(lambda m: f"${_flatten(m.group(1))}$", text)
    text = _INLINE_PAREN.sub(lambda m: f"${_flatten(m.group(1))}$", text)

    # strip markdown only in the non-math segments, leave $...$ untouched
    out = []
    for part in _INLINE_SPLIT.split(text):
        if part.startswith("$") and part.endswith("$") and len(part) >= 2:
            out.append(part)
        else:
            out.append(_strip_markdown(part))
    text = "".join(out)

    text = text.replace(r"\begin{align}", r"\begin{aligned}")
    text = text.replace(r"\end{align}", r"\end{aligned}")
    text = _MULTINEWLINE.sub("\n\n", text).strip()
    return text


# --------------------------------------------------------------------- yaml writing
class _LiteralStr(str):
    pass


def _literal_representer(dumper, data):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


yaml.add_representer(_LiteralStr, _literal_representer)


def _blockify(obj):
    if isinstance(obj, dict):
        return {k: _blockify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_blockify(v) for v in obj]
    if isinstance(obj, str) and ("\n" in obj or len(obj) > 80):
        return _LiteralStr(obj)
    return obj


# --------------------------------------------------------------------------- adapter
class Adapter(ABC):
    """Base adapter: parse a source into YearFiles, then emit validated YAML."""

    name: str = "adapter"

    @abstractmethod
    def parse(self, source: Path) -> list:
        """Return a list of :class:`YearFile` from the given source path."""

    def emit(self, source: Path, outdir: Path, *, check_katex: bool = True,
             dry_run: bool = False) -> list:
        """Parse + validate + (optionally) write YAML. Returns written/would-write paths."""
        year_files = self.parse(Path(source))
        written = []
        for yf in year_files:
            data = yf.to_dict()

            # 1) must satisfy the importer's own schema
            FileSpec.model_validate(data)

            # 2) math must render (mirrors the importer's gate)
            if check_katex:
                if not katex_available():
                    raise RuntimeError(
                        "KaTeX unavailable; run `npm install` in scripts/ or pass check_katex=False"
                    )
                items = [
                    {"id": str(p["number"]), "text": p["statement"]}
                    for p in data["problems"]
                ]
                bad = run_katex_check(items)
                if bad:
                    raise ValueError(f"{self.name}: KaTeX errors in {yf.competition.get('name')} "
                                     f"{yf.year}: {bad}")

            comp_slug = re.sub(r"[^a-z0-9]+", "_", yf.competition["name"].lower()).strip("_")
            path = outdir / comp_slug / f"{yf.year}.yaml"
            written.append(path)
            if dry_run:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                if yf.header:
                    for line in yf.header.strip().splitlines():
                        f.write(f"# {line}\n")
                    f.write("\n")
                yaml.dump(_blockify(data), f, sort_keys=False, allow_unicode=True,
                          default_flow_style=False, width=100)
        return written
