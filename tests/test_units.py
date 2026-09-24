import os

from redfirst import mapping, propose, report, run


class FakeTarget:
    def __init__(self, name):
        self.qualname = name
        self.display = "pkg/m.py"
        self.lineno = 1
        self.path = "pkg/m.py"


def verdict(kind, name="f", **kwargs):
    return run.Verdict(FakeTarget(name), kind, **kwargs)


def test_findings_come_before_good_news():
    text = report.render([verdict(run.GUARDED, "a", witness="t"), verdict(run.UNGUARDED, "b")])
    assert text.index("UNGUARDED") < text.index("GUARDED  a test asserted")


def test_the_exit_code_is_about_unguarded_functions_only():
    assert report.exit_code([verdict(run.CRASHED), verdict(run.UNREACHED)]) == report.EXIT_OK
    assert report.exit_code([verdict(run.UNGUARDED)]) == report.EXIT_UNGUARDED


def test_a_dropped_proposal_is_counted_not_hidden():
    assert "2 proposed assertion(s) were dropped" in report.render([], discarded=2)


def test_a_half_open_fence_is_still_code():
    assert propose.extract('def test_x():\n    assert 1\n```') == "def test_x():\n    assert 1"
    assert propose.extract("```python\ndef test_x():\n    assert 1\n```").startswith("def test_x")
    assert propose.extract("I cannot write that test.") == ""


def test_a_context_matches_a_node_id_by_suffix():
    nodes = {"tests.test_m.test_one": ["tests/test_m.py::test_one"]}
    assert mapping.nodes_for_context("tests.test_m.test_one", nodes)
    assert mapping.nodes_for_context("deeper.tests.test_m.test_one", nodes)
    assert mapping.nodes_for_context("tests.test_m.test_other", nodes) == []


def test_one_context_can_be_many_parametrised_node_ids():
    nodes = {"tests.test_m.test_one": ["tests/test_m.py::test_one[a]", "tests/test_m.py::test_one[b]"]}
    assert len(mapping.nodes_for_context("tests.test_m.test_one", nodes)) == 2


def test_the_projects_own_pytest_options_are_kept():
    command, _ = run.pytest_command("python", ["tests/test_m.py::test_one"], "/tmp/o.json", "/src",
                                    ("pytest", "-q", "-o", "addopts="))
    assert "-o" in command and "addopts=" in command
    assert command[-1] == "tests/test_m.py::test_one"


def test_bytecode_writing_is_off_for_every_run():
    _, env = run.pytest_command("python", [], "/tmp/o.json", "/src")
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"


def test_the_runner_does_not_change_pythonpath():
    """It leaked into the subject's own subprocesses and repaired a mutant. See run.py."""
    _, env = run.pytest_command("python", [], "/tmp/o.json", "/src")
    assert env.get("PYTHONPATH", "") == os.environ.get("PYTHONPATH", "")


def test_the_html_page_escapes_the_report():
    page = report.render_html("UNGUARDED <script>alert(1)</script>")
    assert "&lt;script&gt;" in page and "<script>" not in page


def test_a_target_labels_itself_by_its_display_path(tmp_path):
    """Asserting on a stand-in would be the very thing this project argues against."""
    from redfirst import targets
    from repos import build
    repo = build(tmp_path, {"m.py": "def shout(text):\n    return text\n"})
    target = targets.collect(repo / "pkg")[0]
    target.display = "pkg/m.py"
    assert target.label == "pkg/m.py:1 shout"


def test_the_plugin_records_why_a_test_failed(tmp_path, monkeypatch):
    """The hook runs inside the inner pytest processes, so it is exercised directly here."""
    import json

    from redfirst import _plugin

    outcome = tmp_path / "outcome.json"
    monkeypatch.setenv("REDFIRST_OUTCOME", str(outcome))

    class Item:
        nodeid = "tests/test_m.py::test_one"

    class Excinfo:
        typename = "AssertionError"

    class Call:
        when = "call"
        excinfo = Excinfo()

    _plugin.pytest_runtest_makereport(Item(), Call())
    assert json.loads(outcome.read_text()) == {"test": Item.nodeid, "exception": "AssertionError"}

    outcome.unlink()
    passing = Call()
    passing.excinfo = None
    _plugin.pytest_runtest_makereport(Item(), passing)
    assert not outcome.exists()
