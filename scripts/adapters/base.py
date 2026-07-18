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


_COMMENT = re.compile(r"(?<!\\)%[^\n]*")
_NOTE = re.compile(r"\\(?:textit|emph|textbf)\{\s*Note[.:][^{}]*\}", re.IGNORECASE | re.DOTALL)
_ENUMERATE = re.compile(
    r"\\begin\{enumerate\}(?:\[[^\]]*?label\s*=\s*(?P<fmt>[^\],]*)[^\]]*\])?"
    r"(?P<body>.*?)\\end\{enumerate\}",
    re.DOTALL,
)
_ITEMIZE = re.compile(r"\\begin\{itemize\}(?P<body>.*?)\\end\{itemize\}", re.DOTALL)
_RESIDUAL = re.compile(r"\\[A-Za-z]+|\\\[|\\\]|\\begin|\\end|\\item")
_ROMAN = ["", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
          "xi", "xii", "xiii", "xiv", "xv"]


def _flatten(inner: str) -> str:
    return re.sub(r"\s*\n\s*", " ", inner.strip())


def _flatten_math(text: str) -> str:
    """Collapse newlines inside every ``$...$`` span (the frontend regex is single-line)."""
    return re.sub(
        r"\$[^$]*\$",
        lambda m: "$" + re.sub(r"\s*\n\s*", " ", m.group(0)[1:-1]).strip() + "$",
        text,
    )


def _cleanup(text: str) -> str:
    text = text.replace("\xa0", " ")         # non-breaking spaces from source -> plain space
    text = _flatten_math(text)
    text = re.sub(r"[ \t]+\n", "\n", text)   # trailing spaces/tabs (incl. whitespace-only lines)
    return _MULTINEWLINE.sub("\n\n", text).strip()


def _is_math(part: str) -> bool:
    return part.startswith("$") and part.endswith("$") and len(part) >= 2


def _display_to_inline(text: str) -> str:
    """`$$...$$`, `\\[...\\]`, `\\(...\\)` -> inline `$...$` (newlines flattened)."""
    text = _DISPLAY_DD.sub(lambda m: f"${_flatten(m.group(1))}$", text)
    text = _DISPLAY_BR.sub(lambda m: f"${_flatten(m.group(1))}$", text)
    text = _INLINE_PAREN.sub(lambda m: f"${_flatten(m.group(1))}$", text)
    return text


def _make_label(fmt: str, i: int) -> str:
    fmt = (fmt or "").strip()
    for token, value in (
        (r"\alph*", chr(96 + i)),
        (r"\Alph*", chr(64 + i)),
        (r"\roman*", _ROMAN[i] if i < len(_ROMAN) else str(i)),
        (r"\Roman*", (_ROMAN[i] if i < len(_ROMAN) else str(i)).upper()),
        (r"\arabic*", str(i)),
    ):
        if token in fmt:
            return fmt.replace(token, value)
    return f"{i}."


def _render_items(body: str, fmt, ordered: bool) -> str:
    items = [s.strip() for s in re.split(r"\\item\b", body) if s.strip()]
    lines = []
    for i, item in enumerate(items, 1):
        label = _make_label(fmt, i) if ordered else "-"
        lines.append(f"{label} {_flatten(item)}")
    return "\n\n" + "\n".join(lines) + "\n\n"


def _convert_lists(text: str) -> str:
    text = _ENUMERATE.sub(lambda m: _render_items(m.group("body"), m.group("fmt"), True), text)
    text = _ITEMIZE.sub(lambda m: _render_items(m.group("body"), None, False), text)
    return text


def _strip_markdown(text: str) -> str:
    """Remove markdown emphasis / normalize bullets in non-math text."""
    text = _BOLD.sub(r"\1", text)
    text = _ITALIC.sub(r"\1", text)
    text = _BULLET.sub(r"\1- ", text)  # "* item" -> "- item"
    return text


_TEXT_MACROS = ("textbf", "textit", "textrm", "textsf", "emph", "rem")


