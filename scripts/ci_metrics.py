#!/usr/bin/env python3
"""Collect what a CI run measured into one small JSON file.

Every job that produces a number worth comparing - coverage, test counts -
writes it here, the ci-metrics artifact carries it, and scripts/ci_report.py
turns the artifacts of a run into the PR comment. Reading the lcov tracefile
and the JUnit XML directly, instead of scraping tool output, keeps the numbers
the same ones Codecov and the test-results artifact see.

Tests are classified by the file colcon wrote them to: launch_testing results
(`*.xunit.xml`) are integration tests, a binary with "regression" in its name
is a regression test, everything else is a unit test. A `.ci-test-classes.yaml`
in the repository root (`binary: class`) overrides that per binary.

Usage: scripts/ci_metrics.py [--tracefile coverage.info] [--results build]
                             [--out ci-metrics/build.json] [--summary]
"""

import argparse
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET  # nosec B405 - files are written by our own test run

CLASSES = ("unit", "regression", "integration")


def coverage(tracefile: pathlib.Path) -> dict[str, float]:
    """Percentages over the whole tracefile, the way `lcov --summary` computes them."""
    totals = {"LF": 0, "LH": 0, "FNF": 0, "FNH": 0, "BRF": 0, "BRH": 0}
    if not tracefile.is_file():
        return {}
    for line in tracefile.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition(":")
        if key in totals and value.isdigit():
            totals[key] += int(value)

    def pct(hit: int, found: int) -> float | None:
        return round(100.0 * hit / found, 1) if found else None

    out = {
        "lines": pct(totals["LH"], totals["LF"]),
        "functions": pct(totals["FNH"], totals["FNF"]),
        "branches": pct(totals["BRH"], totals["BRF"]),
    }
    return {k: v for k, v in out.items() if v is not None}


def load_overrides(path: pathlib.Path) -> dict[str, str]:
    """`binary: class` pairs; PyYAML is optional because the file is."""
    if not path.is_file():
        return {}
    try:
        import yaml
    except ImportError:
        print(f"{path} present but PyYAML is not installed - ignoring it", file=sys.stderr)
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in data.items()}


def classify(report: pathlib.Path, overrides: dict[str, str]) -> str:
    name = re.sub(r"\.(gtest|xunit)\.xml$", "", report.name)
    name = re.sub(r"\.py$", "", name)
    cls = overrides.get(name)
    if cls is None:
        if report.name.endswith(".xunit.xml"):
            cls = "integration"
        elif "regression" in name:
            cls = "regression"
        else:
            cls = "unit"
    return cls if cls in CLASSES else "unit"


def tests(results: pathlib.Path, overrides: dict[str, str]) -> dict[str, object]:
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    counts = dict.fromkeys(CLASSES, 0)
    for report in sorted(results.glob("**/test_results/**/*.xml")):
        try:
            root = ET.parse(report).getroot()  # nosec B314 - see the import
        except ET.ParseError:
            continue
        suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
        if not suites:
            continue
        for suite in suites:
            for key in totals:
                totals[key] += int(suite.get(key) or 0)
            # gtest reports a disabled case separately from a skipped one.
            totals["skipped"] += int(suite.get("disabled") or 0)
        counts[classify(report, overrides)] += sum(int(s.get("tests") or 0) for s in suites)
    if not totals["tests"]:
        return {}
    out: dict[str, object] = {
        "tests": "{tests} tests, {failures} failures, {errors} errors, {skipped} skipped".format(
            **totals
        ),
        "tests_total": totals["tests"],
        "tests_failed": totals["failures"] + totals["errors"],
    }
    out.update({f"tests_{k}": v for k, v in counts.items() if v})
    return out


def summary(metrics: dict[str, object]) -> str:
    lines = ["## 🧪 Tests and coverage", ""]
    if "tests" in metrics:
        parts = [f"{k} {metrics[f'tests_{k}']}" for k in CLASSES if metrics.get(f"tests_{k}")]
        lines.append(
            f"**Tests:** {metrics['tests']}" + (f" ({' · '.join(parts)})" if parts else "")
        )
    cov = [f"{k} {metrics[k]}%" for k in ("lines", "functions", "branches") if k in metrics]
    if cov:
        lines.append("**Coverage:** " + " · ".join(cov))
    if len(lines) == 2:
        lines.append("_No test results and no coverage in this run._")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tracefile", type=pathlib.Path, default=pathlib.Path("coverage.info"))
    parser.add_argument("--results", type=pathlib.Path, default=pathlib.Path("build"))
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("ci-metrics/build.json"))
    parser.add_argument(
        "--summary", action="store_true", help="print a Markdown block for the job Summary"
    )
    args = parser.parse_args()

    metrics: dict[str, object] = {}
    metrics.update(coverage(args.tracefile))
    metrics.update(tests(args.results, load_overrides(pathlib.Path(".ci-test-classes.yaml"))))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        print(summary(metrics), end="")
    else:
        print(f"{args.out}: {json.dumps(metrics, sort_keys=True)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
