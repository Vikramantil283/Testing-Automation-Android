#!/usr/bin/env python3
"""
AI Test Agent v2
─────────────────────────────────────────────────────────────────────────────
Improvements over v1:
  • Incremental runs  — tracks last-run SHA; only processes files changed
                        since the previous agent run, not all of main..HEAD
  • Build validation  — compiles after writing each test; deletes the file
                        and reports errors if it doesn't compile
  • Correct naming    — class name always equals file-stem (no duplicates)
  • Stricter prompt   — @Test enforced on every method; no null on non-null
  • Method-level report — HTML shows every test method name + pass/fail
  • Connected device  — runs instrumented tests if adb device is found
─────────────────────────────────────────────────────────────────────────────
"""

import argparse, json, os, re, subprocess, sys, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# ── config ───────────────────────────────────────────────────────────────────
OLLAMA_URL    = "http://localhost:11434/api/chat"
OLLAMA_HOST   = "http://localhost:11434"
MODEL         = "qwen2.5-coder:7b"
TEST_DIR      = Path("app/src/test/java/com/example/unittestingproject")
PACKAGE       = "com.example.unittestingproject"
LAST_RUN_FILE = Path("ai_agent/.last_run_sha")   # relative to project root

# ── ANSI colours ─────────────────────────────────────────────────────────────
class C:
    RESET  = "\033[0m";  BOLD   = "\033[1m"
    GREEN  = "\033[92m"; RED    = "\033[91m"; YELLOW = "\033[93m"
    CYAN   = "\033[96m"; BLUE   = "\033[94m"; GRAY   = "\033[90m"

def cprint(col, msg): print(f"{col}{msg}{C.RESET}", flush=True)

# ── SHA tracking ─────────────────────────────────────────────────────────────
def get_last_run_sha(project_root: Path) -> str | None:
    p = project_root / LAST_RUN_FILE
    return p.read_text().strip() if p.exists() else None

def save_last_run_sha(project_root: Path):
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root, capture_output=True, text=True
    ).stdout.strip()
    p = project_root / LAST_RUN_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(sha)
    return sha

# ── Ollama ────────────────────────────────────────────────────────────────────
def _add_ollama_path():
    d = f"C:/Users/{os.environ.get('USERNAME','')}/AppData/Local/Programs/Ollama"
    if os.path.isdir(d): os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH","")

def ollama_running() -> bool:
    _add_ollama_path()
    try:
        urllib.request.urlopen(OLLAMA_HOST, timeout=3); return True
    except Exception:
        try:
            subprocess.Popen(["ollama","serve"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import time; time.sleep(4)
            urllib.request.urlopen(OLLAMA_HOST, timeout=5); return True
        except Exception: return False

def ollama_has_model(model: str) -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5) as r:
            names = [m["name"] for m in json.loads(r.read()).get("models",[])]
            base  = model.split(":")[0]
            return any(n == model or n.startswith(base+":") for n in names)
    except: return False

def ollama_pull(model: str):
    cprint(C.CYAN, f"  [Ollama] Pulling '{model}' (may take a few minutes)…")
    try:
        subprocess.run(["ollama","pull",model], check=True)
        cprint(C.GREEN, f"  [Ollama] '{model}' ready.")
    except Exception as e:
        cprint(C.RED, f"  [Ollama] Pull failed: {e}"); sys.exit(0)

def call_ollama(prompt: str) -> str:
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role":"user","content":prompt}],
        "stream": False,
        "options": {"temperature":0.1, "num_predict":4096},
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=payload,
        headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())["message"]["content"]

# ── Step 1 : find changed files ───────────────────────────────────────────────
SKIP = re.compile(r"(Activity|Fragment|Service|Provider|Receiver|Application|ViewModel)\.kt$")
KEEP = re.compile(r"(Validator|Manager|Repository|UseCase|Helper|Util|Utils|Handler|"
                  r"Mapper|Converter|Calculator|Processor)\.kt$")

