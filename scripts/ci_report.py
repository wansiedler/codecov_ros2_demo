#!/usr/bin/env python3
"""Compose the CI report: run Summary, sticky pull request comment, metrics JSON.

Reads what the build + test + coverage job left behind and turns it into one
page a reviewer can act on without opening a single log:

* every test suite with its counts and time, every failed case with its message,
  the slowest cases;
* line, function and branch coverage with the delta against the last successful
  run on the default branch, per file, with the exact uncovered line ranges;
* the compiler warnings of the instrumented build (the release build turns
  them into errors, the coverage build only prints them);
* the verdict of every job in the run.

The same text goes to the run Summary in full and to a pull request comment
trimmed to GitHub's 64 KiB limit. Earlier report comments are folded as
outdated so the current one always sits at the bottom of the conversation.

Usage (see .github/workflows/ci.yml for the arguments the report job passes):

    scripts/ci_report.py --junit DIR --lcov coverage.info --build-log build.log \\
        --jobs jobs.json --baseline baseline.json --metrics-out report.json \\
        --summary "$GITHUB_STEP_SUMMARY" [--post]
"""

from __future__ import annotations

import argparse
import dataclasses
import glob
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

# The XML is written by gtest and launch_testing in the job that just ran, not
# fetched from anywhere, so the stdlib parser is not exposed to hostile input.
import xml.etree.ElementTree as ElementTree  # nosec B405

MARKER = "<!-- ci-report -->"
COMMENT_LIMIT = 65536
API = "https://api.github.com"
# codecov.yml paints 60...90 as the yellow band; the same bands colour the files here.
COVERAGE_RED, COVERAGE_GREEN = 60.0, 90.0
SLOWEST_CASES = 5
MAX_WARNING_ROWS = 200
MAX_FAILURE_TEXT = 1500

WARNING_RE = re.compile(
    r"^(?P<path>[^:\s][^:]*):(?P<line>\d+):(?:(?P<col>\d+):)? warning: (?P<msg>.*)$"
)
FLAG_RE = re.compile(r"\s*\[(-W[^\]]+)\]\s*$")


# ----------------------------------------------------------------------------
# Test results
# ----------------------------------------------------------------------------


@dataclasses.dataclass
class Case:
    """One test case as JUnit records it."""

    suite: str
    name: str
    time: float
    status: str  # passed | failed | error | skipped
    message: str = ""


@dataclasses.dataclass
class Suite:
    """One JUnit suite (one gtest binary, one launch test)."""

    name: str
    cases: list[Case] = dataclasses.field(default_factory=list)

    @property
    def time(self) -> float:
        return sum(c.time for c in self.cases)

    def count(self, status: str) -> int:
        return sum(1 for c in self.cases if c.status == status)


def _suite_elements(root: ElementTree.Element) -> list[ElementTree.Element]:
    if root.tag == "testsuite":
        return [root]
    return list(root.iter("testsuite"))


def _case_status(case: ElementTree.Element) -> tuple[str, str]:
    for tag, status in (("failure", "failed"), ("error", "error"), ("skipped", "skipped")):
        node = case.find(tag)
        if node is not None:
            message = (node.get("message") or "").strip()
            body = (node.text or "").strip()
            # gtest repeats the message inside the body; keep the longer one
            text = body if message in body else f"{message}\n{body}".strip()
            return status, text
    if case.get("status") == "notrun" or case.get("result") == "suppressed":
        return "skipped", ""
    return "passed", ""


def load_suites(junit_dir: str) -> list[Suite]:
    """Every *.xml under junit_dir, one Suite per <testsuite>."""
    suites: list[Suite] = []
    for path in sorted(glob.glob(os.path.join(junit_dir, "**", "*.xml"), recursive=True)):
        try:
            # nosemgrep: python.lang.security.use-defused-xml-parse.use-defused-xml-parse
            root = ElementTree.parse(path).getroot()  # nosec B314
        except ElementTree.ParseError:
            continue
        for element in _suite_elements(root):
            name = element.get("name") or pathlib.Path(path).stem
            suite = Suite(name=name)
            for case in element.iter("testcase"):
                status, message = _case_status(case)
                classname = case.get("classname") or ""
                case_name = case.get("name") or "?"
                if classname and classname != name:
                    case_name = f"{classname}.{case_name}"
                suite.cases.append(
                    Case(
                        suite=name,
                        name=case_name,
                        time=float(case.get("time") or 0.0),
                        status=status,
                        message=message,
                    )
                )
            if suite.cases:
                suites.append(suite)
    return suites


