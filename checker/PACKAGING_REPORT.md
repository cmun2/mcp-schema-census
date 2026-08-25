# `mcp-strict-check` packaging — what was done, and the actual output

Commit `dd1eb12`. **Nothing was uploaded.** No PyPI account, no API token, no
`twine`, no `git push`. The work stops at `dist/`.

---

## 1. The constraint that shaped the design

The repository holds **one** copy of the verdict rules, at
`dataset/scripts/rules/`. The dataset build, `src/lint*.py` and the checker
all import it, and `checker/tests/test_single_source.py` asserts both object
identity and a copy-count of 1.

A wheel that carried its own transcription would break that: the published
rates and the tool's output could disagree inside a single release, with no
way to tell which was wrong. So the build **maps** the one directory in
instead of duplicating it — `pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel]
packages = ["checker/mcp_strict_check"]

[tool.hatch.build.targets.wheel.force-include]
"dataset/scripts/rules" = "mcp_strict_check/rules"
```

`hatchling` was chosen over `setuptools` for one concrete reason: setuptools
leaves a `build/lib/...` tree in the working directory, which *is* a second
copy of the rule files on disk and would make `test_single_source.py` fail
every time someone ran `python -m build`. hatchling builds through temp dirs
and leaves only `dist/`.

### How many copies exist on disk

```console
$ grep -rl 'def check_C(tool):' . | grep -v '\.venv\|__pycache__\|\.git/'
checker/tests/test_single_source.py     # quotes the needle; not a rule copy
dataset/scripts/rules/anthropic.py      # <- the one copy

$ git ls-files | grep -E 'rules/.*\.py$'
dataset/scripts/rules/__init__.py
dataset/scripts/rules/anthropic.py
dataset/scripts/rules/codes.py
dataset/scripts/rules/fixes.py
dataset/scripts/rules/mcp_openai.py
dataset/scripts/rules/sdk_oracle.py
```

`dist/` is gitignored, so a build cannot turn into a tracked second copy.

---

## 2. Layout change

`checker/mcp_strict_check.py` (flat module) became a package, because a flat
module cannot carry a `rules` subpackage:

```
checker/mcp_strict_check/
  __init__.py     re-exports, so `import mcp_strict_check` is unchanged
  __main__.py     `python -m mcp_strict_check`
  cli.py          the former checker/mcp_strict_check.py, moved with git mv
  _rules.py       NEW — resolves the engine for both entry paths
```

`_rules.py` is the whole trick:

- **installed** — `import mcp_strict_check.rules` succeeds; no `sys.path`
  manipulation at all.
- **checkout** — that import fails (the package directory has no `rules/`), so
  it falls back to `dataset/scripts` and loads the **same top-level `rules`
  module object** the dataset build uses. Object identity, not just file
  identity, which is what `test_single_source.py` checks.

`./checker/mcp-strict-check` still runs with nothing installed; it now sets
`PYTHONPATH` and calls `python3 -m mcp_strict_check`.

---

## 3. Verification — actual output

### 3.1 `python -m build`, and `rules/*.py` inside the wheel

```
$ unzip -l dist/mcp_strict_check-0.1.0-py3-none-any.whl
      733  mcp_strict_check/__init__.py
      293  mcp_strict_check/__main__.py
     3015  mcp_strict_check/_rules.py
    25957  mcp_strict_check/cli.py
     2819  mcp_strict_check/rules/__init__.py      <-- the rule engine
    14844  mcp_strict_check/rules/anthropic.py     <--
     9552  mcp_strict_check/rules/codes.py         <--
     6943  mcp_strict_check/rules/fixes.py         <--
     9473  mcp_strict_check/rules/mcp_openai.py    <--
     3627  mcp_strict_check/rules/sdk_oracle.py    <--
    17591  mcp_strict_check-0.1.0.dist-info/METADATA
       87  mcp_strict_check-0.1.0.dist-info/WHEEL
       63  mcp_strict_check-0.1.0.dist-info/entry_points.txt
     1728  mcp_strict_check-0.1.0.dist-info/licenses/LICENSE
     1322  mcp_strict_check-0.1.0.dist-info/RECORD
```

All six rule files are present. The sdist keeps the repository layout so that
building a wheel *from the sdist* (which is what `python -m build` does) hits
the same paths — verified, and an sdist install also carries the rules.

### 3.2 Clean venv, run from **outside** the repository

Installed into a fresh Python **3.8.20** venv, run from a scratch directory
where `git rev-parse` reports "not a git repository":

```
$ pip list --format=freeze
mcp-strict-check==0.1.0
pip==23.0.1
setuptools==56.0.0          # zero third-party dependencies
```

`mcp-strict-check --help` → exit **0**.

Violating schema (`additionalProperties: true`, `minLength`, `maxLength`,
`minimum`):

