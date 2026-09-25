"""Four groups, in the order a maintainer needs them.

The findings come first and the good news last, because a report that opens with a score is a
report nobody reads to the end.
"""
from .run import CRASHED, GUARDED, TIMEOUT, UNGUARDED, UNMATCHED, UNREACHED

EXIT_OK = 0
EXIT_UNGUARDED = 1
EXIT_BASELINE = 3

HEADINGS = {
    UNGUARDED: "UNGUARDED  nothing in the suite would notice this function doing nothing",
    UNREACHED: "UNREACHED  no test executes this function at all",
    CRASHED: ("CRASHED  the suite only noticed by accident: an exception, not an assertion. "
              "Nothing here says what this function should do"),
    TIMEOUT: "NOT CHECKED  the time budget ran out before these were judged",
    UNMATCHED: ("NOT CHECKED  tests reach these, but their coverage contexts could not be matched "
                "to pytest node ids"),
    GUARDED: "GUARDED  a test asserted something that stopped holding",
}
ORDER = [UNGUARDED, UNREACHED, CRASHED, TIMEOUT, UNMATCHED, GUARDED]


def group(verdicts):
    grouped = {kind: [] for kind in ORDER}
    for verdict in verdicts:
        grouped[verdict.kind].append(verdict)
    return grouped


WHOLE_SUITE_NOTICE = (
    "Per-test coverage contexts were unavailable, so every function was judged against the whole "
    "suite.\nThat is slower, and it changes what one verdict means: a function no test calls at "
    "all cannot be\ntold apart from one the tests call and ignore, so it appears under UNGUARDED "
    "rather than UNREACHED."
)


def render(verdicts, proposals=(), discarded=0, whole_suite=False):
    grouped = group(verdicts)
    lines = []
    if whole_suite:
        # at the top, not the bottom: it changes how every UNGUARDED below must be read
        lines.append(WHOLE_SUITE_NOTICE)
        lines.append("")
    for kind in ORDER:
        entries = grouped[kind]
        if not entries:
            continue
        lines.append(f"{HEADINGS[kind]}  ({len(entries)})")
        for verdict in entries:
            lines.append(f"  {verdict.target.qualname}")
            lines.append(f"      {verdict.target.display or verdict.target.path}:{verdict.target.lineno}")
            if kind == GUARDED:
                lines.append(f"      caught by {verdict.witness}")
            elif kind == CRASHED:
                lines.append(f"      {verdict.witness} raised {verdict.detail}")
            else:
                lines.append(f"      {verdict.witness}")
            for proposal in proposals:
                if proposal.target is verdict.target:
                    lines.append("      proposed assertion, checked against both versions:")
                    lines.extend(f"        {line}" for line in proposal.assertion.splitlines())
        lines.append("")
    if discarded:
        lines.append(f"{discarded} proposed assertion(s) were dropped: they could not tell the "
                     f"real function from the empty one.")
    return "\n".join(lines).rstrip() + "\n"


def exit_code(verdicts):
    return EXIT_UNGUARDED if any(v.kind == UNGUARDED for v in verdicts) else EXIT_OK


PAGE = """<!doctype html><meta charset=utf-8><title>Red First</title><style>
 body {{ background:#fbfaf7; color:#1a1a18; font:16px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;
   margin:0; padding:40px; }}
 pre {{ white-space:pre-wrap; margin:0; max-width:980px; }}
 h1 {{ font:600 28px/1.2 system-ui,sans-serif; margin:0 0 4px; }}
 p.sub {{ font:15px/1.5 system-ui,sans-serif; color:#6b6a64; margin:0 0 26px; }}
</style><h1>Red First</h1>
<p class=sub>A passing suite is a claim. Each function below was emptied on purpose; this is what
the tests did about it.</p><pre>{body}</pre>"""


def render_html(text):
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return PAGE.format(body=escaped)