def get_changed_files(base: str, project_root: Path) -> tuple[list[Path], str]:
    """Return (eligible_files, diff_description)."""
    last_sha = get_last_run_sha(project_root)

    if last_sha:
        diff_range = f"{last_sha}..HEAD"
        diff_label = f"since last agent run ({last_sha[:7]}..HEAD)"
    else:
        diff_range = f"{base}...HEAD"
        diff_label = f"first run — comparing {base}...HEAD"

    cprint(C.CYAN, f"  Diff range: {diff_label}")

    try:
        r = subprocess.run(
            ["git","diff", diff_range, "--name-only","--diff-filter=ACMR"],
            cwd=project_root, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        cprint(C.YELLOW, f"  git diff failed: {e.stderr.strip()}"); return [], diff_label

    files = []
    for rel in r.stdout.splitlines():
        if not rel.endswith(".kt"): continue
        p = project_root / rel
        if SKIP.search(p.name):
            cprint(C.GRAY, f"  [skip] {p.name}  (Activity/Fragment)")
        elif not KEEP.search(p.name):
            cprint(C.GRAY, f"  [skip] {p.name}  (not a testable suffix)")
        elif not p.exists():
            cprint(C.GRAY, f"  [skip] {p.name}  (file deleted)")
        else:
            files.append(p)
    return files, diff_label

# ── Step 2 : build prompt ─────────────────────────────────────────────────────
def build_prompt(source_code: str, class_name: str,
                 out_class_name: str, existing_test: str | None) -> str:
    existing_section = ""
    if existing_test:
        existing_section = (
            "\n## Existing tests (DO NOT duplicate these):\n"
            f"```kotlin\n{existing_test}\n```\n"
        )
    return f"""You are an expert Kotlin/Android testing engineer.
Generate a complete JUnit 4 unit test file for the class below.

## CRITICAL RULES — violating any rule causes a compile error:
1. First line: `package {PACKAGE}`
2. Import every annotation you use:
   `import org.junit.Test`
   `import org.junit.Before`
   `import org.junit.After`
   `import org.junit.Assert.*`
   — NO other imports (no Mockito, no Robolectric, no Android SDK)
3. Class name must be EXACTLY: `{out_class_name}`
4. EVERY test method MUST have `@Test` on the line directly above it — NO exceptions.
5. Test method names use backtick syntax:  fun `methodName - scenario`()
6. Never pass `null` to a non-nullable parameter. Check parameter types in the source.
7. Output ONLY valid Kotlin code — no markdown fences, no prose, no comments outside code.
{existing_section}
## Source to test (`{class_name}.kt`):
```kotlin
{source_code}
```

Generate the complete test file now. Remember: EVERY test method needs @Test."""

# ── Step 3 : generate ─────────────────────────────────────────────────────────
def generate_tests(source_file: Path, project_root: Path) -> tuple[str, str, str] | None:
    """Returns (out_file_name, class_name, test_code) or None on failure."""
    class_name   = source_file.stem
    source_code  = source_file.read_text(encoding="utf-8")
    test_dir_abs = project_root / TEST_DIR

    # Determine output filename + class name (class name = file stem)
    base_test      = test_dir_abs / f"{class_name}Test.kt"
    gen_test       = test_dir_abs / f"{class_name}_GeneratedTest.kt"

    if not base_test.exists():
        out_name       = f"{class_name}Test.kt"
        out_class_name = f"{class_name}Test"
    elif not gen_test.exists():
        out_name       = f"{class_name}_GeneratedTest.kt"
        out_class_name = f"{class_name}_GeneratedTest"
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name       = f"{class_name}_Generated_{ts}Test.kt"
        out_class_name = f"{class_name}_Generated_{ts}Test"

    # Read existing test as context
    existing = None
    for candidate in [base_test, gen_test]:
        if candidate.exists():
            existing = candidate.read_text(encoding="utf-8"); break

    prompt = build_prompt(source_code, class_name, out_class_name, existing)

    cprint(C.CYAN, f"  [Ollama] Generating tests for {class_name} → {out_name}…")
    try:
        raw = call_ollama(prompt).strip()
    except Exception as e:
        cprint(C.RED, f"  [Ollama] Error for {class_name}: {e}"); return None

    # Strip accidental markdown fences
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw).strip()

    # Post-process: ensure every fun with backtick name has @Test above it
    raw = _inject_missing_test_annotations(raw)

    return out_name, out_class_name, raw