```
mcp-strict-check 0.1.0  ·  dirty.json
rules: mcp_strict_check.rules  (the engine that produced the 617-server corpus)

1 tool(s) checked

  axis                                          scope  verdict  tools   corpus
  --------------------------------------------------------------------------
  MCP specification conformance                always  PASS        0     0.0%
  OpenAI strict mode (hard reject)             opt-in  FAIL        1    27.6%
  OpenAI strict mode (silent constraint loss)  opt-in  WARN        1    56.9%
  Anthropic Messages API baseline              always  PASS        0     0.0%
  Anthropic strict:true subset                 opt-in  FAIL        1    63.0%
  Anthropic request complexity limits          opt-in  PASS        0    37.3%
  --------------------------------------------------------------------------
  ...
  5 hard reject(s) — these axes would refuse your schema.
  3 silently-dropped constraint(s) — accepted, then not enforced.
```
→ exit **1**

Clean schema (`additionalProperties: false`, no constraints):

```
  0 hard rejects on the selected axes.
```
→ exit **0**

`--cmd` (stdio child-process launch) against `demo_server.py` copied outside
the repo: 4 tools, `server: demo-flawed-server 0.1.0`, exit **1**.

### 3.3 `uvx --from ./dist/<wheel>`

```
$ uvx --from .../dist/mcp_strict_check-0.1.0-py3-none-any.whl mcp-strict-check --help
Installed 1 package in 5ms
usage: mcp-strict-check [-h] (--cmd CMDLINE | --tools FILE | --schema FILE) ...
```
and a real run: `rules_engine = mcp_strict_check.rules`, `n_hard_rejects = 5`,
`exit_code = 1`.

### 3.4 The `sdk-oracle` extra

`pip install "<wheel>[sdk-oracle]"` resolves `anthropic==1.0.0`, and
`--sdk-oracle` then runs the vendor transform locally:

```
  anthropic==1.0.0  (the corpus was measured against 1.0.0)
  the SDK silently dropped constraints on 1 tool(s)
      dirty  maxLength, minLength, minimum
```

Without the extra it degrades with one explanatory line and does not crash.

### 3.5 Exit codes for the required gates

| check | exit code |
|---|---:|
| 4. `bash checker/tests/run_all.sh` | **0** — 61 `[PASS]`, 0 `[FAIL]` |
| 5. `cd dataset && bash scripts/verify_all.sh` | **0** — ALL CHECKS PASSED |
| 6. `./checker/mcp-strict-check --help` (repo root) | **0** |

The single-source assertions inside (4), unchanged in meaning and now doubled:

```
[PASS] exactly one copy of the axis-C rule body
        found in: ['dataset/scripts/rules/anthropic.py']
[PASS] exactly one git-tracked copy of the axis-C rule body
        tracked: ['dataset/scripts/rules/anthropic.py']
...  (same for axis-A, axis-B, CODES, meta_for, FIXES,
      UNSUPPORTED_KEYWORDS, SUPPORTED_FORMATS)
```

---

## 4. A pre-existing failure this had to fix

`run_all.sh` was **already failing before any of this work** — baseline on
`590c573`:

```
[FAIL] exactly one copy of the code -> doc-quote table
        found in: ['.venv-oai/lib/python3.12/site-packages/httpcore2/_async/socks_proxy.py',
                   '.venv-oai/lib/python3.12/site-packages/httpx2/_status_codes.py',
                   '.venv-oai/lib/python3.12/site-packages/websockets/frames.py',
                   'dataset/scripts/rules/codes.py']
```

An untracked virtualenv in the tree contains third-party files that happen to
hold the string `CODES = {`. The scan now skips virtualenvs by **`pyvenv.cfg`,
not by name**, skips `build`/`dist` (copies by construction, and gitignored),
and then repeats every count over `git ls-files` — so the answer no longer
depends on the exclusion list being complete.

---

## 5. `requires-python = ">=3.8"` — actually tested, not asserted

CPython 3.8.20 was installed locally and used for the whole verification: all
shipped sources byte-compile under it, and the CLI runs end to end under it
(`--version`, `--cmd` stdio launch, `--json`, `--schema`). The README's
3.8+ claim stands as written; it did not have to be raised.

---

## 6. Not done / not certain

- **Nothing published.** `dist/` only. `uvx mcp-strict-check` (the bare name)
  does **not** work yet — it needs the upload. `checker/README.md` carries a
  blockquote saying so, marked for deletion in the publishing commit.
- **Project URLs are inferred, not confirmed.** This worktree has no git
  remote. `https://github.com/cmun2/mcp-schema-census` was taken from the
  `git clone` line already in `checker/README.md`. If the repository lands
  anywhere else, `pyproject.toml [project.urls]` and that clone line must move
  together. A question was sent to the coordinator and had not been answered
  when this was written.
- **Author is `cmun2`, with no email.** PyPI metadata is public, so the
  git-configured address was deliberately left out rather than published on a
  guess. Add `email = "..."` under `[[project.authors]]` if that is wanted.
- **Only tested on macOS/arm64**, Python 3.8 and 3.12. The package is pure
  Python with no dependencies, so other platforms should be fine, but that is
  reasoning, not a measurement.
- **`Development Status :: 3 - Alpha`** was chosen for a 0.1.0. Bump to
  `4 - Beta` if that undersells it.
- **The name `mcp-strict-check` is not reserved on PyPI.** It was not checked
  for availability, because doing so is a step toward publishing.
