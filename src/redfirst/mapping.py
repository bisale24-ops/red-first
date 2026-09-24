"""Which tests reach which function.

coverage.py already records, per line, the test that executed it. That is exactly the map needed
to avoid running a whole suite for every function: a test that never reaches the function cannot
possibly notice it breaking.
"""
import pathlib
import subprocess

CONFIG = "[run]\ndynamic_context = test_function\nbranch = false\n"


class MappingError(RuntimeError):
    pass


def measure(repo, source, test_command, python):
    """Run the suite once under coverage and return {absolute path: {lineno: [contexts]}}."""
    repo = pathlib.Path(repo)
    config = repo / ".redfirst-coveragerc"
    config.write_text(CONFIG, encoding="utf-8")
    data_file = repo / ".redfirst-coverage"
    result = subprocess.run(
        [python, "-m", "coverage", "run", f"--rcfile={config}", f"--source={source}",
         f"--data-file={data_file}", "-m", *test_command],
        cwd=repo, capture_output=True, text=True)
    if not data_file.exists():
        raise MappingError((result.stderr or result.stdout).strip()[-2000:])

    import coverage
    data = coverage.CoverageData(basename=str(data_file))
    data.read()
    # macOS hands out /var paths that resolve to /private/var; the two sides of this comparison
    # have to agree or every function looks untested.
    return ({str(pathlib.Path(path).resolve()): data.contexts_by_lineno(path)
             for path in data.measured_files()}, result)


def tests_for(target, measured):
    """Every test context that executed a line inside this function's body."""
    by_line = measured.get(str(target.path.resolve()), {})
    tests = set()
    for line, contexts in by_line.items():
        if target.covers(line):
            tests.update(context for context in contexts if context)
    return sorted(tests)


def node_ids(repo, python, test_command=("pytest", "-q"), plugin_module="_redfirst_plugin"):
    """Map coverage's `module.test_name` contexts onto real pytest node ids.

    A parametrised test is one context and many node ids: coverage records
    `test_tinydb.test_purge` while pytest calls it `tests/test_tinydb.py::test_purge[storage0]`.
    Keying on the bare name and keeping every id behind it is what makes the map work on a real
    suite; matching them one to one silently finds nothing.
    """
    import json
    import os
    import tempfile

    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as handle:
        collected = pathlib.Path(handle.name)
    try:
        subprocess.run([python, "-m", test_command[0], "--collect-only", "-p", "no:cacheprovider",
                        "-p", plugin_module, *test_command[1:]],
                       cwd=repo, capture_output=True, text=True,
                       env={**os.environ, "REDFIRST_COLLECT": str(collected)})
        nodes = json.loads(collected.read_text() or "[]")
    except (OSError, json.JSONDecodeError):
        nodes = []
    finally:
        collected.unlink(missing_ok=True)

    mapping = {}
    for node in nodes:
        file_part, _, rest = node.partition("::")
        base = rest.split("[")[0].replace("::", ".")
        dotted = ".".join(pathlib.PurePath(file_part).with_suffix("").parts)
        for key in {f"{dotted}.{base}", f"{pathlib.Path(file_part).stem}.{base}"}:
            mapping.setdefault(key, []).append(node)
    return mapping


def nodes_for_context(context, mapping):
    """Coverage names a test by its module path; how much of that path it keeps varies."""
    if context in mapping:
        return mapping[context]
    parts = context.split(".")
    for start in range(1, len(parts) - 1):
        key = ".".join(parts[start:])
        if key in mapping:
            return mapping[key]
    return []
