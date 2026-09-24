"""The whole tool against repositories whose right answer is known in advance."""
import pytest

from redfirst import cli, report

from repos import build

PACKAGE = {"m.py": '''
    def shout(text):
        return text.upper() + "!"

    def whisper(text):
        return text.lower()

    def never_called(text):
        return text.strip()
'''}

TESTS = {"test_m.py": '''
    from pkg.m import shout, whisper

    def test_shout():
        assert shout("hi") == "HI!"

    def test_whisper_runs():
        whisper("HI")
'''}


def run(repo, *extra):
    return cli.main(["--repo", str(repo), "--source", "pkg", "--tests", "pytest -q", *extra])


def verdicts(text):
    """Read the printed report back as {function: group heading}."""
    found, heading = {}, ""
    for line in text.splitlines():
        if line and not line.startswith(" "):
            heading = line.split(" ")[0]
        elif line.startswith("  ") and not line.startswith("      ") and line.strip():
            found[line.strip()] = heading
    return found


def test_the_three_answers(tmp_path, capsys):
    repo = build(tmp_path, PACKAGE, TESTS)
    code = run(repo)
    found = verdicts(capsys.readouterr().out)
    assert found["shout"] == "GUARDED"        # a test asserted its result
    assert found["whisper"] == "UNGUARDED"    # a test called it and checked nothing
    assert found["never_called"] == "UNREACHED"
    assert code == report.EXIT_UNGUARDED


def test_a_suite_that_checks_everything_exits_clean(tmp_path, capsys):
    repo = build(tmp_path, {"m.py": "def double(x):\n    return x * 2\n"},
                 {"test_m.py": "from pkg.m import double\n\n"
                               "def test_double():\n    assert double(3) == 6\n"})
    assert run(repo) == report.EXIT_OK
    assert "UNGUARDED" not in capsys.readouterr().out


def test_a_failing_suite_stops_the_run(tmp_path, capsys):
    repo = build(tmp_path, {"m.py": "def double(x):\n    return x * 2\n"},
                 {"test_m.py": "from pkg.m import double\n\n"
                               "def test_double():\n    assert double(3) == 7\n"})
    assert run(repo) == report.EXIT_BASELINE
    assert "already failing" in capsys.readouterr().out


def test_neighbouring_functions_do_not_contaminate_each_other(tmp_path, capsys):
    """Regression: two same-shaped functions in one file.

    The mutants of `subtract` and `decrement` had the same length and were written in the same
    second, so CPython reused the bytecode of the previous one and the second verdict was wrong.
    """
    repo = build(tmp_path, {"m.py": '''
        def subtract(a, b):
            return a - b

        def decrement(a):
            return a - 1
    '''}, {"test_m.py": '''
        from pkg.m import subtract, decrement

        def test_subtract():
            assert subtract(5, 2) == 3

        def test_decrement():
            assert decrement(5) == 4
    '''})
    run(repo)
    found = verdicts(capsys.readouterr().out)
    assert found["subtract"] == "GUARDED"
    assert found["decrement"] == "GUARDED"


def test_a_crash_is_not_counted_as_a_guard(tmp_path, capsys):
    """A test that only fails because `None` broke something downstream is reported separately."""
    repo = build(tmp_path, {"m.py": '''
        def make_list(n):
            return list(range(n))
    '''}, {"test_m.py": '''
        from pkg.m import make_list

        def test_length():
            assert len(make_list(3)) == 3
    '''})
    run(repo)
    found = verdicts(capsys.readouterr().out)
    assert found["make_list"] == "CRASHED"
