"""Ask a model for the missing test, then refuse to believe it.

This is the only place a model appears, and it never decides anything. It proposes one test for a
function nothing defends; the proposal is then run twice, against the real function and against
the emptied one. It is shown only if it passes the first and fails the second — that is, only if
it can tell working code from code that does nothing. Anything else is dropped without being
printed, because an unchecked suggestion is exactly the kind of unearned confidence this tool
exists to measure.
"""
import dataclasses
import json
import os
import pathlib
import re
import urllib.error
import urllib.request

from . import mutate, run

DEFAULT_BASE = "https://api.publicai.co/v1"
DEFAULT_MODEL = "swiss-ai/apertus-v1.5-70b"
KEY_FILE = pathlib.Path.home() / ".config" / "publicai.key"

PROMPT = """You are writing one pytest test for a function that the existing suite does not check.

The function:

```python
{source}
```

It is imported as: from {module} import {name}

Write a single pytest test function. It must fail if the function's body is replaced by
`return None`, so assert on the value it returns or on an effect it has. Use only the standard
library and pytest. No comments, no explanation, no markdown around it. Start with `def test_`.
"""


@dataclasses.dataclass
class Proposal:
    target: object
    assertion: str


def api_key():
    key = os.environ.get("REDFIRST_API_KEY", "")
    if not key and KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()
    return key


def ask(source, module, name, timeout=60):
    key = api_key()
    if not key:
        return ""
    body = json.dumps({
        "model": os.environ.get("REDFIRST_MODEL", DEFAULT_MODEL),
        "messages": [{"role": "user", "content": PROMPT.format(source=source, module=module, name=name)}],
        "temperature": 0.2,
        "max_tokens": 400,
    }).encode()
    request = urllib.request.Request(
        f"{os.environ.get('REDFIRST_API_BASE', DEFAULT_BASE)}/chat/completions",
        data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                            # The gateway sits behind a proxy that rejects urllib's default
                            # User-Agent with an opaque 403; curl works, so the header is the
                            # difference. Worth stating rather than leaving as folklore.
                            "User-Agent": "red-first/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return ""
    return payload.get("choices", [{}])[0].get("message", {}).get("content", "")


def extract(text):
    """The model is asked for bare code and usually sends it wrapped anyway.

    A half-open fence is common enough — a closing ``` with no opening one — that stripping every
    fence line is more reliable than matching a pair.
    """
    code = "\n".join(line for line in text.splitlines() if not line.strip().startswith("```"))
    start = code.find("def test_")
    return code[start:].strip() if start >= 0 else ""


def source_of(target):
    lines = target.path.read_text(encoding="utf-8").splitlines(keepends=True)
    return "".join(lines[target.lineno - 1:target.body_end])


def module_path(target, source_root):
    relative = target.path.relative_to(source_root.parent).with_suffix("")
    return ".".join(relative.parts)


def check(repo, python, target, code, plugin_path, timeout, test_command=("pytest", "-q")):
    """A proposal earns its place by passing on the real function and failing on the empty one."""
    test_file = pathlib.Path(repo) / "test_redfirst_proposal.py"
    test_file.write_text(code + "\n", encoding="utf-8")
    try:
        passes_on_real, _, _ = run.run_tests(repo, python, [test_file.name], plugin_path,
                                             timeout, test_command)
        if passes_on_real is not True:
            return False
        with mutate.emptied(target):
            passes_on_empty, _, _ = run.run_tests(repo, python, [test_file.name], plugin_path,
                                                  timeout, test_command)
        return passes_on_empty is False
    finally:
        test_file.unlink(missing_ok=True)


def for_all(repo, python, verdicts, plugin_path, timeout, source_root=None,
            test_command=("pytest", "-q")):
    proposals, discarded = [], 0
    for verdict in verdicts:
        if verdict.kind != run.UNGUARDED:
            continue
        target = verdict.target
        module = module_path(target, source_root) if source_root else target.path.stem
        code = extract(ask(source_of(target), module, target.qualname.split(".")[-1]))
        if code and check(repo, python, target, code, plugin_path, timeout, test_command):
            proposals.append(Proposal(target, code))
        else:
            discarded += 1
    return proposals, discarded