# ----------------------------------------------------------------------------
# Coverage
# ----------------------------------------------------------------------------


@dataclasses.dataclass
class FileCoverage:
    """lcov totals for one source file plus its uncovered lines."""

    path: str
    lines_found: int = 0
    lines_hit: int = 0
    functions_found: int = 0
    functions_hit: int = 0
    branches_found: int = 0
    branches_hit: int = 0
    uncovered: list[int] = dataclasses.field(default_factory=list)

    @property
    def lines(self) -> float | None:
        return pct(self.lines_hit, self.lines_found)

    @property
    def functions(self) -> float | None:
        return pct(self.functions_hit, self.functions_found)

    @property
    def branches(self) -> float | None:
        return pct(self.branches_hit, self.branches_found)


def pct(hit: int, found: int) -> float | None:
    """Percentage rounded to one decimal, None when nothing was found."""
    if not found:
        return None
    return round(100.0 * hit / found, 1)


def load_lcov(path: str, workspace: str) -> list[FileCoverage]:
    """Parse an lcov tracefile; paths are made relative to the workspace."""
    files: list[FileCoverage] = []
    current: FileCoverage | None = None
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return files
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("SF:"):
            source = line[3:]
            if workspace and source.startswith(workspace):
                source = source[len(workspace) :].lstrip("/")
            current = FileCoverage(path=source)
        elif current is None:
            continue
        elif line.startswith("DA:"):
            number, _, count = line[3:].partition(",")
            count = count.split(",")[0]  # DA:line,count[,checksum]
            if count.isdigit() and int(count) == 0:
                current.uncovered.append(int(number))
        elif line.startswith("LF:"):
            current.lines_found = int(line[3:])
        elif line.startswith("LH:"):
            current.lines_hit = int(line[3:])
        elif line.startswith("FNF:"):
            current.functions_found = int(line[4:])
        elif line.startswith("FNH:"):
            current.functions_hit = int(line[4:])
        elif line.startswith("BRF:"):
            current.branches_found = int(line[4:])
        elif line.startswith("BRH:"):
            current.branches_hit = int(line[4:])
        elif line == "end_of_record":
            files.append(current)
            current = None
    return sorted(files, key=lambda f: f.path)


def ranges(numbers: list[int]) -> str:
    """12, 13, 14, 20 -> "12-14, 20"."""
    out: list[str] = []
    start = prev = None
    for n in sorted(set(numbers)):
        if start is None:
            start = prev = n
        elif n == prev + 1:
            prev = n
        else:
            out.append(str(start) if start == prev else f"{start}-{prev}")
            start = prev = n
    if start is not None:
        out.append(str(start) if start == prev else f"{start}-{prev}")
    return ", ".join(out)


def totals(files: list[FileCoverage]) -> dict[str, float | None]:
    return {
        "lines": pct(sum(f.lines_hit for f in files), sum(f.lines_found for f in files)),
        "functions": pct(
            sum(f.functions_hit for f in files), sum(f.functions_found for f in files)
        ),
        "branches": pct(sum(f.branches_hit for f in files), sum(f.branches_found for f in files)),
    }


# ----------------------------------------------------------------------------
# Compiler warnings
# ----------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Warning:
    """One compiler diagnostic of severity warning."""

    path: str
    line: int
    flag: str
    message: str


