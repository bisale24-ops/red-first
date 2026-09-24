"""Run the tests that reach one gutted function, and read the verdict off pytest.

Everything happens in a copy of the repository, in a fresh subprocess, so nothing here can touch
the working tree or reuse an already-imported module.
"""
import dataclasses
import json
import os
import pathlib
import subprocess
import tempfile
import time

# The plugin is written into the copy being examined and loaded from there, because `python -m
# pytest` already has the working directory on its path. Two earlier designs were worse: importing
# it out of this package let a project with the same package name shadow the mutated module, and
# putting it on PYTHONPATH leaked that variable into the subject's own subprocesses — which, when
# the subject was this tool, quietly repaired the mutant and produced a false "unguarded".
PLUGIN_MODULE = "_redfirst_plugin"

GUARDED, CRASHED, UNGUARDED, UNREACHED, TIMEOUT, UNMATCHED = (
    "guarded", "crashed", "unguarded", "unreached", "timeout", "unmatched")


@dataclasses.dataclass
class Verdict:
    target: object
    kind: str
    witness: str = ""        # the test that noticed, or the reason it did not
    detail: str = ""         # the exception type, when something crashed
    seconds: float = 0.0
    test_count: int = 0


def pytest_command(python, nodes, outcome_path, plugin_path, test_command=("pytest", "-q")):
    # The project's own options come along: a repository whose pytest.ini adds coverage flags
    # fails on an invented command line, and every function then looks like a collection error.
    options = [part for part in test_command[1:] if not part.startswith(("test", "."))]
    return ([python, "-m", test_command[0], "-x", "--tb=no", "-p", "no:cacheprovider",
             "-p", PLUGIN_MODULE, *options, *nodes],
            {**os.environ,
             "REDFIRST_OUTCOME": str(outcome_path),
             # CPython validates a .pyc against the source's (mtime, size), both of which have
             # one-second resolution and can collide between two mutants of similarly shaped
             # functions. When they do, the tests import the previous mutant and the verdict
             # depends on what ran before it. Writing no bytecode at all removes the race.
             "PYTHONDONTWRITEBYTECODE": "1",
             })


def run_tests(repo, python, nodes, plugin_path, timeout, test_command=("pytest", "-q")):
    """Return (passed, nodeid that failed, exception type) for one run."""
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as handle:
        outcome_path = pathlib.Path(handle.name)
    try:
        command, env = pytest_command(python, nodes, outcome_path, plugin_path, test_command)
        try:
            result = subprocess.run(command, cwd=repo, capture_output=True, text=True,
                                    env=env, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None, "", ""
        if result.returncode == 0:
            return True, "", ""
        if outcome_path.stat().st_size:
            recorded = json.loads(outcome_path.read_text())
            return False, recorded["test"], recorded["exception"]
        # pytest failed before any test ran: a collection error is not a guard
        return False, "", "CollectionError"
    finally:
        outcome_path.unlink(missing_ok=True)


def judge(repo, python, target, nodes, plugin_path, timeout, test_command=("pytest", "-q")):
    """Empty the function, run its tests, and say what the suite did about it."""
    from . import mutate
    if not nodes:
        return Verdict(target, UNREACHED, witness="no test executes this function")
    started = time.monotonic()
    with mutate.emptied(target):
        passed, witness, exception = run_tests(repo, python, nodes, plugin_path, timeout,
                                               test_command)
    seconds = time.monotonic() - started
    if passed is None:
        return Verdict(target, TIMEOUT, witness=f"{timeout:.0f}s budget", seconds=seconds,
                       test_count=len(nodes))
    if passed:
        return Verdict(target, UNGUARDED, witness=f"{len(nodes)} test(s) still passed",
                       seconds=seconds, test_count=len(nodes))
    if exception == "AssertionError":
        return Verdict(target, GUARDED, witness=witness, detail=exception, seconds=seconds,
                       test_count=len(nodes))
    return Verdict(target, CRASHED, witness=witness, detail=exception or "error",
                   seconds=seconds, test_count=len(nodes))
