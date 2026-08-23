#!/usr/bin/env python3
"""Assert there is exactly ONE copy of the verdict rules.

The dataset's published rates and the checker's output have to come from the
same engine. If they ever came from two copies, they could disagree inside a
single release and neither would be trustworthy. This test is what stops that
happening quietly.

    python3 checker/tests/test_single_source.py

It checks four things:
  1. Every consumer resolves to the SAME module object (identity, not equality).
  2. The rule function bodies exist in exactly one file on disk.
  3. Every non-ambiguous code in CODES resolves to a source quote AND a fix.
  4. Every code the judges can emit is registered in CODES (no ("?","unknown")).
"""
import importlib
import inspect
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.dirname(HERE)
ROOT = os.path.dirname(CHECKER)
sys.path.insert(0, CHECKER)
sys.path.insert(0, os.path.join(ROOT, "dataset", "scripts"))
sys.path.insert(0, os.path.join(ROOT, "src"))

fails = []


def check(label, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    if detail:
        print(f"        {detail}")
    if not ok:
        fails.append(label)


# --------------------------------------------------- 1. same module object
import mcp_schema_check                       # noqa: E402  the checker
import judge_anthropic, judge_mcp_and_openai  # noqa: E402  dataset build CLIs
import lint_anthropic, lint                   # noqa: E402  collection CLIs
import explain                                # noqa: E402  per-verdict re-derivation
import rules                                  # noqa: E402  the engine itself
import codes                                  # noqa: E402  compat shim

consumers = {
    "checker/mcp_schema_check.py":            mcp_schema_check,
    "dataset/scripts/judge_anthropic.py":     judge_anthropic,
    "dataset/scripts/judge_mcp_and_openai.py": judge_mcp_and_openai,
    "src/lint_anthropic.py":                  lint_anthropic,
    "src/lint.py":                            lint,
}

canonical_C = rules.anthropic.check_C
canonical_A = rules.mcp_openai.check_A
canonical_B = rules.mcp_openai.check_B
canonical_meta = rules.codes.meta_for

bound = {
    "checker/mcp_schema_check.py -> judge_server_anthropic":
        mcp_schema_check.judge_server_anthropic is rules.anthropic.judge_server,
    "checker/mcp_schema_check.py -> judge_server_mcp_openai":
        mcp_schema_check.judge_server_mcp_openai is rules.mcp_openai.judge_server,
    "checker/mcp_schema_check.py -> meta_for":
        mcp_schema_check.meta_for is canonical_meta,
    "dataset/scripts/judge_anthropic.py -> check_C":
        judge_anthropic.check_C is canonical_C,
    "dataset/scripts/judge_mcp_and_openai.py -> check_A":
        judge_mcp_and_openai.check_A is canonical_A,
    "dataset/scripts/judge_mcp_and_openai.py -> check_B":
        judge_mcp_and_openai.check_B is canonical_B,
    "src/lint_anthropic.py -> check_C":
        lint_anthropic.check_C is canonical_C,
    "src/lint.py -> check_A":
        lint.check_A is canonical_A,
    "dataset/scripts/explain.py -> judge_server":
        explain.judge_anthropic.judge_server is rules.anthropic.judge_server,
    "dataset/scripts/codes.py -> meta_for":
        codes.meta_for is canonical_meta,
}
for label, ok in bound.items():
    check(f"same object: {label}", ok)

print()
print(f"  check_C   defined once at {inspect.getsourcefile(canonical_C)}")
print(f"  check_A/B defined once at {inspect.getsourcefile(canonical_A)}")
print(f"  meta_for  defined once at {inspect.getsourcefile(canonical_meta)}")
print()

# ------------------------------------------- 2. one copy of the bodies on disk
def bodies_on_disk(needle):
    hits = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs
                   if d not in {".git", ".venv-anth", "node_modules", "__pycache__",
                                "out", "data", "oracle_ts", "sdk-bug"}]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(base, fn)
            if os.path.abspath(p) == os.path.abspath(__file__):
                continue  # this file quotes the needles; it is not a rule copy
            with open(p, errors="replace") as f:
                if needle in f.read():
                    hits.append(os.path.relpath(p, ROOT))
    return sorted(hits)


for needle, what in [
    ("def check_C(tool):", "the axis-C rule body"),
    ("def check_A(tool):", "the axis-A rule body"),
    ("def check_B(tool):", "the axis-B rule body"),
    ("CODES = {", "the code -> doc-quote table"),
    ("def meta_for(code):", "the code -> metadata resolver"),
    ("FIXES = {", "the code -> one-line-fix table"),
    ("UNSUPPORTED_KEYWORDS = {", "the OpenAI unsupported-keyword table"),
    ("SUPPORTED_FORMATS = {", "the Anthropic supported-format table"),
]:
    hits = bodies_on_disk(needle)
    check(f"exactly one copy of {what}", len(hits) == 1, f"found in: {hits}")

print()

# ------------------------------- 3. every code has a quote and a fix
missing_quote, missing_fix = [], []
for code, (axis, sev, src, quote) in rules.CODES.items():
    if not quote:
        missing_quote.append(code)
    if not rules.fix_for(code):
        missing_fix.append(code)
check("every registered code carries a verbatim source quote",
      not missing_quote, f"missing: {missing_quote}")
check("every registered code carries a one-line fix",
      not missing_fix, f"missing: {missing_fix}")

# ------------------------------- 4. no emitted code falls through lookup()
EMITTED = set()
for mod in (rules.anthropic, rules.mcp_openai):
    src = inspect.getsource(mod)
    import re
    for m in re.finditer(r'"((?:A|B|C|CL|AMB)[0-9A-Za-z_-]*-[A-Za-z0-9$_-]+)"', src):
        EMITTED.add(m.group(1))
unresolved = sorted(c for c in EMITTED if rules.lookup(c)[0] == "?")
check("no code the judges emit falls through lookup() to ('?','unknown')",
      not unresolved, f"unresolved: {unresolved}")
print(f"        codes seen in the rule sources: {len(EMITTED)}")

print()
if fails:
    print(f"{len(fails)} FAILED: {fails}")
    raise SystemExit(1)
print("single source of truth: confirmed")
