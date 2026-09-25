# Red First

A passing test suite is a claim. Red First breaks each function on purpose and reports which ones
no test would notice were broken.

```bash
./run.sh --repo . --source src/redfirst --tests "pytest -q"
```

It runs the suite once under coverage to learn which tests reach which function, then empties one
function at a time and re-runs only those tests. Four answers, printed every time:

- **unguarded** — every test that reaches it still passed. It looks tested, it counts as covered,
  and nothing in the suite would notice if it stopped working.
- **unreached** — no test executes it at all.
- **crashed** — a test failed, but on an exception rather than an assertion. The suite noticed by
  accident; nothing in it says what this function should do.
- **guarded** — a test asserted something that stopped holding, and it is named.

The command exits non-zero on **unguarded**, so it can sit in CI as one line.

Coverage tells you a line *ran*. It cannot tell you anything *checked* it.

## On real repositories

| Repository | Functions | guarded | crashed | unreached | unguarded | Time |
|---|---:|---:|---:|---:|---:|---:|
| [tinydb](https://github.com/msiemens/tinydb) | 101 | 39 | 56 | 6 | 0 | 19 s |
| [python-tabulate](https://github.com/astanin/python-tabulate) | 73 | 29 | 43 | 0 | 0 | 111 s |
| Red First itself | 36 | 10 | 26 | 0 | 0 | 35 s |

Neither library has an unguarded function, and the report says so plainly — a tool that always
finds something is not measuring anything. The finding in these runs is the other column: in
tinydb, 39 functions are held by an assertion and 56 are noticed only because `None` broke
something downstream. That is not a bug list. It is a map of where the suite states an intention
and where it merely passes through.

## It found something in its own tests

The first self-run reported `isolated_plugin` as unguarded. Checking the claim by hand showed the
tests *did* fail on that mutation — so the verdict was wrong, and the reason was a real defect:
the runner put its plugin directory on `PYTHONPATH`, that variable leaked into the subprocesses
the tests themselves start, and it repaired the mutant. The plugin now lives inside the copy being
examined and `PYTHONPATH` is left alone. There is a test for that, because the failure was
invisible from the outside.

The same run named nine functions no test executed. They have tests now. The tool's own report is
in CI, and the build fails on an unguarded function.

## Prior art

Mutation testing is not a new idea, and Python has had tools for it for years:
[mutmut](https://github.com/boxed/mutmut), [cosmic-ray](https://github.com/sixty-north/cosmic-ray)
and [mutpy](https://github.com/mutpy/mutpy). They mutate far more aggressively than this does —
operators, constants, boundaries, branch conditions — and if you want a mutation score, use one of
them.

Red First makes one mutation, not many: it empties a function's body entirely. That is a
deliberately blunt instrument, and it buys three things.

- **A question a reader can answer.** "Would any test notice if this function did nothing at all?"
  has an obvious right answer for every function in a codebase; a mutation score does not.
- **A cost that fits a pull request.** Only the tests that actually cover the mutated line are
  re-run, taken from coverage.py's per-test contexts, so the run is proportional to the functions
  you touched rather than to the suite.
- **Four verdicts instead of a percentage.** `guarded`, `crashed`, `unguarded`, `unreached` — and
  the ones that matter, the unguarded, are named with their file and line and make the command exit
  non-zero. `crashed` is kept separate on purpose: a test that fails because the function returned
  `None` and something downstream blew up is not the same as a test that checked the result.

Use mutmut to grade a suite. Use this to find the functions nothing defends before you ship them.

## Where the model is, and is not

Behind `--explain`, a model is asked for one test for a function nothing defends. The suggestion
is then run twice: it must **pass** against the real function and **fail** against the emptied
one. Only then is it printed. Anything else is dropped, and the report says how many were dropped.

```
UNGUARDED  nothing in the suite would notice this function doing nothing  (1)
  shout
      pkg/calc.py:4
      1 test(s) still passed
      proposed assertion, checked against both versions:
        def test_shout():
            from pkg.calc import shout
            assert shout("hello") == "HELLO!"
```

The model never decides a verdict. It proposes; the mutant decides. With no key the tool skips the
step and says so.

## Usage

```bash
./run.sh --repo . --source src/redfirst                      # pytest -q by default
./run.sh --repo ../tinydb --source tinydb --tests "pytest -q -o addopts="
./run.sh --repo . --source src/redfirst --only mutate        # one function or one prefix
./run.sh --repo . --source src/redfirst --max-seconds 120    # unfinished work is reported, not guessed
./run.sh --repo . --source src/redfirst --html report.html
```

| Exit code | Meaning |
|---|---|
| 0 | nothing unguarded |
| 1 | a function no test would notice breaking |
| 3 | the suite was already failing, so no verdict was possible |

It works on a copy of the repository. Your files are never mutated.

## Tests

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests -q     # 32 tests, no network
```

They build small repositories on the spot — a function with an assertion behind it, one that is
called and never checked, one nobody calls — and assert the verdict the tool should reach.

## What went wrong while building this

Three of the bugs were invisible from the outside, and each is now a test:

- **The bytecode cache.** CPython validates a `.pyc` against the source's `(mtime, size)`, both at
  one-second resolution. Two mutants of similarly shaped functions collided on both, the tests
  imported the previous mutant, and verdicts changed depending on what ran before them. Bytecode
  writing is now off for every run.
- **Plugin shadowing.** The reporting plugin was imported from this package, so a project with a
  package of the same name — this one, for instance — shadowed the mutated module.
- **Parsing pytest's output.** Node ids were read off `--collect-only`; a project that sets `-v`
  prints a tree with no node ids in it, and every function came back unmatched. The plugin reports
  them directly now.

## When coverage contexts are unavailable

If `coverage` cannot produce per-test contexts — it is missing, or the suite runs in a way that
defeats them — the tool does not stop. It runs the whole suite for every function instead, and
says so in the first line of the report, because one verdict changes meaning: a function no test
calls at all cannot be told apart from one the tests call and ignore, so it lands under
`unguarded` rather than `unreached`.

That line used to read "slower, same verdicts". It was wrong, and it was found the way these
things are found — by running the tool in an environment without `coverage` and reading a verdict
that did not match the fixture.

## Honest limits

- One mutation operator, deliberately. Emptying a function is brutal, and on real code it usually
  produces `crashed` rather than `unguarded`. A subtler operator would find more, and take longer
  than anyone waits.
- A surviving mutant is not always a defect. Some functions are legitimately unobservable, and the
  report is a list to read, not a list to fix.
- Verdicts depend on the coverage map. When per-test contexts are unavailable the tool falls back
  to the whole suite and says so; when a context cannot be matched to a node id, it reports
  `not checked` rather than calling the function clean.
- Python and pytest only.

MIT licensed. Planned with the Devpost Learn skill pack; `devpost/` holds the scope, PRD and spec
written before the code.
