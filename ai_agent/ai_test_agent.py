#!/usr/bin/env python3
"""
AI Test Agent - Automatically generates JUnit unit tests using Ollama (local AI).
No API key required. Triggered by the pre-push git hook on every `git push`.

Workflow:
  1. Identify changed Kotlin files (vs main branch)
  2. Filter to testable business logic files (skip Activity/Fragment)
  3. Call local Ollama model to generate JUnit 4 tests
  4. Write generated tests to the test source directory
  5. Run Gradle unit tests
  6. Parse XML results
  7. Generate HTML report
  8. Print colored terminal summary
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Ollama config — change MODEL to any model you have pulled
# ---------------------------------------------------------------------------
OLLAMA_URL  = "http://localhost:11434/api/chat"
OLLAMA_HOST = "http://localhost:11434"
MODEL       = "qwen2.5-coder:7b"   # best coding model; ~4.7 GB
TEST_DIR    = Path("app/src/test/java/com/example/unittestingproject")
PACKAGE     = "com.example.unittestingproject"


# ---------------------------------------------------------------------------
# ANSI colors
# ---------------------------------------------------------------------------
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BLUE   = "\033[94m"
    GRAY   = "\033[90m"


def cprint(color: str, msg: str):
    print(f"{color}{msg}{C.RESET}", flush=True)


# ---------------------------------------------------------------------------
# Ollama helpers
# ---------------------------------------------------------------------------
def _ensure_ollama_on_path():
    """Add the default Windows Ollama install dir to PATH if needed."""
    username = os.environ.get("USERNAME", "")
    win_dir = f"C:/Users/{username}/AppData/Local/Programs/Ollama"
    if os.path.isdir(win_dir):
        os.environ["PATH"] = win_dir + os.pathsep + os.environ.get("PATH", "")


def ollama_running() -> bool:
    """Return True if Ollama server is reachable."""
    _ensure_ollama_on_path()
    # If server not yet started, try to start it
    try:
        urllib.request.urlopen(OLLAMA_HOST, timeout=3)
        return True
    except Exception:
        # Try starting Ollama serve in background
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            import time; time.sleep(3)
            urllib.request.urlopen(OLLAMA_HOST, timeout=5)
            return True
        except Exception:
            return False


def ollama_has_model(model: str) -> bool:
    """Return True if the model is already pulled locally."""
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            names = [m["name"] for m in data.get("models", [])]
            # match with or without tag (e.g. "qwen2.5-coder:7b" or "qwen2.5-coder")
            base = model.split(":")[0]
            return any(n == model or n.startswith(base + ":") for n in names)
    except Exception:
        return False


def ollama_pull(model: str):
    """Pull a model from Ollama registry (blocking, shows progress)."""
    cprint(C.CYAN, f"  [Ollama] Pulling model '{model}' (this may take a few minutes)...")
    try:
        subprocess.run(["ollama", "pull", model], check=True)
        cprint(C.GREEN, f"  [Ollama] Model '{model}' ready.")
    except subprocess.CalledProcessError as e:
        cprint(C.RED, f"  [Ollama] Pull failed: {e}")
        sys.exit(0)
    except FileNotFoundError:
        cprint(C.RED, "  [Ollama] 'ollama' command not found. Is Ollama installed?")
        cprint(C.YELLOW, "  Download from: https://ollama.com/download")
        sys.exit(0)


def call_ollama(prompt: str) -> str:
    """Send a prompt to Ollama and return the response text."""
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 4096},
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read())
        return data["message"]["content"]


# ---------------------------------------------------------------------------
# Step 1: Identify changed Kotlin files
# ---------------------------------------------------------------------------
SKIP_PATTERNS = re.compile(
    r"(Activity|Fragment|Service|Provider|Receiver|Application|ViewModel)\.kt$"
)
KEEP_PATTERNS = re.compile(
    r"(Validator|Manager|Repository|UseCase|Helper|Util|Utils|Handler|"
    r"Mapper|Converter|Calculator|Processor|Service(?!.*Activity))\.kt$"
)


def get_changed_files(base: str, project_root: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "diff", f"{base}...HEAD", "--name-only", "--diff-filter=ACMR"],
            cwd=project_root, capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        cprint(C.YELLOW, f"[AI Agent] git diff failed: {e.stderr.strip()}")
        return []

    files = []
    for rel_path in result.stdout.splitlines():
        if not rel_path.endswith(".kt"):
            continue
        abs_path = project_root / rel_path
        name = abs_path.name
        if SKIP_PATTERNS.search(name):
            cprint(C.GRAY, f"  [skip] {rel_path}  (Activity/Fragment)")
            continue
        if not KEEP_PATTERNS.search(name):
            cprint(C.GRAY, f"  [skip] {rel_path}  (not a testable class suffix)")
            continue
        files.append(abs_path)
    return files


# ---------------------------------------------------------------------------
# Step 2: Generate tests with Ollama
# ---------------------------------------------------------------------------
def build_prompt(source_code: str, class_name: str, existing_test: str | None) -> str:
    existing_section = ""
    if existing_test:
        existing_section = f"""
