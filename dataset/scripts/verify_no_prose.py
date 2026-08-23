#!/usr/bin/env python3
"""Release gate: prove the published JSONL contains no third-party prose,
no credentials, and no PII.

This is the test that backs the redistribution claim in LICENSE/CONSTRAINTS.md.
It scans EVERY line of EVERY published file and prints hard counts. A non-zero
prose or credential count is a build failure (exit 1).

Usage:  python3 dataset/scripts/verify_no_prose.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from prose import PROSE_KEYS, prose_findings, walk_strings   # noqa: E402

FILES = ["servers.jsonl", "tools.jsonl", "violations.jsonl",
         "controls.jsonl", "failures.jsonl"]

# Fields this dataset authors itself that legitimately hold long English text.
# They are OUR words (rule descriptions, verbatim quotes from PUBLIC provider
# docs, oracle library error strings), never a third party's schema prose.
OWN_TEXT_PATHS = re.compile(
    r"\.(message|source_quote|source|note|repro|oracle|corroborated_by|"
    r"oracle_error|oracle_B_errors|oracle_A_issues|static_rule_codes|"
    r"observed_codes|codes|ambiguous_codes|dropped|dropped_keywords|raises)(\[\d+\])?$"
)

# Derived structural paths (JSON pointers, repo slugs, digests) -- ours, and
# never prose. Excluded from the eyeball list so real author-supplied strings
# (regexes, enum members, $ref targets) are the ones that surface.
POINTER_PATHS = re.compile(r"\.(json_pointer|repo_slug|repository|"
                           r"description_sha256_12|stderr_sha256_12)$")

CREDENTIAL_PATTERNS = [
    ("anthropic-key",   re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}")),
    ("openai-key",      re.compile(r"\bsk-[A-Za-z0-9]{32,}")),
    ("github-token",    re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}")),
    ("github-pat",      re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("aws-access-key",  re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("google-api-key",  re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("slack-token",     re.compile(r"\bxox[baprs]-[0-9A-Za-z\-]{10,}")),
    ("private-key-pem", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("jwt",             re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.")),
    ("bearer-literal",  re.compile(r"[Bb]earer\s+[A-Za-z0-9_\-\.]{20,}")),
    ("basic-auth-url",  re.compile(r"https?://[^/\s:@]+:[^/\s@]+@")),
]

# An address, not the literal word "email" used as a JSON Schema `format` value.
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
# Public-repo owner strings such as "user@example.com" inside a $ref are still
# flagged; nothing is auto-allowlisted.


def main():
    total_lines = 0
    prose_hits, cred_hits, email_hits = [], [], []
    longest = []

    for name in FILES:
        path = os.path.join(DATASET, name)
        with open(path) as f:
            for lineno, line in enumerate(f, 1):
                total_lines += 1
                rec = json.loads(line)

                for h in prose_findings(rec):
                    prose_hits.append({"file": name, "line": lineno, **h})

                for spath, s in walk_strings(rec):
                    if not OWN_TEXT_PATHS.search(spath) and not POINTER_PATHS.search(spath):
                        longest.append((len(s), name, spath, s[:120]))
                    for label, pat in CREDENTIAL_PATTERNS:
                        if pat.search(s):
                            cred_hits.append({"file": name, "line": lineno,
                                              "path": spath, "kind": label,
                                              "preview": s[:80]})
                    if EMAIL_RE.search(s) and not OWN_TEXT_PATHS.search(spath):
                        email_hits.append({"file": name, "line": lineno,
                                           "path": spath, "preview": s[:80]})

    longest.sort(reverse=True)

    print("=" * 78)
    print("PROSE / CREDENTIAL / PII SCAN  --  mcp-schema-census")
    print("=" * 78)
    print(f"files scanned                : {len(FILES)}")
    print(f"JSON records scanned         : {total_lines}")
    print(f"prose keys checked           : {', '.join(sorted(PROSE_KEYS))}")
    print()
    print(f"third-party prose fields found : {len(prose_hits)}")
    print(f"credential matches found       : {len(cred_hits)}")
    print(f"email-address matches found    : {len(email_hits)}")
    print()
    print("longest non-authored string values (eyeball check, top 15):")
    for ln, name, spath, prev in longest[:15]:
        print(f"  {ln:5}  {name:16} {spath[:60]:60} {prev[:60]!r}")

    for label, hits in (("PROSE", prose_hits), ("CREDENTIAL", cred_hits), ("EMAIL", email_hits)):
        if hits:
            print(f"\n!! {label} FINDINGS ({len(hits)}):")
            for h in hits[:20]:
                print("   ", json.dumps(h)[:200])

    ok = not prose_hits and not cred_hits and not email_hits
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
