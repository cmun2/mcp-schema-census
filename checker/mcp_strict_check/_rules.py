"""Find the ONE copy of the verdict rules, whichever way this code was started.

There is exactly one physical copy of the rule engine in this repository:
`dataset/scripts/rules/`. The dataset build, the collection scripts and this
checker all import that same directory, so a published rate and a checker
finding can never come from two diverging tables. `checker/tests/
test_single_source.py` is the test that keeps it that way.

Two entry paths have to reach it:

  installed wheel   the build maps dataset/scripts/rules into the package as
                    `mcp_strict_check.rules` (pyproject, force-include). Still
                    one copy in the repo; one copy in the wheel. No sys.path
                    manipulation at runtime.

  repo checkout     nothing is installed, so the package has no `rules`
                    subdirectory. Fall back to the on-disk location, which is
                    where `dataset/scripts/*.py` and `src/lint*.py` import it
                    from as a top-level `rules` package. Loading it under that
                    same top-level name is deliberate: it makes the checker and
                    the dataset build share one module OBJECT, not merely one
                    file.
"""
import importlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
# checker/mcp_strict_check -> checker -> repository root
ROOT = os.path.dirname(os.path.dirname(_HERE))
#: The directory that had to go on sys.path for `import rules` to work from a
#: checkout, or None when the package carried its own copy (installed wheel).
#: This is what tells the two cases apart -- not a path prefix test, which
#: cannot distinguish a repository from a site-packages tree.
RULES_PARENT = None


def _load():
    global RULES_PARENT
    try:
        return importlib.import_module(__name__.rsplit(".", 1)[0] + ".rules")
    except ImportError:
        pass
    parent = os.path.join(ROOT, "dataset", "scripts")
    if os.path.isdir(os.path.join(parent, "rules")):
        if parent not in sys.path:
            sys.path.insert(0, parent)
        RULES_PARENT = parent
        return importlib.import_module("rules")
    raise ImportError(
        "cannot locate the rule engine.\n"
        "Installed from PyPI it ships as mcp_strict_check.rules; from a\n"
        f"checkout it is read from {parent}. Neither was importable, which\n"
        "means this is a broken install rather than a missing option.")


rules = _load()


def engine_label():
    """Where the rules were read from, for the header line and --json
    `rules_engine`.

    A checkout names the repository-relative directory, so the output points
    at the tree the published corpus was built from. An installed copy names
    the module, because there is no repository for a path to be relative to
    and printing an absolute site-packages path would say nothing useful."""
    if RULES_PARENT is None:
        return "mcp_strict_check.rules"
    return os.path.relpath(RULES_PARENT, ROOT)
