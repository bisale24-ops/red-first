"""The model's suggestion has to earn its place, and these tests are about that check."""
import pathlib

from redfirst import propose, report, run, targets

from repos import build


def target_for(tmp_path, source):
    repo = build(tmp_path, {"m.py": source})
    return repo, targets.collect(repo / "pkg")[0]


def test_the_function_source_is_read_back_whole(tmp_path):
    repo, target = target_for(tmp_path, '''
        def shout(text):
            """Loudly."""
            return text.upper() + "!"
    ''')
    source = propose.source_of(target)
    assert source.startswith("def shout(text):")
    assert "upper" in source


def test_the_import_path_matches_the_package(tmp_path):
    repo, target = target_for(tmp_path, "def shout(text):\n    return text\n")
    assert propose.module_path(target, repo / "pkg") == "pkg.m"


def test_a_proposal_that_cannot_tell_the_two_versions_apart_is_rejected(tmp_path):
    repo = build(tmp_path, {"m.py": "def shout(text):\n    return text.upper()\n"},
                 {"test_m.py": "from pkg.m import shout\n\ndef test_runs():\n    shout('hi')\n"})
    target = targets.collect(repo / "pkg")[0]
    plugin = pathlib.Path(__file__).resolve().parent.parent / "src" / "redfirst" / "_plugin.py"
    installed = repo / f"{run.PLUGIN_MODULE}.py"
    installed.write_text(plugin.read_text(), encoding="utf-8")

    weak = "def test_weak():\n    from pkg.m import shout\n    shout('hi')\n"
    strong = "def test_strong():\n    from pkg.m import shout\n    assert shout('hi') == 'HI'\n"
    import sys
    assert propose.check(repo, sys.executable, target, weak, repo, 60) is False
    assert propose.check(repo, sys.executable, target, strong, repo, 60) is True


def test_a_rejected_proposal_is_counted_and_not_shown(tmp_path, monkeypatch):
    repo = build(tmp_path, {"m.py": "def shout(text):\n    return text.upper()\n"},
                 {"test_m.py": "from pkg.m import shout\n\ndef test_runs():\n    shout('hi')\n"})
    target = targets.collect(repo / "pkg")[0]
    (repo / f"{run.PLUGIN_MODULE}.py").write_text(
        (pathlib.Path(__file__).resolve().parent.parent / "src" / "redfirst" / "_plugin.py").read_text())
    monkeypatch.setattr(propose, "ask", lambda *a, **k: "def test_weak():\n    pass\n")
    import sys
    proposals, discarded = propose.for_all(
        repo, sys.executable, [run.Verdict(target, run.UNGUARDED)], repo, 60, repo / "pkg")
    assert proposals == [] and discarded == 1


def test_no_key_means_no_call_and_no_claim(monkeypatch):
    monkeypatch.setenv("REDFIRST_API_KEY", "")
    monkeypatch.setattr(propose, "KEY_FILE", pathlib.Path("/nonexistent/key"))
    assert propose.api_key() == ""
    assert propose.ask("def f(): pass", "pkg.m", "f") == ""
