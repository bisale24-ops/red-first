"""red-first — break each function on purpose and see whether any test notices."""
import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

from . import mapping, report, run, targets

IGNORE = shutil.ignore_patterns(".git", ".venv", "venv", "__pycache__", ".pytest_cache",
                                "node_modules", ".mypy_cache", ".tox", "build", "dist")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="red-first", description=__doc__)
    parser.add_argument("--repo", default=".", help="repository to examine")
    parser.add_argument("--source", required=True, help="package directory, relative to the repo")
    parser.add_argument("--tests", default="pytest -q", help="test command, run as a module")
    parser.add_argument("--max-seconds", type=float, default=300.0, help="budget for the whole run")
    parser.add_argument("--timeout", type=float, default=60.0, help="budget for one function")
    parser.add_argument("--only", default="", help="substring filter on the function name")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--html", default="", help="also write the report to this path")
    parser.add_argument("--explain", action="store_true",
                        help="ask a model for one assertion per unguarded function")
    return parser.parse_args(argv)


def copy_repo(repo):
    work = pathlib.Path(tempfile.mkdtemp(prefix="redfirst-")).resolve()
    destination = work / pathlib.Path(repo).resolve().name
    shutil.copytree(repo, destination, ignore=IGNORE, symlinks=True)
    return destination


def install_plugin(work):
    """Drop the pytest plugin into the copy, where the working directory is already importable."""
    source = pathlib.Path(__file__).resolve().parent / "_plugin.py"
    installed = pathlib.Path(work) / f"{run.PLUGIN_MODULE}.py"
    installed.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return installed


def baseline_green(repo, python, test_command):
    result = subprocess.run([python, "-m", *test_command, "-p", "no:cacheprovider"],
                            cwd=repo, capture_output=True, text=True)
    return result.returncode == 0, (result.stdout or result.stderr)[-1500:]


def main(argv=None):
    args = parse_args(argv)
    test_command = args.tests.split()
    work = copy_repo(args.repo)
    plugin_path = install_plugin(work)

    green, output = baseline_green(work, args.python, test_command)
    if not green:
        print("The suite is already failing, so a mutation verdict would mean nothing.\n")
        print(output)
        return report.EXIT_BASELINE

    try:
        measured, _ = mapping.measure(work, args.source, test_command, args.python)
        whole_suite = False
    except mapping.MappingError as error:
        print(f"Could not read per-test coverage contexts: {error}", file=sys.stderr)
        measured, whole_suite = {}, True
    nodes_by_context = mapping.node_ids(work, args.python, test_command)

    found = targets.collect(work / args.source)
    for target in found:
        target.display = str(target.path.relative_to(work))
    if args.only:
        found = [target for target in found if args.only in target.qualname]

    # Any bytecode left by the baseline and coverage runs would be read by the mutation runs.
    for cached in work.rglob("__pycache__"):
        shutil.rmtree(cached, ignore_errors=True)

    verdicts, started = [], time.monotonic()
    for target in found:
        if time.monotonic() - started > args.max_seconds:
            verdicts.append(run.Verdict(target, run.TIMEOUT, witness="run budget spent"))
            continue
        contexts = mapping.tests_for(target, measured)
        nodes = sorted({node for context in contexts
                        for node in mapping.nodes_for_context(context, nodes_by_context)})
        if whole_suite:
            nodes = ["."]
        elif contexts and not nodes:
            # Tests do reach this function; we just could not name them. Saying "unreached" here
            # would be a false clean bill of health, which is the one answer this tool must never
            # give by accident.
            verdicts.append(run.Verdict(target, run.UNMATCHED, test_count=len(contexts),
                                        witness=f"{len(contexts)} coverage context(s), no node id"))
            continue
        verdicts.append(run.judge(work, args.python, target, nodes, plugin_path, args.timeout,
                                  test_command))

    proposals, discarded = [], 0
    if args.explain:
        from . import propose
        proposals, discarded = propose.for_all(work, args.python, verdicts, plugin_path,
                                               args.timeout, work / args.source, test_command)

    text = report.render(verdicts, proposals, discarded, whole_suite)
    print(text)
    if args.html:
        pathlib.Path(args.html).write_text(report.render_html(text), encoding="utf-8")
    shutil.rmtree(work.parent, ignore_errors=True)
    return report.exit_code(verdicts)


if __name__ == "__main__":
    raise SystemExit(main())