def load_warnings(path: str, workspace: str) -> list[Warning]:
    """Distinct `file:line: warning: ...` diagnostics from a build log."""
    seen: set[Warning] = set()
    ordered: list[Warning] = []
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ordered
    for raw in text.splitlines():
        match = WARNING_RE.match(raw.strip())
        if not match:
            continue
        source = match.group("path")
        if workspace and source.startswith(workspace):
            source = source[len(workspace) :].lstrip("/")
        message = match.group("msg")
        flag_match = FLAG_RE.search(message)
        flag = flag_match.group(1) if flag_match else ""
        if flag_match:
            message = message[: flag_match.start()]
        warning = Warning(source, int(match.group("line")), flag, message.strip())
        if warning not in seen:
            seen.add(warning)
            ordered.append(warning)
    return ordered


# ----------------------------------------------------------------------------
# Markdown
# ----------------------------------------------------------------------------


def cell(value: object, limit: int = 160) -> str:
    """A value safe inside a Markdown table cell."""
    text = str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}%"


def band(value: float | None) -> str:
    if value is None:
        return "⚪"
    if value < COVERAGE_RED:
        return "🔴"
    if value < COVERAGE_GREEN:
        return "🟡"
    return "🟢"


def delta(current: float | None, previous: float | None) -> str:
    if current is None or previous is None:
        return "new" if previous is None and current is not None else ""
    diff = round(current - previous, 1)
    if diff > 0:
        return f"▲ {diff:+.1f}"
    if diff < 0:
        return f"▼ {diff:+.1f}"
    return "="


def fmt_time(seconds: float) -> str:
    return f"{seconds:.3f} s" if seconds < 10 else f"{seconds:.1f} s"


