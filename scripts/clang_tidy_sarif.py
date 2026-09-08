#!/usr/bin/env python3
"""Turn a clang-tidy log into SARIF for the Security tab.

clang-tidy has no SARIF writer of its own, and the log it prints is enough:
one `file:line:col: warning: message [check]` line per finding. The Security
tab then shows the findings against the diff of a pull request, and closes an
alert when a later scan no longer reports it.

That last part is why an incomplete scan must never be published: a SARIF
without results reads as "everything fixed". So when the producer failed
(`--producer-rc` not 0) and the log holds no diagnostic at all - clang-tidy
crashed, or never found the compilation database - this exits 3 and writes
nothing, and the workflow skips the upload.

Usage: scripts/clang_tidy_sarif.py LOG SARIF [--producer-rc N] [--summary PATH]
"""

import argparse
import collections
import contextlib
import json
import os
import pathlib
import re
import sys

DIAGNOSTIC = re.compile(
    r"^(?P<file>[^:\s][^:]*):(?P<line>\d+):(?P<col>\d+): "
    r"(?P<sev>warning|error): (?P<msg>.*?)(?: \[(?P<rule>[^\]]+)\])?$"
)


def parse(log: str, root: pathlib.Path) -> list[dict]:
    results = []
    seen: set[tuple] = set()
    for line in log.splitlines():
        match = DIAGNOSTIC.match(line)
        if not match:
            continue
        path = pathlib.Path(match["file"])
        if path.is_absolute():
            with contextlib.suppress(ValueError):
                path = path.relative_to(root)
        key = (str(path), match["line"], match["col"], match["rule"], match["msg"])
        # run-clang-tidy repeats a header diagnostic once per translation unit
        # that includes it; one alert per location is what the Security tab wants.
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "ruleId": match["rule"] or "clang-tidy",
                "level": "error" if match["sev"] == "error" else "warning",
                "message": {"text": match["msg"]},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": path.as_posix()},
                            "region": {
                                "startLine": int(match["line"]),
                                "startColumn": int(match["col"]),
                            },
                        }
                    }
                ],
            }
        )
    return results


def summary(results: list[dict], producer_rc: int) -> str:
    if not results:
        return "## ✅ clang-tidy: clean\n"
    verdict = "❌" if producer_rc else "⚠️"
    lines = [
        f"## {verdict} clang-tidy: {len(results)} finding(s)",
        "",
        "| check | count |",
        "| --- | --- |",
    ]
    by_rule = collections.Counter(r["ruleId"] for r in results)
    lines += [f"| `{rule}` | {count} |" for rule, count in by_rule.most_common()]
    lines += ["", "_Every finding with its location: Security → Code scanning, tool clang-tidy._"]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("log", type=pathlib.Path)
    parser.add_argument("sarif", type=pathlib.Path)
    parser.add_argument("--producer-rc", type=int, default=0, help="exit status of clang-tidy")
    parser.add_argument("--summary", type=pathlib.Path, help="append a Markdown block to this file")
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path(os.environ.get("GITHUB_WORKSPACE") or pathlib.Path.cwd()),
        help="paths in the log are made relative to this directory",
    )
    args = parser.parse_args()

    if not args.log.is_file():
        print(f"{args.log} is missing - clang-tidy never ran; nothing to publish", file=sys.stderr)
        return 3
    results = parse(args.log.read_text(encoding="utf-8", errors="replace"), args.root)
    if args.producer_rc and not results:
        print(
            f"clang-tidy exited {args.producer_rc} without a single diagnostic - "
            "it did not run to completion; refusing to publish an empty SARIF",
            file=sys.stderr,
        )
        return 3
    sarif = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "clang-tidy",
                        "informationUri": "https://clang.llvm.org/extra/clang-tidy/",
                    }
                },
                "results": results,
            }
        ],
    }
    args.sarif.write_text(json.dumps(sarif, indent=2) + "\n", encoding="utf-8")
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as handle:
            handle.write(summary(results, args.producer_rc))
    print(f"{len(results)} finding(s) -> {args.sarif}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
