#!/usr/bin/env bash
# Everything that has to hold for the checker to be trustworthy.
#   bash checker/tests/run_all.sh
# Exits non-zero if anything fails. No network, no API key, no paid call.
set -uo pipefail
cd "$(dirname "$0")/../.."

fail=0
run() {
    echo
    echo "############################################################################"
    echo "# $1"
    echo "############################################################################"
    shift
    "$@" || { echo "!! FAILED: $*"; fail=1; }
}

run "1/4  one copy of the rules; every consumer imports the same object" \
    python3 checker/tests/test_single_source.py

run "2/4  checker output == dataset/violations.jsonl, server by server" \
    python3 checker/tests/crosscheck_corpus.py

run "3/4  minimal repros of schemas that failed in real GitHub issues" \
    python3 checker/tests/github_issue_repros.py

run "4/4  end-to-end: stdio launch, exit codes, --json, error paths" \
    python3 checker/tests/test_cli.py

echo
echo "############################################################################"
if [ "$fail" -eq 0 ]; then echo "# ALL CHECKER TESTS PASSED"; else echo "# SOME CHECKER TESTS FAILED"; fi
echo "############################################################################"
exit "$fail"
