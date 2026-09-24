---
doc: checklist
status: approved
---

# Build checklist

1. **Targets** — walk the AST, skip what cannot be made to do less. *done, 5 tests*
2. **Mutation** — empty one body, keep the signature and docstring, restore in a `finally`.
   Generators become `yield from ()` so they stay generators. *done, 4 tests*
3. **Mapping** — coverage with per-test contexts, function → tests. *done*
4. **Runner** — run only the mapped tests, read the failure reason from a pytest plugin rather
   than from a traceback. *done*
5. **Verdicts and report** — four groups, findings first, non-zero exit on unguarded. *done*
6. **Real repository** — tinydb, then python-tabulate. Three bugs found and fixed there:
   the bytecode-cache race, plugin shadowing, and parsing pytest's output. *done*
7. **Dogfood** — Red First on Red First; fixed what it found, added nine tests. *done*
8. **Proposal step** — a model writes one test; it is accepted only if it fails on the mutant and
   passes on the original. *done, 5 tests*
9. **CI** — unit tests, then the tool against itself. *done*
10. **Video and submission.** *in progress*
