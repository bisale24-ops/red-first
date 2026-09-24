---
doc: scope
status: approved
---

# Red First

One line: a passing test suite is a claim; Red First breaks each function on purpose and reports
which ones no test would notice were broken.

## The Unique Kernel

Coverage tells you a line *ran*. It cannot tell you that anything *checked* it. Red First removes
the body of one function at a time and runs the tests that actually reach it. If they all still
pass, that function is unguarded: it looks tested, it is counted as covered, and nothing in the
suite would notice if it stopped working.

The second half of the kernel is where the model sits. For an unguarded function, a model proposes
one assertion — and the proposal is only shown after the machine has run it twice: it must **fail**
against the gutted function and **pass** against the real one. A suggestion that cannot tell the
two apart is discarded without being shown. The model proposes; the mutant decides.

## Who It's For

A maintainer who inherited a repository with a green badge and 90% coverage and does not know
which parts of it are actually defended. Today they either trust the badge, or they read the tests
by hand, or they install a full mutation-testing framework and abandon it when the first run takes
forty minutes.

## The Core Loop

Point it at a repository and a test command. It maps which tests reach which functions, then for
each function it gives the body away and runs only those tests. It prints four verdicts per
function — guarded, crashed, unguarded, unreached — and exits non-zero when something unguarded
sits in the code you just changed. You run it again after writing the missing test, and watch the
verdict move.

## Inspiration & Identity

Mutation testing, narrowed to the one question people act on. Prior art it deliberately does not
try to replace: mutmut (https://github.com/boxed/mutmut) and Cosmic Ray
(https://github.com/sixty-north/cosmic-ray) apply many operators and are thorough and slow. Red
First applies exactly one brutal operator and answers in the time you will actually wait.

Tone: the same as the two projects before it — plain, evidence-first, and uncomfortable on
purpose. A report that never says anything unwelcome is not measuring anything.

## Why This Matters to the Learner

"I have shipped seven apps on the strength of suites I never audited. I want to know which of
those green checks were real." It is also the third turn of one idea: an artifact's claim, checked
against what it can actually show.

## What "Working" Looks Like

Run it against a real public Python repository with good coverage and watch it name functions that
nothing defends. Then run it against Red First's own test suite, in its own CI, and let it report
its own unguarded functions — the demo lands hardest when the tool is honest about itself.

The moment: a function with 100% line coverage, printed next to the sentence "no test in this
suite would notice if this function returned nothing."

## The POC Boundary

In: Python and pytest; one mutation operator (empty the body); coverage-driven test selection; the
four verdicts; non-zero exit; a proposed-assertion step that must pass its own before/after check.

Out of the boundary: everything that does not prove the kernel.

## Later

Other languages and runners. More operators. A cache keyed by file hash. A pull-request comment.

## Explicitly Cut

- **Full mutation testing.** Many operators multiply the runtime, and the extra verdicts do not
  change what the maintainer does next.
- **Auto-writing the missing test into the repository.** The tool proposes a checked assertion; a
  person decides where it lives. Writing tests into someone's suite on the strength of a model's
  suggestion is the failure mode this project exists to argue against.
- **A score out of 100.** A mutation score invites gaming and hides which function is undefended.
