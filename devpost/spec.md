---
doc: spec
status: approved
---

# Red First — Technical Spec

## How This Works, In Plain Language

Run the suite once with coverage switched on, recording which test executed which line. That gives
a map: for every function, the tests that reach it. Then take one function, rewrite its body to do
nothing, and run only its tests. If they all pass, nothing in the suite was checking that function.
Put the file back and move to the next one.

## The Core Journey Through the System

1. `cli.py` parses arguments and checks the baseline suite is green.
2. `mapping.py` runs the suite under `coverage.py` with dynamic contexts and builds function → tests.
3. `targets.py` walks the AST and lists candidate functions, applying the skip list.
4. `mutate.py` rewrites one function body and restores it afterwards.
5. `run.py` runs the mapped tests and classifies the outcome from pytest's report.
6. `propose.py` asks a model for one assertion and accepts it only if it fails on the mutant and
   passes on the original.
7. `report.py` prints the four groups and returns the exit code.

## Stack

Python 3.11+, `pytest`, `coverage.py`. No web framework, no database. The model step uses one HTTPS
call with a key read from the environment; everything else runs offline.

## Where It Runs and How Someone Tries It

A terminal on the maintainer's machine, and CI. `./run.sh --repo . --tests "pytest -q"`.

## Look and Feel

Monospaced report, four headed groups, evidence indented under each line. An optional
`--html report.html` writes the same content as one static page.

## Components

### mapping.py
Runs coverage with `--context=test` and reads the resulting data to build function → tests. Falls
back to "all tests" when contexts are unavailable, and says so in the report.

### mutate.py
AST rewrite: replace the body with `return None`, preserving the signature, decorators and
docstring. Writes to the file in place, keeps the original bytes in memory, restores in a `finally`.

### run.py
Subprocess pytest with the mapped node ids, `-x -q`, a timeout, and `-p no:cacheprovider`.
Classifies: assertion failure → `guarded`; other exception → `crashed`; all passed → `unguarded`;
timeout → `timeout`.

### propose.py
One model call, strict output shape, and a two-run check. Never writes into the repository.

## Data Model

```
Target(module, qualname, lineno, tests: list[str])
Verdict(target, kind: guarded|crashed|unguarded|unreached|timeout, witness: str|None, seconds: float)
Proposal(target, assertion: str, failed_on_mutant: bool, passed_on_original: bool)
```

## File Structure

```
src/redfirst/{cli,mapping,targets,mutate,run,propose,report}.py
tests/                 synthetic repositories built on the spot
run.sh
.github/workflows/tests.yml
devpost/               scope, prd, spec, checklist
```

## External Services and Dependencies

`pytest`, `coverage`. One optional HTTPS call to an OpenAI-compatible endpoint for the proposal
step, keyed from the environment and never logged.

## Important Failure Modes

- Baseline suite already failing → stop, exit 3. A mutation verdict against a red suite is noise.
- Coverage contexts unsupported by the project's configuration → fall back to the whole suite,
  slower, stated in the report.
- A mutated function that the import system caches → run each mutation in a fresh subprocess.
- A test that fails only under mutation because of ordering → confirm by re-running that one test.
- A repository that writes files during tests → work on a copy, never the original tree.

## What Was Simplified and Why

One operator instead of a matrix; Python only; no cache. Each of those multiplies work without
changing the sentence the maintainer acts on.

## Decisions and Open Issues

The skip list starts small and is widened only when a real repository shows a verdict that is
noise rather than news.