def _inject_missing_test_annotations(code: str) -> str:
    """Add @Test before any backtick test method that is missing it."""
    lines  = code.splitlines()
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        is_test_fn = re.match(r"fun\s+`", stripped) or re.match(r"fun\s+`", stripped)
        if is_test_fn:
            # Check if previous non-blank line already has @Test
            prev = next((result[j] for j in range(len(result)-1,-1,-1)
                         if result[j].strip()), "")
            if not prev.strip().startswith("@Test"):
                indent = len(line) - len(line.lstrip())
                result.append(" " * indent + "@Test")
        result.append(line)
        i += 1
    return "\n".join(result)

# ── Step 4 : write + compile-validate ────────────────────────────────────────
def write_and_validate(out_name: str, content: str,
                       project_root: Path) -> tuple[Path | None, str | None]:
    """
    Write the test file, then compile-check it.
    Returns (path, None) on success, (None, error_summary) on compile failure.
    """
    test_dir_abs = project_root / TEST_DIR
    test_dir_abs.mkdir(parents=True, exist_ok=True)
    out_path = test_dir_abs / out_name
    out_path.write_text(content, encoding="utf-8")

    cprint(C.CYAN, f"    Compile-checking {out_name}…")
    gradlew = "gradlew.bat" if sys.platform.startswith("win") else "./gradlew"
    result  = subprocess.run(
        [gradlew, "compileDebugUnitTestSources", "--rerun-tasks"],
        cwd=project_root, capture_output=True, text=True, timeout=180)

    if result.returncode == 0:
        cprint(C.GREEN, f"    ✓ Compiles OK — {out_name}")
        return out_path, None

    # Check if the error mentions our file
    combined = result.stdout + result.stderr
    if out_name.replace(".kt","") in combined or out_name in combined:
        # Extract relevant error lines
        err_lines = [l for l in combined.splitlines()
                     if out_name.replace(".kt","") in l or "error:" in l.lower()]
        summary = "\n".join(err_lines[:15])
        cprint(C.RED, f"    ✗ Compile FAILED — deleting {out_name}")
        cprint(C.GRAY, f"    Errors:\n{summary}")
        out_path.unlink(missing_ok=True)
        return None, summary
    else:
        # Compile error is from a different file — keep ours
        cprint(C.YELLOW, f"    ⚠ Compile error in another file — keeping {out_name}")
        return out_path, None

# ── Step 5 : Gradle tests ─────────────────────────────────────────────────────
def has_connected_device() -> bool:
    try:
        r = subprocess.run(["adb","devices"], capture_output=True, text=True, timeout=5)
        return any("\tdevice" in l for l in r.stdout.splitlines()[1:])
    except: return False

def run_gradle_tests(project_root: Path) -> tuple[int, str, bool]:
    """Returns (rc, output, ran_on_device)."""
    gradlew = "gradlew.bat" if sys.platform.startswith("win") else "./gradlew"
    device  = has_connected_device()

    task = "connectedDebugAndroidTest" if device else "testDebugUnitTest"
    cprint(C.CYAN, f"\n[Gradle] Running {task}" +
           (" (device connected!)" if device else " (JVM only)"))

    try:
        r = subprocess.run([gradlew, task, "--continue"],
            cwd=project_root, capture_output=True, text=True, timeout=300)
        return r.returncode, r.stdout+"\n"+r.stderr, device
    except subprocess.TimeoutExpired:
        return 1, "[Agent] Gradle timed out after 5 min.", device
    except FileNotFoundError:
        return 1, f"[Agent] gradlew not found in {project_root}", device

