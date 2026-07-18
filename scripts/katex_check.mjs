// KaTeX validation helper for the import pipeline.
//
// Reads a JSON array of {id, text} on stdin and writes a JSON array of
// {id, ok, errors:[{math, error}]} on stdout. It mirrors exactly how the frontend
// renders (frontend/src/components/ProblemDetail.jsx): the text is split on the
// inline-math regex /(\$.*?\$)/g and each `$...$` segment is rendered with KaTeX
// (throwOnError). Anything outside `$...$` is plain text and is not validated, except
// that stray `$` left in the plain-text parts is flagged (unbalanced or multiline math,
// which the frontend would render as broken).
//
// Usage:  node scripts/katex_check.mjs   (with scripts/node_modules/katex installed)

import katex from "katex";

const MATH_SPLIT = /(\$.*?\$)/g;

function isMath(part) {
  return part.startsWith("$") && part.endsWith("$") && part.length >= 2;
}

function checkText(text) {
  const errors = [];
  const parts = String(text ?? "").split(MATH_SPLIT);
  for (const part of parts) {
    if (!isMath(part)) continue;
    const math = part.slice(1, -1);
    try {
      katex.renderToString(math, { throwOnError: true, displayMode: false });
    } catch (e) {
      errors.push({ math, error: e.message });
    }
  }
  // Any `$` surviving in the non-math parts means an unbalanced or multiline
  // delimiter — the frontend regex won't capture it and the `$` shows literally.
  const nonMath = parts.filter((p) => !isMath(p)).join("");
  const stray = (nonMath.match(/(?<!\\)\$/g) || []).length;
  if (stray > 0) {
    errors.push({ math: null, error: `${stray} unbalanced or multiline '$' delimiter(s)` });
  }
  return errors;
}

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (d) => (input += d));
process.stdin.on("end", () => {
  let items;
  try {
    items = JSON.parse(input);
  } catch (e) {
    process.stderr.write(`katex_check: invalid JSON input: ${e.message}\n`);
    process.exit(2);
  }
  const results = items.map(({ id, text }) => {
    const errors = checkText(text);
    return { id, ok: errors.length === 0, errors };
  });
  process.stdout.write(JSON.stringify(results));
});
