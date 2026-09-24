"""A pytest plugin that records *why* a test failed, not just that it did.

The difference between "a test asserted something and the assertion did not hold" and "the code
blew up because a function suddenly returned None" is the difference between a suite that checks
this function and a suite that merely touches it. Reading that off a traceback is guesswork, so
the runner asks pytest directly.
"""
import json
import os


def pytest_collection_modifyitems(items):
    """Report the collected node ids to a file.

    Reading them off pytest's printed output is a guess about the project's verbosity settings; a
    project that sets `-v` prints a tree with no node ids in it at all.
    """
    path = os.environ.get("REDFIRST_COLLECT")
    if not path:
        return
    with open(path, "w", encoding="utf-8") as handle:
        json.dump([item.nodeid for item in items], handle)


def pytest_runtest_makereport(item, call):
    if call.when != "call" or call.excinfo is None:
        return
    path = os.environ.get("REDFIRST_OUTCOME")
    if not path:
        return
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"test": item.nodeid, "exception": call.excinfo.typename}, handle)