## Existing test file (already covered — DO NOT duplicate these tests):
```kotlin
{existing_test}
```
"""
    return f"""You are an expert Android / Kotlin testing engineer.

Generate a complete JUnit 4 unit test file in Kotlin for the class below.

## Rules (STRICT — violations cause build failures):
1. Package declaration: `package {PACKAGE}` (exactly this, first line)
2. Imports: ONLY `org.junit.Test`, `org.junit.Assert.*`, `org.junit.Before`, `org.junit.After`
   - NO Mockito, NO Robolectric, NO AndroidX, NO Android SDK imports
   - These tests run on the JVM without an emulator
3. Use JUnit 4 annotations: @Test, @Before, @After  (NOT JUnit 5)
4. Class name: `{class_name}GeneratedTest`
5. Test method names use Kotlin backtick syntax: fun `methodName - scenario description`()
6. Cover: happy paths, edge cases, boundary values, null/blank inputs, every branch
7. Output ONLY valid Kotlin code — no markdown fences, no explanation text
{existing_section}
## Source file to test (`{class_name}.kt`):
```kotlin
{source_code}
```

Generate the complete test file now:"""


def generate_tests(source_file: Path, project_root: Path) -> tuple[str, str] | None:
    """Returns (test_file_name, test_code) or None on failure."""
    class_name = source_file.stem
    source_code = source_file.read_text(encoding="utf-8")

    test_dir_abs   = project_root / TEST_DIR
    base_test      = test_dir_abs / f"{class_name}Test.kt"
    generated_test = test_dir_abs / f"{class_name}_GeneratedTest.kt"

    existing_test_code = None
    if base_test.exists():
        existing_test_code = base_test.read_text(encoding="utf-8")
    elif generated_test.exists():
        existing_test_code = generated_test.read_text(encoding="utf-8")

    prompt = build_prompt(source_code, class_name, existing_test_code)

    cprint(C.CYAN, f"  [Ollama] Generating tests for {class_name}...")
    try:
        raw = call_ollama(prompt).strip()
    except urllib.error.URLError as e:
        cprint(C.RED, f"  [Ollama] Connection error for {class_name}: {e}")
        return None
    except Exception as e:
        cprint(C.RED, f"  [Ollama] Error for {class_name}: {e}")
        return None

    # Strip accidental markdown fences
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    # Determine output filename
    if not base_test.exists():
        out_name = f"{class_name}Test.kt"
    elif not generated_test.exists():
        out_name = f"{class_name}_GeneratedTest.kt"
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name = f"{class_name}_Generated_{ts}Test.kt"

    return out_name, raw.strip()


# ---------------------------------------------------------------------------
# Step 3: Write generated test files
# ---------------------------------------------------------------------------
def write_test_file(file_name: str, content: str, project_root: Path) -> Path:
    test_dir_abs = project_root / TEST_DIR
    test_dir_abs.mkdir(parents=True, exist_ok=True)
    out_path = test_dir_abs / file_name
    out_path.write_text(content, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Step 4: Run Gradle tests
# ---------------------------------------------------------------------------
def run_gradle_tests(project_root: Path) -> tuple[int, str]:
    cprint(C.CYAN, "\n[Gradle] Running testDebugUnitTest...")
    gradlew = "gradlew.bat" if sys.platform.startswith("win") else "./gradlew"
    try:
        result = subprocess.run(
            [gradlew, "testDebugUnitTest", "--continue"],
            cwd=project_root, capture_output=True, text=True, timeout=300,
        )
        return result.returncode, result.stdout + "\n" + result.stderr
    except subprocess.TimeoutExpired:
        return 1, "[AI Agent] Gradle timed out after 5 minutes."
    except FileNotFoundError:
        return 1, f"[AI Agent] Gradle wrapper not found at {project_root}/{gradlew}"


# ---------------------------------------------------------------------------
# Step 5: Parse XML test results
# ---------------------------------------------------------------------------
def parse_test_results(project_root: Path) -> list[dict]:
    results_dir = project_root / "app/build/test-results/testDebugUnitTest"
    suites = []
    if not results_dir.exists():
        return suites

    for xml_file in sorted(results_dir.glob("TEST-*.xml")):
        try:
            root = ET.parse(xml_file).getroot()
        except ET.ParseError:
            continue

        suite = {
            "name":     root.get("name", xml_file.stem),
            "tests":    int(root.get("tests", 0)),
            "failures": int(root.get("failures", 0)),
            "errors":   int(root.get("errors", 0)),
            "skipped":  int(root.get("skipped", 0)),
            "time":     float(root.get("time", 0.0)),
            "failures_list": [],
        }
        suite["passed"] = suite["tests"] - suite["failures"] - suite["errors"] - suite["skipped"]

        for tc in root.findall("testcase"):
            elem = tc.find("failure") or tc.find("error")
            if elem is not None:
                suite["failures_list"].append({
                    "classname": tc.get("classname", ""),
                    "name":      tc.get("name", ""),
                    "message":   elem.get("message", ""),
                    "detail":    (elem.text or "").strip(),
                })
        suites.append(suite)
    return suites


# ---------------------------------------------------------------------------
# Step 6: Generate HTML report
# ---------------------------------------------------------------------------
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Test Agent Report — {branch}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0d1117; color: #c9d1d9; line-height: 1.6; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 24px 16px; }}
  h1 {{ font-size: 1.6rem; color: #58a6ff; margin-bottom: 4px; }}
  .meta {{ color: #8b949e; font-size: 0.9rem; margin-bottom: 24px; }}
  .badge {{ display: inline-block; padding: 4px 14px; border-radius: 20px;
            font-weight: 700; font-size: 1rem; margin-bottom: 24px; }}
  .badge-pass {{ background: #1a4731; color: #3fb950; border: 1px solid #3fb950; }}
  .badge-fail {{ background: #4d1f1f; color: #f85149; border: 1px solid #f85149; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 12px; margin-bottom: 24px; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
           padding: 16px; text-align: center; }}
  .card .num {{ font-size: 2rem; font-weight: 700; }}
  .card .lbl {{ font-size: 0.8rem; color: #8b949e; text-transform: uppercase; }}
  .num-pass {{ color: #3fb950; }} .num-fail {{ color: #f85149; }}
  .num-skip {{ color: #d29922; }} .num-total {{ color: #58a6ff; }}
  section {{ margin-bottom: 28px; }}
  h2 {{ font-size: 1.1rem; color: #58a6ff; border-bottom: 1px solid #30363d;
        padding-bottom: 6px; margin-bottom: 12px; }}
  ul {{ padding-left: 20px; }} li {{ margin-bottom: 4px; font-size: 0.9rem; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
  th, td {{ padding: 8px 12px; border: 1px solid #30363d; text-align: left; }}
  th {{ background: #161b22; color: #8b949e; font-weight: 600; }}
  tr:nth-child(even) {{ background: #0d1117; }} tr:nth-child(odd) {{ background: #161b22; }}
  .status-pass {{ color: #3fb950; font-weight: 600; }}
  .status-fail {{ color: #f85149; font-weight: 600; }}
  .detail-box {{ background: #0d1117; border: 1px solid #30363d; border-radius: 6px;
                 padding: 12px; font-family: monospace; font-size: 0.82rem;
                 white-space: pre-wrap; word-break: break-all; max-height: 200px;
                 overflow-y: auto; color: #f85149; margin-top: 4px; }}
  .gradle-box {{ background: #0d1117; border: 1px solid #30363d; border-radius: 6px;
                 padding: 12px; font-family: monospace; font-size: 0.8rem;
                 white-space: pre-wrap; word-break: break-all; max-height: 360px;
                 overflow-y: auto; color: #c9d1d9; }}
</style>
</head>
<body>
<div class="container">
  <h1>AI Test Agent Report</h1>
  <div class="meta">Branch: <strong>{branch}</strong> &nbsp;|&nbsp;
       Generated: <strong>{timestamp}</strong> &nbsp;|&nbsp;
       Model: <strong>{model}</strong> (local Ollama)</div>
  <div class="badge {badge_class}">{overall_status}</div>
  <div class="cards">
    <div class="card"><div class="num num-total">{total}</div><div class="lbl">Total</div></div>
    <div class="card"><div class="num num-pass">{passed}</div><div class="lbl">Passed</div></div>
    <div class="card"><div class="num num-fail">{failed}</div><div class="lbl">Failed</div></div>
    <div class="card"><div class="num num-skip">{skipped}</div><div class="lbl">Skipped</div></div>
  </div>
  <section><h2>Changed Files Analyzed</h2>{changed_files_html}</section>
  <section><h2>AI-Generated Test Files</h2>{generated_files_html}</section>
  <section><h2>Test Suite Results</h2>{suites_table_html}</section>
  {failures_section_html}
  <section><h2>Gradle Output (last 50 lines)</h2>
    <div class="gradle-box">{gradle_output_html}</div></section>
</div>
</body>
</html>
"""