def tests_section(suites: list[Suite]) -> tuple[list[str], dict[str, object]]:
    """Markdown lines and the metrics of the test results."""
    if not suites:
        return (
            [
                "### 🧪 Tests",
                "",
                "_No JUnit results were produced - the build or the test step did not get "
                "that far._",
                "",
            ],
            {},
        )
    cases = [c for s in suites for c in s.cases]
    counts = {
        k: sum(1 for c in cases if c.status == k) for k in ("passed", "failed", "error", "skipped")
    }
    total_time = sum(s.time for s in suites)
    ok = counts["failed"] == 0 and counts["error"] == 0
    lines = [
        "### 🧪 Tests",
        "",
        f"{'✅' if ok else '❌'} **{len(cases)} tests** - {counts['passed']} passed, "
        f"{counts['failed']} failed, {counts['error']} errors, {counts['skipped']} skipped "
        f"in {fmt_time(total_time)} across {len(suites)} suite(s)",
        "",
        "| suite | tests | ✅ | ❌ | ⏭️ | time |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for suite in suites:
        bad = suite.count("failed") + suite.count("error")
        lines.append(
            f"| {'❌' if bad else '✅'} `{cell(suite.name, 80)}` | {len(suite.cases)} | "
            f"{suite.count('passed')} | {bad} | {suite.count('skipped')} | {fmt_time(suite.time)} |"
        )
    lines.append("")
    problems = [c for c in cases if c.status in ("failed", "error")]
    if problems:
        lines += ["<details open>", f"<summary>❌ {len(problems)} failing case(s)</summary>", ""]
        for case in problems:
            lines.append(f"**`{case.suite}` / `{case.name}`** ({case.status})")
            lines.append("")
            text = case.message or "(no message recorded)"
            if len(text) > MAX_FAILURE_TEXT:
                text = text[:MAX_FAILURE_TEXT] + "\n... (truncated)"
            lines += ["```", text.replace("```", "'''"), "```", ""]
        lines.append("</details>")
        lines.append("")
    slowest = sorted(cases, key=lambda c: c.time, reverse=True)[:SLOWEST_CASES]
    if slowest and slowest[0].time > 0:
        lines += [
            "<details>",
            f"<summary>⏱️ Slowest {len(slowest)} case(s)</summary>",
            "",
            "| case | time |",
            "| --- | ---: |",
        ]
        lines += [
            f"| `{cell(c.suite, 60)}` / `{cell(c.name, 80)}` | {fmt_time(c.time)} |"
            for c in slowest
        ]
        lines += ["", "</details>", ""]
    metrics: dict[str, object] = {
        "tests": len(cases),
        "tests_passed": counts["passed"],
        "tests_failed": counts["failed"] + counts["error"],
        "tests_skipped": counts["skipped"],
        "tests_time": round(total_time, 3),
        "suites": {s.name: len(s.cases) for s in suites},
    }
    return lines, metrics


def coverage_section(
    files: list[FileCoverage], baseline: dict[str, object]
) -> tuple[list[str], dict[str, object]]:
    """Markdown lines and the metrics of the coverage report."""
    if not files:
        return (
            [
                "### 📊 Coverage",
                "",
                "_No coverage tracefile - a failing test stops `make coverage` before lcov runs._",
                "",
            ],
            {},
        )
    current = totals(files)
    base_totals = {k: baseline.get(k) for k in ("lines", "functions", "branches")}
    base_files: dict[str, dict[str, float | None]] = baseline.get("files") or {}  # type: ignore[assignment]
    head = " / ".join(
        f"**{k}** {band(current[k])} {fmt_pct(current[k])}"
        + (
            f" ({delta(current[k], base_totals[k])} vs main)"
            if base_totals.get(k) is not None
            else ""
        )
        for k in ("lines", "functions", "branches")
    )
    lines = [
        "### 📊 Coverage",
        "",
        head,
        "",
        "| file | lines | Δ main | functions | branches | uncovered lines |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for f in sorted(files, key=lambda f: (f.lines if f.lines is not None else 101.0, f.path)):
        previous = (base_files.get(f.path) or {}).get("lines") if base_files else None
        uncovered = ranges(f.uncovered) or "-"
        lines.append(
            f"| `{cell(f.path, 120)}` | {band(f.lines)} {fmt_pct(f.lines)} "
            f"({f.lines_hit}/{f.lines_found}) | "
            f"{delta(f.lines, previous) if base_files else ''} | {fmt_pct(f.functions)} | "
            f"{fmt_pct(f.branches)} | {cell(uncovered, 200)} |"
        )
    gone = sorted(set(base_files) - {f.path for f in files}) if base_files else []
    if gone:
        lines.append("")
        lines.append(
            "Files in the main baseline that no longer appear: " + ", ".join(f"`{p}`" for p in gone)
        )
    if not base_files and not any(v is not None for v in base_totals.values()):
        lines.append("")
        lines.append(
            "_No baseline from the default branch yet - the Δ column fills in after the "
            "next successful run on main._"
        )
    lines.append("")
    metrics: dict[str, object] = {
        **{k: v for k, v in current.items() if v is not None},
        "files": {
            f.path: {"lines": f.lines, "functions": f.functions, "branches": f.branches}
            for f in files
        },
    }
    return lines, metrics


def warnings_section(warnings: list[Warning]) -> tuple[list[str], dict[str, object]]:
    """Markdown lines and the metrics of the compiler warnings."""
    if not warnings:
        return ["### 🛠️ Compiler warnings", "", "✅ none in the instrumented build", ""], {
            "warnings": 0
        }
    lines = [
        "### 🛠️ Compiler warnings",
        "",
        f"⚠️ **{len(warnings)}** distinct warning(s) in the instrumented build "
        "(the gcc and clang jobs build with `-Werror`, so these are the ones only "
        "`-DCOVERAGE=ON` sees)",
        "",
        "| location | flag | message |",
        "| --- | --- | --- |",
    ]
    for w in warnings[:MAX_WARNING_ROWS]:
        flag = f"`{cell(w.flag, 60)}`" if w.flag else ""
        lines.append(f"| `{cell(w.path, 120)}:{w.line}` | {flag} | {cell(w.message, 200)} |")
    if len(warnings) > MAX_WARNING_ROWS:
        lines.append(f"| ... | | {len(warnings) - MAX_WARNING_ROWS} more in the build log |")
    lines.append("")
    return lines, {"warnings": len(warnings)}


def jobs_section(jobs: list[dict[str, object]]) -> list[str]:
    """Markdown lines with the verdict of every job of the run."""
    rows = [j for j in jobs if j.get("name") and "report" not in str(j["name"]).lower()]
    if not rows:
        return []
    icons = {"success": "✅", "failure": "❌", "cancelled": "🚫", "skipped": "⏭️", None: "⏳"}
    lines = ["### 🧱 Jobs", "", "| job | result | failed step |", "| --- | --- | --- |"]
    for j in rows:
        conclusion = j.get("conclusion")
        steps = ", ".join(str(s) for s in (j.get("steps") or []))
        lines.append(
            f"| {cell(j['name'], 80)} | {icons.get(conclusion, '❔')} "
            f"{conclusion or 'in progress'} | {cell(steps, 120)} |"
        )
    lines.append("")
    return lines


def compose(
    suites: list[Suite],
    files: list[FileCoverage],
    warnings: list[Warning],
    jobs: list[dict[str, object]],
    baseline: dict[str, object],
    run_url: str,
) -> tuple[str, dict[str, object]]:
    """The full report and the metrics dictionary the next run compares against."""
    test_lines, test_metrics = tests_section(suites)
    cov_lines, cov_metrics = coverage_section(files, baseline)
    warn_lines, warn_metrics = warnings_section(warnings)
    failed_jobs = [
        j
        for j in jobs
        if j.get("conclusion") == "failure" and "report" not in str(j.get("name", "")).lower()
    ]
    tests_bad = int(test_metrics.get("tests_failed", 0) or 0)
    verdict = "❌ **red**" if tests_bad or failed_jobs else "✅ **green**"
    reasons: list[str] = []
    if tests_bad:
        reasons.append(f"{tests_bad} failing test(s)")
    if failed_jobs:
        reasons.append("failed: " + ", ".join(f"`{j['name']}`" for j in failed_jobs))
    if not suites and not files:
        reasons.append("no test or coverage results were produced")
    headline = f"{verdict}" + (" - " + "; ".join(reasons) if reasons else "")
    lines = [MARKER, "## 🧪 CI report", "", headline, ""]
    lines += test_lines + cov_lines + warn_lines + jobs_section(jobs)
    lines += [
        f"→ [run Summary]({run_url}) (this report in full, artifacts `coverage-html`, "
        "`test-results` and `ci-report-inputs` at the bottom)",
    ]
    metrics = {**test_metrics, **cov_metrics, **warn_metrics}
    return "\n".join(lines), metrics


def trim(body: str, limit: int = COMMENT_LIMIT) -> str:
    """Cut whole lines from the end so the comment fits, keeping the footer."""
    if len(body.encode()) <= limit:
        return body
    lines = body.split("\n")
    footer = lines[-1]
    note = "_... report truncated to fit GitHub's comment limit; the run Summary has everything._"
    budget = limit - len(f"\n\n{note}\n{footer}".encode()) - 64
    kept: list[str] = []
    used = 0
    for line in lines[:-1]:
        size = len(line.encode()) + 1
        if used + size > budget:
            break
        kept.append(line)
        used += size
    return "\n".join([*kept, "", note, footer])


# ----------------------------------------------------------------------------
# GitHub
# ----------------------------------------------------------------------------


def _request(token: str, url: str, method: str = "GET", data: object = None) -> object:
    # urlopen honours file:// and custom schemes; every URL here is built from
    # the constant https base above, and the check keeps it that way.
    if not url.startswith("https://"):
        raise ValueError(f"refusing a non-https endpoint: {url}")
    request = urllib.request.Request(
        url,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "perfect_ros2_atomic_package-ci-report",
        },
    )
    if data is not None:
        request.data = json.dumps(data).encode()
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
        payload = response.read()
    return json.loads(payload) if payload else None


def _graphql(token: str, query: str, variables: dict[str, object]) -> dict[str, object]:
    result = _request(token, f"{API}/graphql", "POST", {"query": query, "variables": variables})
    return result if isinstance(result, dict) else {}


def post_comment(body: str, repo: str, pr: str, head_sha: str, token: str) -> None:
    """Fold the previous report comments as outdated and post a fresh one."""
    current = _request(token, f"{API}/repos/{repo}/pulls/{pr}")
    live_sha = (
        str((current or {}).get("head", {}).get("sha", "")) if isinstance(current, dict) else ""
    )
    if head_sha and live_sha and head_sha != live_sha:
        print(
            f"::notice::skipping the comment: run is for {head_sha[:7]}, "
            f"PR head moved to {live_sha[:7]}"
        )
        return
    stale: list[str] = []
    page = 1
    while True:
        comments = _request(
            token, f"{API}/repos/{repo}/issues/{pr}/comments?per_page=100&page={page}"
        )
        if not isinstance(comments, list):
            break
        # Only fold comments the Actions bot itself wrote - the marker is public
        # and a participant may quote it.
        stale += [
            str(c["node_id"])
            for c in comments
            if MARKER in (c.get("body") or "")
            and (c.get("user") or {}).get("login") == "github-actions[bot]"
        ]
        if len(comments) < 100:
            break
        page += 1
    folded = 0
    for node_id in stale:
        try:
            result = _graphql(
                token,
                "mutation($id:ID!){minimizeComment(input:{subjectId:$id,classifier:OUTDATED})"
                "{minimizedComment{isMinimized}}}",
                {"id": node_id},
            )
            data = result.get("data") or {}
            if isinstance(data, dict) and (data.get("minimizeComment") or {}).get(
                "minimizedComment", {}
            ).get("isMinimized"):
                folded += 1
        except (urllib.error.URLError, ValueError, KeyError) as error:
            print(f"::warning::could not fold an earlier report ({error})")
    _request(token, f"{API}/repos/{repo}/issues/{pr}/comments", "POST", {"body": body})
    print(f"posted the report (folded {folded}/{len(stale)} earlier one(s))")


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------


def _load_json(path: str | None) -> object:
    if not path:
        return None
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--junit", default="build", help="directory searched recursively for JUnit XML"
    )
    parser.add_argument("--lcov", default="coverage.info", help="lcov tracefile")
    parser.add_argument(
        "--build-log", default="build.log", help="compiler output of the coverage build"
    )
    parser.add_argument("--jobs", help="JSON list of {name, conclusion, steps} for the run")
    parser.add_argument(
        "--baseline", help="metrics JSON of the last successful run on the default branch"
    )
    parser.add_argument(
        "--workspace", default=os.environ.get("GITHUB_WORKSPACE", ""), help="path prefix to strip"
    )
    parser.add_argument("--metrics-out", help="where to write this run's metrics JSON")
    parser.add_argument("--summary", help="file the report is appended to (the run Summary)")
    parser.add_argument("--comment-out", help="write the trimmed comment body here")
    parser.add_argument(
        "--post",
        action="store_true",
        help="post the comment (GH_TOKEN, GITHUB_REPOSITORY, PR_NUMBER)",
    )
    args = parser.parse_args(argv)

    suites = load_suites(args.junit)
    files = load_lcov(args.lcov, args.workspace)
    warnings = load_warnings(args.build_log, args.workspace)
    jobs = _load_json(args.jobs)
    baseline = _load_json(args.baseline)
    run_url = os.environ.get("RUN_URL", "")
    body, metrics = compose(
        suites,
        files,
        warnings,
        jobs if isinstance(jobs, list) else [],
        baseline if isinstance(baseline, dict) else {},
        run_url,
    )

    if args.metrics_out:
        out = pathlib.Path(args.metrics_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as handle:
            handle.write(body.replace(MARKER, "").lstrip() + "\n")
    else:
        print(body)
    comment = trim(body)
    if args.comment_out:
        pathlib.Path(args.comment_out).write_text(comment + "\n", encoding="utf-8")
    if args.post:
        token = os.environ.get("GH_TOKEN", "")
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        pr = os.environ.get("PR_NUMBER", "")
        if not pr:
            print(
                "::notice::no pull request for this commit - the report is in the run Summary only"
            )
            return 0
        try:
            post_comment(comment, repo, pr, os.environ.get("HEAD_SHA", ""), token)
        except (urllib.error.URLError, ValueError, KeyError) as error:
            # A Dependabot or fork run holds a read-only token: the Summary
            # still has the report, only the comment is missing.
            print(f"::warning::could not post the report comment ({error}) - see the run Summary")
    return 0


if __name__ == "__main__":
    sys.exit(main())