def _unwrap_macros(text: str, names=_TEXT_MACROS) -> str:
    """Remove ``\\name{...}`` wrappers, keeping the inner content.

    Brace-balanced so it works even when the argument spans ``$...$`` math or nested
    braces (e.g. ``\\rem{... $1 \\le i,j \\le n$ ...}``), which a plain regex can't.
    """
    pattern = re.compile(r"\\(?:" + "|".join(names) + r")\{")
    while True:
        m = pattern.search(text)
        if not m:
            return text
        depth, i = 0, m.end() - 1
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if i >= len(text):
            return text  # unbalanced; leave as-is (residual check will flag)
        text = text[: m.start()] + text[m.end() : i] + text[i + 1 :]


def _strip_text_mode(text: str) -> str:
    """Resolve markdown emphasis + LaTeX escapes in non-math text."""
    text = _strip_markdown(text)
    # bare ellipsis macros in prose (e.g. "$x_1$, \dots, $x_n$") -> wrapped math so
    # they render instead of showing literally.
    text = re.sub(r"\\(?:dots|ldots|cdots)(?![A-Za-z])", r"$\\ldots$", text)
    text = re.sub(r"\\ ", " ", text)  # control space
    for esc, ch in ((r"\%", "%"), (r"\&", "&"), (r"\#", "#"), (r"\_", "_")):
        text = text.replace(esc, ch)
    return text


def _apply_outside_math(text: str, fn) -> str:
    return "".join(p if _is_math(p) else fn(p) for p in _INLINE_SPLIT.split(text))


def normalize_statement(text: str) -> str:
    """Convert dataset markdown+LaTeX to the KaTeX-safe, inline-``$...$`` form.

    - ``$$...$$`` / ``\\[...\\]`` / ``\\(...\\)`` -> inline ``$...$`` (newlines flattened),
    - markdown ``**bold**`` / ``*italic*`` stripped, ``* bullets`` -> ``- bullets``,
      only outside math spans,
    - ``align`` -> ``aligned`` (KaTeX rejects bare ``align``).
    """
    text = _display_to_inline(text)
    text = _apply_outside_math(text, _strip_markdown)
    text = text.replace(r"\begin{align}", r"\begin{aligned}")
    text = text.replace(r"\end{align}", r"\end{aligned}")
    return _cleanup(text)


def normalize_latex(text: str) -> str:
    """Convert plain-LaTeX (e.g. per-problem .tex) to the KaTeX-safe inline form.

    Handles what ``normalize_statement`` does, plus text-mode LaTeX the frontend can't
    render: strips ``%`` comments, drops ``\\textit{Note...}`` grader notes, turns
    ``enumerate``/``itemize`` into text lists (``(a)``/``(i)``/``-`` labels), and unwraps
    ``\\emph``/``\\textbf`` outside math.
    """
    text = _COMMENT.sub("", text)
    text = _NOTE.sub("", text)          # drop grader notes before unwrapping emphasis
    text = _unwrap_macros(text)         # \emph{x}/\rem{x} -> x (brace-balanced, spans math)
    text = _display_to_inline(text)
    text = _convert_lists(text)
    text = _apply_outside_math(text, _strip_text_mode)
    text = text.replace(r"\begin{align}", r"\begin{aligned}")
    text = text.replace(r"\end{align}", r"\end{aligned}")
    return _cleanup(text)


def find_residual_latex(text: str) -> list:
    """Return LaTeX commands left in non-math text (would render literally / broken)."""
    found = []
    for part in _INLINE_SPLIT.split(text):
        if not _is_math(part):
            found.extend(_RESIDUAL.findall(part))
    return sorted(set(found))


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

            # 2) no un-normalized text-mode LaTeX (KaTeX only checks $...$ spans, so a
            #    stray \item / \begin{...} outside math would render literally)
            for p in data["problems"]:
                residual = find_residual_latex(p["statement"])
                if residual:
                    raise ValueError(
                        f"{self.name}: residual LaTeX outside math in "
                        f"{yf.competition.get('name')} {yf.year} P{p['number']}: {residual}"
                    )

            # 3) math must render (mirrors the importer's gate)
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
