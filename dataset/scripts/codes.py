#!/usr/bin/env python3
"""Compatibility shim. The code table lives in `rules/codes.py`.

Kept so `from codes import meta_for` keeps working in build_dataset.py and
explain.py without those files caring where the table moved to.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rules.codes import CODES, SRC, lookup, meta_for   # noqa: E402,F401

__all__ = ["CODES", "SRC", "lookup", "meta_for"]
