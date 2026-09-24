"""Build the demo video: synthesised narration over real output.

    /tmp/ttsenv/bin/python video/build.py

Every terminal frame in `shots/` is this tool's actual output — on a toy package, on the public
tinydb repository, and on Red First itself. Nothing is retyped for the camera. The narration is
edge-tts; the last card says so.
"""
import asyncio
import pathlib
import re
import subprocess
import sys

from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).parent
SHOTS = HERE / "shots"
BUILD = HERE / "build"
VOICE = "en-US-AndrewNeural"
W, H, FPS = 1280, 720, 30

SCENES = [
    ("card:title",
     "A test suite that passes is treated as proof the code works. It is not proof. It is a claim. "
     "Coverage does not settle it either: coverage tells you a line ran, never that anything "
     "checked it."),
    ("card:idea",
     "Red First asks the question directly. It empties one function at a time and re-runs only the "
     "tests that reach it. Four answers, and all four are printed every time."),
    ("term:spike",
     "Here is the shape of the problem in five lines. Both functions are called by a test. Both "
     "have full line coverage. One is held by an assertion. The other is called and never checked, "
     "and nothing in the suite would notice it doing nothing at all."),
    ("term:tinydb",
     "On a real library — tinydb, a hundred and one functions, nineteen seconds. Six functions no "
     "test executes. Not one unguarded function, and the report says so plainly. A tool that "
     "always finds something is not measuring anything."),
    ("card:accident",
     "The finding is the other column. Thirty-nine functions are held by an assertion. Fifty-six "
     "are noticed only because an empty function broke something downstream. That is a real "
     "distinction: one says what the code should do, the other just happens to fall over."),
    ("term:self",
     "It runs against itself, in its own continuous integration, and exits non-zero when a "
     "function nothing defends is added. It is clean now. It was not when it first ran."),
    ("card:selffind",
     "The first self-run was wrong, and finding out why was the point. It called one function "
     "unguarded. Checking by hand showed the tests did fail on that mutation — so the verdict was "
     "false, and the cause was a real defect: the runner put its own directory on the python path, "
     "that variable leaked into the subprocesses the tests start, and it repaired the mutant. "
     "Two more bugs like it are in the readme. Each one is a test now."),
    ("term:explain",
     "There is one model in this, and it never decides anything. For a function nothing defends it "
     "proposes a test — and the proposal is run twice before you see it. It must pass against the "
     "real function and fail against the empty one. If it cannot tell them apart it is dropped, "
     "and the report counts how many were dropped."),
    ("card:end",
     "Red First. The model proposes; the mutant decides. M I T licensed, and the narration in this "
     "video is synthesised."),
]

CARDS = {
    "title": """<h1>Who checks the tests?</h1>
    <p class=sub>A green suite is a claim. Coverage says a line ran, not that anything looked at it.</p>
    <pre>$ pytest -q
      226 passed

$ coverage report
      TOTAL    98%</pre>
    <p class=foot>Neither number says a single test would notice if a function stopped working.</p>""",
    "idea": """<h1>Red First</h1>
    <p class=sub>Empty one function. Re-run only the tests that reach it. Read what the suite did.</p>
    <table>
      <tr><td class=no>unguarded</td><td>every test that reaches it still passed</td></tr>
      <tr><td class=no>unreached</td><td>no test executes it at all</td></tr>
      <tr><td class=a>crashed</td><td>a test failed on an exception, not an assertion — noticed by accident</td></tr>
      <tr><td class=ok>guarded</td><td>a test asserted something that stopped holding, and it is named</td></tr>
    </table>
    <p class=foot>Non-zero exit on <b>unguarded</b>, so it fits in CI as one line.</p>""",
    "accident": """<h1>Guarded, or noticed by accident</h1>
    <table>
      <tr><th></th><th>what the test says</th><th>what it proves</th></tr>
      <tr><td class=ok>guarded</td><td><code>assert shout("hi") == "HI!"</code></td>
        <td>the suite states what this function is for</td></tr>
      <tr><td class=a>crashed</td><td><code>len(make_list(3))</code> raised TypeError</td>
        <td>only that <code>None</code> broke something downstream</td></tr>
    </table>
    <p class=foot>tinydb: 39 guarded, 56 by accident. python-tabulate: 29 and 43.
    Red First itself: 10 and 25. The split is the finding.</p>""",
    "selffind": """<h1>Its first finding was about itself</h1>
    <table>
      <tr><td>The verdict</td><td><code>isolated_plugin</code> — unguarded</td></tr>
      <tr><td>Checked by hand</td><td>the tests <b>did</b> fail on that mutation. The verdict was wrong.</td></tr>
      <tr><td>The cause</td><td>the runner put its plugin directory on <code>PYTHONPATH</code>; that
        leaked into the subprocesses the tests start, and repaired the mutant</td></tr>
    </table>
    <p class=foot>Also fixed: CPython's bytecode cache is keyed on (mtime, size) — two mutants
    collided and verdicts depended on run order. And node ids were parsed from pytest's output,
    which a project's own <code>-v</code> silently empties. Three tests, three bugs.</p>""",
    "end": """<h1>Red First</h1><p class=sub>The model proposes. The mutant decides.</p>
    <p class=big>github.com/bisale24-ops/red-first</p>
    <p class=foot>MIT licensed · built with the Devpost Learn skill pack · 31 tests, no network in
    the engine · the narration in this video is synthesised, there is no presenter.</p>""",
}