def generate_html_report(branch, timestamp, changed_files, generated_files,
                         suites, gradle_output, project_root) -> Path:
    import html as hl

    total   = sum(s["tests"]   for s in suites)
    passed  = sum(s["passed"]  for s in suites)
    failed  = sum(s["failures"] + s["errors"] for s in suites)
    skipped = sum(s["skipped"] for s in suites)

    cf_html = (
        "<ul>" + "".join(f"<li>{hl.escape(f.name)}</li>" for f in changed_files) + "</ul>"
        if changed_files else "<p style='color:#8b949e'>No eligible files changed.</p>"
    )
    gf_html = (
        "<ul>" + "".join(
            f"<li><code>{hl.escape(n)}</code> — {hl.escape(a)}</li>"
            for n, a in generated_files
        ) + "</ul>"
        if generated_files else "<p style='color:#8b949e'>No test files generated.</p>"
    )

    if suites:
        rows = "".join(
            f"<tr><td>{hl.escape(s['name'])}</td><td>{s['tests']}</td>"
            f"<td style='color:#3fb950'>{s['passed']}</td>"
            f"<td style='color:#f85149'>{s['failures']+s['errors']}</td>"
            f"<td style='color:#d29922'>{s['skipped']}</td>"
            f"<td>{s['time']:.2f}s</td>"
            f"<td class='{'status-pass' if s['failures']+s['errors']==0 else 'status-fail'}'>"
            f"{'PASSED' if s['failures']+s['errors']==0 else 'FAILED'}</td></tr>"
            for s in suites
        )
        suites_html = (
            "<table><thead><tr><th>Suite</th><th>Tests</th><th>Pass</th>"
            "<th>Fail</th><th>Skip</th><th>Time</th><th>Status</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )
    else:
        suites_html = "<p style='color:#8b949e'>No test results found.</p>"

    all_failures = [f for s in suites for f in s["failures_list"]]
    if all_failures:
        frows = "".join(
            f"<tr><td>{hl.escape(f['classname'])}</td><td>{hl.escape(f['name'])}</td>"
            f"<td>{hl.escape(f['message'])}</td></tr>"
            f"<tr><td colspan='3'><div class='detail-box'>{hl.escape(f['detail'])}</div></td></tr>"
            for f in all_failures
        )
        fail_section = (
            "<section><h2>Failure Details</h2>"
            "<table><thead><tr><th>Class</th><th>Test</th><th>Message</th></tr></thead>"
            f"<tbody>{frows}</tbody></table></section>"
        )
    else:
        fail_section = ""

    gradle_html = hl.escape("\n".join(gradle_output.strip().splitlines()[-50:]))
    safe_branch = re.sub(r"[^a-zA-Z0-9_\-]", "_", branch)
    ts_file = datetime.now().strftime("%Y%m%d_%H%M%S")

    content = HTML_TEMPLATE.format(
        branch=hl.escape(branch), timestamp=timestamp, model=MODEL,
        badge_class="badge-pass" if failed == 0 else "badge-fail",
        overall_status="ALL TESTS PASSED" if failed == 0 else "TESTS FAILED",
        total=total, passed=passed, failed=failed, skipped=skipped,
        changed_files_html=cf_html, generated_files_html=gf_html,
        suites_table_html=suites_html, failures_section_html=fail_section,
        gradle_output_html=gradle_html,
    )

    reports_dir = project_root / "ai_agent" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"report_{safe_branch}_{ts_file}.html"
    report_path.write_text(content, encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# Step 7: Terminal summary
# ---------------------------------------------------------------------------
def print_summary(branch, changed_files, generated_files, suites, report_path):
    total   = sum(s["tests"]   for s in suites)
    passed  = sum(s["passed"]  for s in suites)
    failed  = sum(s["failures"] + s["errors"] for s in suites)
    skipped = sum(s["skipped"] for s in suites)

    print()
    cprint(C.BOLD + C.BLUE, "=" * 60)
    cprint(C.BOLD + C.BLUE, "  AI TEST AGENT — RESULTS SUMMARY")
    cprint(C.BOLD + C.BLUE, "=" * 60)
    cprint(C.CYAN,  f"  Branch   : {branch}")
    cprint(C.CYAN,  f"  Model    : {MODEL} (local Ollama)")
    cprint(C.CYAN,  f"  Analyzed : {len(changed_files)} file(s)")
    cprint(C.CYAN,  f"  Generated: {len(generated_files)} test file(s)")
    print()
    if suites:
        cprint((C.GREEN if failed == 0 else C.RED) + C.BOLD,
               f"  Overall  : {'PASSED' if failed == 0 else 'FAILED'}")
        cprint(C.CYAN,  f"  Total    : {total}")
        cprint(C.GREEN, f"  Passed   : {passed}")
        if failed:  cprint(C.RED,    f"  Failed   : {failed}")
        if skipped: cprint(C.YELLOW, f"  Skipped  : {skipped}")
    else:
        cprint(C.YELLOW, "  No test results found.")
    print()
    cprint(C.CYAN, f"  Report   : {report_path}")
    cprint(C.BOLD + C.BLUE, "=" * 60)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="AI Test Agent (Ollama)")
    parser.add_argument("--branch",       required=True)
    parser.add_argument("--base",         default="main")
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    branch, base = args.branch, args.base
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cprint(C.BOLD + C.CYAN, "\n[AI Test Agent] Starting (Ollama — no API key needed)...")
    cprint(C.CYAN, f"  Branch: {branch}  |  Base: {base}  |  Root: {project_root}")

    # Check Ollama is running
    if not ollama_running():
        cprint(C.RED, "\n[AI Test Agent] ERROR: Ollama is not running.")
        cprint(C.YELLOW, "  Start it with:  ollama serve")
        cprint(C.YELLOW, "  Or just open the Ollama app from your taskbar.")
        cprint(C.YELLOW, "  Push is NOT blocked.")
        sys.exit(0)
    cprint(C.GREEN, "  [Ollama] Server is running.")

    # Ensure model is pulled
    if not ollama_has_model(MODEL):
        cprint(C.YELLOW, f"  [Ollama] Model '{MODEL}' not found locally. Pulling now...")
        ollama_pull(MODEL)

    # Step 1: Find changed files
    cprint(C.CYAN, "\n[Step 1] Identifying changed Kotlin files...")
    changed_files = get_changed_files(base, project_root)
    if not changed_files:
        cprint(C.YELLOW, "  No eligible Kotlin files changed. Nothing to do.")
        sys.exit(0)
    for f in changed_files:
        cprint(C.GREEN, f"  [eligible] {f.name}")

    # Step 2 + 3: Generate and write tests
    cprint(C.CYAN, "\n[Step 2] Generating tests with Ollama...")
    generated_files: list[tuple[str, str]] = []
    for source_file in changed_files:
        result = generate_tests(source_file, project_root)
        if result is None:
            continue
        out_name, test_code = result
        out_path = write_test_file(out_name, test_code, project_root)
        action = "created" if "_Generated" not in out_name else "generated (existing preserved)"
        generated_files.append((out_name, action))
        cprint(C.GREEN, f"  [written] {out_path.relative_to(project_root)}")

    if not generated_files:
        cprint(C.YELLOW, "  No test files were generated.")
        sys.exit(0)

    # Step 4: Run Gradle
    cprint(C.CYAN, "\n[Step 3] Running Gradle unit tests...")
    gradle_rc, gradle_output = run_gradle_tests(project_root)
    cprint(C.GREEN if gradle_rc == 0 else C.YELLOW,
           "  Gradle finished." if gradle_rc == 0 else f"  Gradle exited {gradle_rc}.")

    # Step 5: Parse results
    cprint(C.CYAN, "\n[Step 4] Parsing test results...")
    suites = parse_test_results(project_root)
    cprint(C.CYAN, f"  Found {len(suites)} test suite(s).")

    # Step 6: HTML report
    cprint(C.CYAN, "\n[Step 5] Generating HTML report...")
    report_path = generate_html_report(
        branch, timestamp, changed_files, generated_files,
        suites, gradle_output, project_root,
    )
    cprint(C.GREEN, f"  Report: {report_path}")

    # Step 7: Summary
    print_summary(branch, changed_files, generated_files, suites, report_path)


if __name__ == "__main__":
    main()
