"""Small repositories, built on the spot.

Every test here asserts against a suite written by the test itself, so the expected verdict is
known before the tool runs. No fixture repository is checked in and nothing reaches the network.
"""
import pathlib
import textwrap


def build(tmp_path, package: dict, tests: dict = None, name="pkg"):
    tests = tests or {}
    repo = pathlib.Path(tmp_path)
    (repo / name).mkdir(parents=True, exist_ok=True)
    (repo / name / "__init__.py").write_text("", encoding="utf-8")
    for filename, body in package.items():
        (repo / name / filename).write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    (repo / "tests").mkdir(exist_ok=True)
    for filename, body in tests.items():
        (repo / "tests" / filename).write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    return repo
