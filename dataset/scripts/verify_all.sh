#!/usr/bin/env bash
# Release gate. Run from the dataset directory:  bash scripts/verify_all.sh
# Exits non-zero if any check fails. No network, no API key, no server launch.
set -uo pipefail
cd "$(dirname "$0")/.."

fail=0
run() {
    echo
    echo "############################################################################"
    echo "# $1"
    echo "############################################################################"
    shift
    "$@" || { echo "!! FAILED: $*"; fail=1; }
}

skip() {
    echo
    echo "############################################################################"
    echo "# $1"
    echo "############################################################################"
    echo "SKIPPED — needs the raw collection output in ../data/, which is not"
    echo "published: it carries tool descriptions written by server authors, and"
    echo "this dataset redistributes verdicts rather than that prose (see"
    echo "CONSTRAINTS.md, 'Redistribution'). To run these two, re-collect first:"
    echo "    python3 ../src/fetch_registry.py && python3 ../src/collect_stdio.py"
    echo "That is Layer 2 in README.md 'Reproducing' — hours, and it launches"
    echo "servers. Layer 1 (checks 1 and 4) needs none of it and is what a"
    echo "fresh clone runs."
}

# Layer 1 — self-contained: only the published files.
run "1/4  no third-party prose, no credentials, no PII" \
    python3 scripts/verify_no_prose.py

# Layer 2 — needs ../data/ (raw collection, deliberately unpublished).
if [ -d ../data ]; then
    run "2/4  prose removal changed no verdict; dataset is self-contained" \
        python3 scripts/verify_verdicts.py
    run "3/4  rebuild from source and assert every frozen rate" \
        python3 scripts/build_dataset.py
else
    skip "2/4  prose removal changed no verdict; dataset is self-contained"
    skip "3/4  rebuild from source and assert every frozen rate"
fi

run "4/4  regenerate every number quoted in the docs (also writes STATS.txt)" \
    bash -c 'python3 scripts/stats.py | tee STATS.txt'

echo
echo "############################################################################"
if [ "$fail" -eq 0 ]; then
    echo "# ALL CHECKS PASSED"
else
    echo "# SOME CHECKS FAILED"
fi
echo "############################################################################"
exit "$fail"