SHELL = {
    "spike": ("$ red-first --repo . --source pkg", "explain.txt", 0, 5),
    "tinydb": ("$ red-first --repo ../tinydb --source tinydb --tests \"pytest -q -o addopts=\"",
               "tinydb-summary.txt", None, None),
    "self": ("$ red-first --repo . --source src/redfirst", "self-summary.txt", None, None),
    "explain": ("$ red-first --repo . --source pkg --explain", "explain.txt", 0, 9),
}

PAGE = """<!doctype html><meta charset=utf-8><style>
 body {{ margin:0; width:1280px; height:720px; background:#fbfaf7; color:#1a1a18;
   font:20px/1.5 system-ui,-apple-system,sans-serif; display:flex; flex-direction:column;
   justify-content:center; padding:0 64px; box-sizing:border-box; }}
 h1 {{ font-size:40px; margin:0 0 6px; letter-spacing:-.02em; }}
 .sub {{ color:#6b6a64; margin:0 0 26px; font-size:22px; }}
 table {{ border-collapse:collapse; font-size:19px; width:100%; }}
 td, th {{ text-align:left; padding:8px 12px; border-bottom:1px solid #e2e0d8; vertical-align:top; }}
 th {{ font-size:14px; text-transform:uppercase; letter-spacing:.06em; color:#6b6a64; }}
 .ok {{ color:#2f6f45; font-weight:600; }} .no {{ color:#8a2f2f; font-weight:600; }}
 .a {{ color:#8a5a12; font-weight:600; }}
 .big {{ font-size:28px; }} .foot {{ color:#6b6a64; font-size:16px; margin-top:22px; }}
 pre {{ font:17px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace; background:#fff;
   border:1px solid #e2e0d8; border-left:3px solid #8a5a12; border-radius:10px;
   padding:16px 18px; margin:0; white-space:pre-wrap; }}
 code {{ font-family:ui-monospace,Menlo,monospace; }}
 .term {{ background:#14140f; color:#eceae2; border-radius:12px; padding:22px 24px;
   font:16px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace; white-space:pre-wrap;
   overflow:hidden; height:600px; box-sizing:border-box; }}
 .term b {{ color:#fff; }} .term .g {{ color:#7fc79a; }} .term .a {{ color:#e0b063; }}
 .term .r {{ color:#e08a8a; }} .term .d {{ color:#9a988e; }} .term .p {{ color:#7fc79a; }}
</style>{body}"""


def shell_html(command, source, start, end):
    text = (SHOTS / source).read_text().splitlines()
    if start is None:
        start, end = 0, 26
    body = []
    if command:
        body.append(f"<span class=p>$</span> <b>{command}</b>\n")
    for line in text[start:end]:
        escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if line.startswith(("UNGUARDED", "UNREACHED")):
            escaped = f'<b><span class=r>{escaped}</span></b>'
        elif line.startswith("CRASHED"):
            escaped = f'<b><span class=a>{escaped}</span></b>'
        elif line.startswith("GUARDED"):
            escaped = f'<b><span class=g>{escaped}</span></b>'
        elif line.startswith("      "):
            escaped = f"<span class=d>{escaped}</span>"
        body.append(escaped)
    return f'<div class=term>{chr(10).join(body)}</div>'


def run(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


async def render_frames():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        for name, body in CARDS.items():
            await page.set_content(PAGE.format(body=body))
            await page.screenshot(path=str(BUILD / f"card-{name}.png"))
        for name, (command, source, start, end) in SHELL.items():
            await page.set_content(PAGE.format(body=shell_html(command, source, start, end)))
            await page.screenshot(path=str(BUILD / f"term-{name}.png"))
        await browser.close()


def narrate():
    for index, (_, line) in enumerate(SCENES):
        out = BUILD / f"line-{index:02d}.mp3"
        if not out.exists():
            subprocess.run([sys.executable.replace("python", "edge-tts"), "--voice", VOICE,
                            "--text", line, "--write-media", str(out)], check=True)


def main():
    BUILD.mkdir(exist_ok=True)
    asyncio.run(render_frames())
    narrate()
    segments = []
    for index, (frame, _) in enumerate(SCENES):
        kind, name = frame.split(":")
        image = BUILD / f"{'card' if kind == 'card' else 'term'}-{name}.png"
        audio = BUILD / f"line-{index:02d}.mp3"
        segment = BUILD / f"seg-{index:02d}.mp4"
        run("-loop", "1", "-i", str(image), "-i", str(audio),
            "-filter_complex",
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:0:color=0xfbfaf7,format=yuv420p[v];"
            f"[1:a]apad=pad_dur=0.7,aresample=48000[a]",
            "-map", "[v]", "-map", "[a]", "-r", str(FPS), "-t", f"{duration(audio) + 0.7:.2f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", str(segment))
        segments.append(segment)
    listing = BUILD / "segments.txt"
    listing.write_text("".join(f"file '{s.name}'\n" for s in segments))
    final = HERE / "red-first-demo.mp4"
    run("-f", "concat", "-safe", "0", "-i", str(listing),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        str(final))
    print(f"{final.name}  {duration(final):.1f}s")


if __name__ == "__main__":
    main()