# ── Step 6 : parse XML ────────────────────────────────────────────────────────
def parse_test_results(project_root: Path, ran_on_device: bool) -> list[dict]:
    if ran_on_device:
        results_dir = project_root / "app/build/outputs/androidTest-results/connected"
    else:
        results_dir = project_root / "app/build/test-results/testDebugUnitTest"

    suites = []
    if not results_dir.exists(): return suites

    for xml_file in sorted(results_dir.rglob("TEST-*.xml")):
        try: root = ET.parse(xml_file).getroot()
        except ET.ParseError: continue

        suite = {
            "name":     root.get("name", xml_file.stem),
            "tests":    int(root.get("tests", 0)),
            "failures": int(root.get("failures", 0)),
            "errors":   int(root.get("errors", 0)),
            "skipped":  int(root.get("skipped", 0)),
            "time":     float(root.get("time", 0.0)),
            "cases":    [],          # ← list of individual test methods
            "failures_list": [],
        }
        suite["passed"] = (suite["tests"] - suite["failures"]
                           - suite["errors"] - suite["skipped"])

        for tc in root.findall("testcase"):
            fail = tc.find("failure") or tc.find("error")
            skip = tc.find("skipped")
            status = "PASS"
            if fail is not None: status = "FAIL"
            elif skip is not None: status = "SKIP"

            suite["cases"].append({
                "classname": tc.get("classname",""),
                "name":      tc.get("name",""),
                "time":      float(tc.get("time", 0.0)),
                "status":    status,
            })
            if fail is not None:
                suite["failures_list"].append({
                    "classname": tc.get("classname",""),
                    "name":      tc.get("name",""),
                    "message":   fail.get("message",""),
                    "detail":    (fail.text or "").strip(),
                })
        suites.append(suite)
    return suites

