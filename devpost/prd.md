---
doc: prd
status: approved
---

# Red First — Product Requirements

## The Core Journey

A maintainer runs `red-first` in a repository. It runs the suite once under coverage to learn which
tests reach which functions. Then, function by function, it empties a body and re-runs only the
tests that reach it. It prints a report grouped by verdict, ending with the functions nothing
defends, and exits non-zero if any of them were touched by the current change. The maintainer
writes a test, runs it again, and the function moves from `unguarded` to `guarded`.

## Screens and Layout

A terminal report and an optional single HTML page. The terminal is the product; the page exists
so a verdict can be attached to a pull request.

## Look and Feel

Plain, dense, and quotable. One line per function, with the evidence indented underneath. The same
restraint as the two previous projects: no score, no badge, no celebration.

## Features and Behavior

### Mapping

- Run the test command once under coverage with per-test contexts, producing a map from function
  to the tests that execute it.
- A function no test executes is `unreached`. It is reported first, because no mutation is needed
  to know nothing checks it.

### Mutation

- For each candidate function, rewrite its body to `return None` in a copy of the file, leaving
  signature, decorators and docstring intact.
- Run only the mapped tests for that function, stopping at the first failure.
- Restore the file before the next function. One function is mutated at a time, never two.

### Verdicts

- `guarded` — a test failed on an assertion. Name the first such test.
- `crashed` — a test failed on an exception rather than an assertion. Something noticed, but only
  because the missing return value broke something downstream. Reported separately, never counted
  as guarded.
- `unguarded` — every mapped test still passed.
- `unreached` — no test executes the function.

### Proposed assertion

- For an unguarded function, the model is given the function source and one existing test file for
  style, and asked for a single assertion.
- The proposal is run twice: it must fail against the mutant and pass against the original.
- Only a proposal that passes both runs is printed, marked as checked. Everything else is dropped
  silently, with a count of how many were discarded.
- With no API key the tool skips this step and says so.

### Selection and budget

- `--changed-since REF` limits the run to functions in the diff.
- `--max-seconds` bounds the whole run; unfinished functions are reported as `not-yet-checked`,
  never as guarded.
- Skip list for functions whose absence is legitimately unobservable: `__repr__`, `__str__`,
  logging helpers, and anything decorated as a property by configuration.

## States and Boundaries

- No tests at all, or the suite is already red: stop and say so. A mutation result means nothing
  against a failing baseline.
- A test that is flaky under mutation: a function is only called `guarded` when the failure is
  reproducible on a second run of that one test.
- A repository whose test command needs arguments: the command is a flag, not a guess.
- Timeouts are a verdict of their own, never silently folded into `unguarded`.

## Product Decisions

- One operator, not many. The question is "would anything notice", and one brutal operator answers
  it.
- `crashed` is kept separate from `guarded`, even though both are "a test failed". Merging them
  would let a suite look defended when it only has type accidents.
- No mutation score. The unit of action is a function name.
- The model never decides a verdict. It may only propose an assertion that the machine then tries
  to falsify.

## What We're Building

A command-line tool, a small library, its own test suite, and CI that runs Red First against Red
First and fails on an unguarded function in the changed set.

## Deferred From the POC

Caching, parallel workers, other languages, other runners.

## Possible Later Enhancements

A pull-request comment; a second operator for boolean returns; a watch mode.

## Non-Goals

Replacing mutation-testing frameworks. Writing tests into the repository. Rating a codebase.

## Open Questions

How aggressive the default skip list should be — resolved during the build by running against a
real repository and reading what it reports.