# ── Step 7 : HTML report ──────────────────────────────────────────────────────
def generate_html_report(branch, timestamp, diff_label, changed_files,
                         generated_files, failed_validations,
                         suites, gradle_output, ran_on_device, project_root) -> Path:
    import html as hl

    total   = sum(s["tests"]   for s in suites)
    passed  = sum(s["passed"]  for s in suites)
    failed  = sum(s["failures"]+s["errors"] for s in suites)
    skipped = sum(s["skipped"] for s in suites)

    # ── changed files
    cf_html = ("<ul>" + "".join(f"<li>{hl.escape(f.name)}</li>"
               for f in changed_files) + "</ul>") if changed_files \
        else "<p class='muted'>No eligible files changed.</p>"

    # ── generated files
    gf_rows = "".join(
        f"<tr><td><code>{hl.escape(n)}</code></td><td class='ok'>✓ written</td>"
        f"<td>{hl.escape(a)}</td></tr>"
        for n,a in generated_files)
    fv_rows = "".join(
        f"<tr><td><code>{hl.escape(n)}</code></td>"
        f"<td class='fail'>✗ compile failed</td>"
        f"<td><pre class='small'>{hl.escape(e[:300])}</pre></td></tr>"
        for n,e in failed_validations)
    gf_html = (f"<table><thead><tr><th>File</th><th>Status</th><th>Note</th></tr></thead>"
               f"<tbody>{gf_rows}{fv_rows}</tbody></table>") if (generated_files or failed_validations) \
        else "<p class='muted'>No test files generated.</p>"

    # ── suites table
    if suites:
        suite_rows = "".join(
            f"<tr><td>{hl.escape(s['name'])}</td>"
            f"<td>{s['tests']}</td>"
            f"<td class='ok'>{s['passed']}</td>"
            f"<td class='fail'>{s['failures']+s['errors']}</td>"
            f"<td class='warn'>{s['skipped']}</td>"
            f"<td>{s['time']:.2f}s</td>"
            f"<td class='{'ok' if s['failures']+s['errors']==0 else 'fail'}'>"
            f"{'PASSED' if s['failures']+s['errors']==0 else 'FAILED'}</td></tr>"
            for s in suites)
        suites_html = (
            "<table><thead><tr><th>Suite</th><th>Total</th><th>Pass</th>"
            "<th>Fail</th><th>Skip</th><th>Time</th><th>Status</th></tr></thead>"
            f"<tbody>{suite_rows}</tbody></table>")
    else:
        suites_html = "<p class='muted'>No results found.</p>"

    # ── test methods table
    all_cases = [c for s in suites for c in s["cases"]]
    if all_cases:
        method_rows = "".join(
            f"<tr><td class='mono'>{hl.escape(c['classname'].split('.')[-1])}</td>"
            f"<td class='mono'>{hl.escape(c['name'])}</td>"
            f"<td class='{'ok' if c['status']=='PASS' else 'fail' if c['status']=='FAIL' else 'warn'}'>"
            f"{c['status']}</td>"
            f"<td>{c['time']:.3f}s</td></tr>"
            for c in all_cases)
        methods_html = (
            "<table><thead><tr><th>Class</th><th>Test Method</th>"
            "<th>Result</th><th>Time</th></tr></thead>"
            f"<tbody>{method_rows}</tbody></table>")
    else:
        methods_html = "<p class='muted'>No test methods found.</p>"

    # ── failures
    all_failures = [f for s in suites for f in s["failures_list"]]
    fail_section = ""
    if all_failures:
        frows = "".join(
            f"<tr><td>{hl.escape(f['classname'].split('.')[-1])}</td>"
            f"<td class='mono'>{hl.escape(f['name'])}</td>"
            f"<td>{hl.escape(f['message'])}</td></tr>"
            f"<tr><td colspan='3'><pre class='err'>{hl.escape(f['detail'][:600])}</pre></td></tr>"
            for f in all_failures)
        fail_section = (
            "<section><h2>Failure Details</h2>"
            "<table><thead><tr><th>Class</th><th>Method</th><th>Message</th></tr></thead>"
            f"<tbody>{frows}</tbody></table></section>")

    gradle_html = hl.escape("\n".join(gradle_output.strip().splitlines()[-60:]))
    safe_branch = re.sub(r"[^a-zA-Z0-9_\-]","_",branch)
    ts_file     = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_mode    = "Connected Device" if ran_on_device else "JVM Unit Tests"

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>AI Test Agent — {hl.escape(branch)}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#0d1117;color:#c9d1d9;line-height:1.6}}
.wrap{{max-width:1100px;margin:0 auto;padding:24px 16px}}
h1{{font-size:1.6rem;color:#58a6ff;margin-bottom:4px}}
.meta{{color:#8b949e;font-size:.9rem;margin-bottom:20px}}
.badge{{display:inline-block;padding:4px 16px;border-radius:20px;
        font-weight:700;font-size:1rem;margin-bottom:20px}}
.badge-pass{{background:#1a4731;color:#3fb950;border:1px solid #3fb950}}
.badge-fail{{background:#4d1f1f;color:#f85149;border:1px solid #f85149}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));
        gap:12px;margin-bottom:24px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;
       padding:14px;text-align:center}}
.num{{font-size:2rem;font-weight:700}}
.lbl{{font-size:.75rem;color:#8b949e;text-transform:uppercase}}
section{{margin-bottom:28px}}
h2{{font-size:1.05rem;color:#58a6ff;border-bottom:1px solid #30363d;
    padding-bottom:6px;margin-bottom:12px}}
table{{width:100%;border-collapse:collapse;font-size:.85rem}}
th,td{{padding:7px 12px;border:1px solid #30363d;text-align:left}}
th{{background:#161b22;color:#8b949e;font-weight:600}}
tr:nth-child(even){{background:#0d1117}}tr:nth-child(odd){{background:#161b22}}
.ok{{color:#3fb950;font-weight:600}}.fail{{color:#f85149;font-weight:600}}
.warn{{color:#d29922;font-weight:600}}.muted{{color:#8b949e}}
.mono{{font-family:monospace;font-size:.82rem}}
pre.small{{font-family:monospace;font-size:.78rem;white-space:pre-wrap;
           word-break:break-all;color:#f85149}}
pre.err{{font-family:monospace;font-size:.78rem;white-space:pre-wrap;
         word-break:break-all;color:#f85149;background:#0d1117;
         padding:8px;border-radius:4px;max-height:160px;overflow-y:auto}}
.gradle-box{{background:#0d1117;border:1px solid #30363d;border-radius:6px;
             padding:12px;font-family:monospace;font-size:.78rem;
             white-space:pre-wrap;word-break:break-all;max-height:400px;
             overflow-y:auto;color:#c9d1d9}}
ul{{padding-left:20px}}li{{margin-bottom:4px;font-size:.9rem}}
</style></head>
<body><div class="wrap">
<h1>AI Test Agent Report</h1>
<div class="meta">
  Branch: <strong>{hl.escape(branch)}</strong> &nbsp;|&nbsp;
  {hl.escape(timestamp)} &nbsp;|&nbsp;
  Model: <strong>{MODEL}</strong> (local Ollama) &nbsp;|&nbsp;
  Run mode: <strong>{run_mode}</strong><br>
  <span style="color:#8b949e">Diff: {hl.escape(diff_label)}</span>
</div>
<div class="badge {'badge-pass' if failed==0 else 'badge-fail'}">
  {'ALL TESTS PASSED' if failed==0 else 'TESTS FAILED'}
</div>
<div class="cards">
  <div class="card"><div class="num" style="color:#58a6ff">{total}</div><div class="lbl">Total</div></div>
  <div class="card"><div class="num ok">{passed}</div><div class="lbl">Passed</div></div>
  <div class="card"><div class="num fail">{failed}</div><div class="lbl">Failed</div></div>
  <div class="card"><div class="num warn">{skipped}</div><div class="lbl">Skipped</div></div>
</div>
<section><h2>Changed Files Analysed</h2>{cf_html}</section>
<section><h2>Generated Test Files</h2>{gf_html}</section>
<section><h2>Test Suite Summary</h2>{suites_html}</section>
<section><h2>Test Methods</h2>{methods_html}</section>
{fail_section}
<section><h2>Gradle Output (last 60 lines)</h2>
<div class="gradle-box">{gradle_html}</div></section>
</div></body></html>"""

    rd = project_root / "ai_agent" / "reports"
    rd.mkdir(parents=True, exist_ok=True)
    rp = rd / f"report_{safe_branch}_{ts_file}.html"
    rp.write_text(html, encoding="utf-8")
    return rp

# ── Step 8 : terminal summary ─────────────────────────────────────────────────
def print_summary(branch, changed, generated, failed_val, suites, report_path, diff_label):
    total   = sum(s["tests"]   for s in suites)
    passed  = sum(s["passed"]  for s in suites)
    failed  = sum(s["failures"]+s["errors"] for s in suites)
    skipped = sum(s["skipped"] for s in suites)

    print()
    cprint(C.BOLD+C.BLUE, "="*62)
    cprint(C.BOLD+C.BLUE, "  AI TEST AGENT v2 — RESULTS SUMMARY")
    cprint(C.BOLD+C.BLUE, "="*62)
    cprint(C.CYAN,  f"  Branch   : {branch}")
    cprint(C.CYAN,  f"  Diff     : {diff_label}")
    cprint(C.CYAN,  f"  Model    : {MODEL} (local Ollama)")
    cprint(C.CYAN,  f"  Analysed : {len(changed)} file(s)")
    cprint(C.GREEN, f"  Written  : {len(generated)} test file(s)")
    if failed_val:
        cprint(C.RED, f"  Rejected : {len(failed_val)} file(s) failed compile")
    print()

    if suites:
        col = C.GREEN if failed == 0 else C.RED
        cprint(col+C.BOLD, f"  Overall  : {'PASSED' if failed==0 else 'FAILED'}")
        cprint(C.CYAN,  f"  Total    : {total}")
        cprint(C.GREEN, f"  Passed   : {passed}")
        if failed:  cprint(C.RED,    f"  Failed   : {failed}")
        if skipped: cprint(C.YELLOW, f"  Skipped  : {skipped}")
    else:
        cprint(C.YELLOW, "  No test results found.")

    print()
    cprint(C.CYAN, f"  Report   : {report_path}")
    cprint(C.BOLD+C.BLUE, "="*62)
    print()

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AI Test Agent v2")
    parser.add_argument("--branch",       required=True)
    parser.add_argument("--base",         default="main")
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    branch, base = args.branch, args.base
    timestamp    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cprint(C.BOLD+C.CYAN, "\n[AI Test Agent v2] Starting (Ollama — no API key needed)…")
    cprint(C.CYAN, f"  Branch: {branch}  |  Base: {base}  |  Root: {project_root}")

    # ── Ollama
    if not ollama_running():
        cprint(C.RED,    "\n[Agent] ERROR: Ollama not running.")
        cprint(C.YELLOW, "  Start it: ollama serve   (or open the Ollama app)")
        sys.exit(0)
    cprint(C.GREEN, "  [Ollama] Server is running.")

    if not ollama_has_model(MODEL):
        cprint(C.YELLOW, f"  [Ollama] Model '{MODEL}' not found. Pulling…")
        ollama_pull(MODEL)

    # ── Step 1 : find changed files
    cprint(C.CYAN, "\n[Step 1] Identifying changed Kotlin files…")
    changed_files, diff_label = get_changed_files(base, project_root)

    if not changed_files:
        cprint(C.YELLOW, "  No eligible Kotlin files changed since last run. Nothing to do.")
        cprint(C.GRAY,   "  (Run 'git test-gen' after committing new business logic files)")
        sys.exit(0)

    for f in changed_files:
        cprint(C.GREEN, f"  [eligible] {f.name}")

    # ── Steps 2+3+4 : generate + validate
    cprint(C.CYAN, "\n[Step 2] Generating & validating tests…")
    generated_files:   list[tuple[str,str]] = []   # (name, note)
    failed_validations: list[tuple[str,str]] = []   # (name, error)

    for src in changed_files:
        result = generate_tests(src, project_root)
        if result is None:
            continue
        out_name, out_class, test_code = result

        out_path, compile_err = write_and_validate(out_name, test_code, project_root)
        if out_path:
            note = "created" if "_Generated" not in out_name else "generated (existing preserved)"
            generated_files.append((out_name, note))
            cprint(C.GREEN, f"  [kept]    {out_path.relative_to(project_root)}")
        else:
            failed_validations.append((out_name, compile_err or ""))
            cprint(C.RED, f"  [deleted] {out_name}  — compile failed")

    if not generated_files:
        cprint(C.YELLOW, "\n  No valid test files were produced.")
        # Still save SHA so next run is incremental
        save_last_run_sha(project_root)
        sys.exit(0)

    # ── Step 5 : run tests
    cprint(C.CYAN, "\n[Step 3] Running tests…")
    gradle_rc, gradle_output, ran_on_device = run_gradle_tests(project_root)
    cprint(C.GREEN if gradle_rc==0 else C.YELLOW,
           f"  Gradle finished (exit {gradle_rc}).")

    # ── Step 6 : parse results
    cprint(C.CYAN, "\n[Step 4] Parsing results…")
    suites = parse_test_results(project_root, ran_on_device)
    total_methods = sum(len(s["cases"]) for s in suites)
    cprint(C.CYAN, f"  {len(suites)} suite(s), {total_methods} method(s).")

    # ── Step 7 : HTML report
    cprint(C.CYAN, "\n[Step 5] Generating HTML report…")
    report_path = generate_html_report(
        branch, timestamp, diff_label,
        changed_files, generated_files, failed_validations,
        suites, gradle_output, ran_on_device, project_root)
    cprint(C.GREEN, f"  Report: {report_path}")

    # ── Step 8 : save last-run SHA (only after success)
    new_sha = save_last_run_sha(project_root)
    cprint(C.GRAY, f"  Last-run SHA saved: {new_sha[:12]}")

    # ── Summary
    print_summary(branch, changed_files, generated_files,
                  failed_validations, suites, report_path, diff_label)

if __name__ == "__main__":
    main()
