#!/usr/bin/env python3
"""Post one sticky CI report on the pull request of a run.

Reads the ci-metrics JSON files the jobs of this run produced, the same files
from the last successful run on the default branch for the delta, and the job
list of the run for what failed. The report always goes to the run Summary;
on a pull request it is also posted as a comment.

Older reports are not edited in place: they are minimized as OUTDATED (still
expandable, so the history survives) and a fresh comment is posted, which
keeps the current verdict at the bottom of the conversation instead of buried
where the first run happened to put it. A run whose commit is no longer the
head of the pull request leaves the comments alone - a slow older run must
not overwrite a newer verdict.

Only comments the Actions bot wrote are ever folded: the marker is public,
and a participant quoting it must keep their comment.

Environment: GH_TOKEN, GITHUB_REPOSITORY, GITHUB_STEP_SUMMARY, RUN_URL;
PR_NUMBER and HEAD_SHA are optional (no PR: Summary only).

Usage: scripts/ci_report.py [--current ci-metrics] [--base ci-metrics-base]
                            [--jobs jobs.json]
"""

import argparse
import json
import os
import pathlib
import sys
import urllib.request

API = "https://api.github.com"
MARKER = "<!-- ci-report -->"
BOT = "github-actions[bot]"
COMMENT_LIMIT = 65536  # GitHub rejects a longer comment body


def load_dir(directory: pathlib.Path) -> dict:
    merged: dict = {}
    for path in sorted(directory.glob("**/*.json")):
        try:
            merged.update(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as error:
            print(f"::warning::skipping {path}: {error}")
    return merged


def delta(current: dict, base: dict, key: str, label: str) -> str | None:
    now = current.get(key)
    if now is None:
        return None
    text = f"{label} {now}%"
    before = base.get(key)
    if before is None:
        return text
    diff = round(now - before, 1)
    if not diff:
        return f"{text} (=)"
    arrow = "▲" if diff > 0 else "▼"
    return f"{text} ({before}% → {now}%, {arrow}{abs(diff)})"


def compose(current: dict, base: dict, jobs: list[dict], run_url: str) -> list[str]:
    lines = [MARKER, "## 🧪 CI report", ""]
    if current.get("tests"):
        classes = [
            f"{k} {current[f'tests_{k}']}"
            for k in ("unit", "regression", "integration")
            if current.get(f"tests_{k}")
        ]
        icon = "❌" if current.get("tests_failed") else "✅"
        text = f"**Tests:** {icon} {current['tests']}"
        if classes:
            text += " (" + " · ".join(classes) + ")"
        lines.append(text)
    coverage = [
        part
        for part in (
            delta(current, base, "lines", "lines"),
            delta(current, base, "functions", "functions"),
            delta(current, base, "branches", "branches"),
        )
        if part
    ]
    if coverage:
        lines.append("**Coverage:** " + " · ".join(coverage))
    failed = [j for j in jobs if j.get("conclusion") == "failure"]
    if failed:
        rows = []
        for job in failed:
            steps = ", ".join(job.get("steps") or []) or "job failed"
            rows.append(f"❌ `{job['name']}` — {steps}")
        lines.append("**Failed:** " + " · ".join(rows))
        if "lines" not in current and not current.get("tests"):
            lines.append("_The run failed before any metric was collected - see the job logs._")
    if len(lines) == 3:
        lines.append("_No metrics in this run._")
    lines += ["", f"→ full report: [run Summary]({run_url})"]
    return lines


def request(token: str, url: str, method: str = "GET", data: dict | None = None):
    if not url.startswith("https://"):
        sys.exit(f"refusing a non-https endpoint: {url}")
    req = urllib.request.Request(
        url,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "ci-report",
        },
    )
    if data is not None:
        req.data = json.dumps(data).encode()
    with urllib.request.urlopen(req, timeout=30) as response:  # nosec B310 - https only
        return json.load(response) if response.length != 0 else None


def graphql(token: str, query: str, variables: dict) -> dict:
    return request(token, f"{API}/graphql", "POST", {"query": query, "variables": variables})


def fold_previous(token: str, repo: str, pr: str) -> tuple[int, int]:
    """Minimize every earlier report on the pull request; returns (folded, candidates)."""
    stale: list[str] = []
    page = 1
    while True:
        comments = request(
            token, f"{API}/repos/{repo}/issues/{pr}/comments?per_page=100&page={page}"
        )
        stale += [
            c["node_id"]
            for c in comments
            if MARKER in (c.get("body") or "") and (c.get("user") or {}).get("login") == BOT
        ]
        if len(comments) < 100:
            break
        page += 1
    if not stale:
        return 0, 0
    # Skip what earlier runs already folded: re-minimizing the whole history
    # on every run grows with the age of the pull request for nothing.
    try:
        state: dict[str, bool] = {}
        query = "query($ids:[ID!]!){nodes(ids:$ids){... on IssueComment{id isMinimized}}}"
        for start in range(0, len(stale), 100):
            reply = graphql(token, query, {"ids": stale[start : start + 100]})
            for node in (reply.get("data") or {}).get("nodes") or []:
                if node:
                    state[node["id"]] = node.get("isMinimized", False)
        stale = [node_id for node_id in stale if not state.get(node_id, False)]
    except Exception as error:
        print(f"::warning::minimized-state lookup failed ({error}) - folding every candidate")
    folded = 0
    mutation = (
        "mutation($id:ID!){minimizeComment(input:{subjectId:$id,classifier:OUTDATED})"
        "{minimizedComment{isMinimized}}}"
    )
    for node_id in stale:
        try:
            reply = graphql(token, mutation, {"id": node_id})
            done = not reply.get("errors") and (reply.get("data") or {}).get(
                "minimizeComment", {}
            ).get("minimizedComment", {}).get("isMinimized")
        except Exception as error:
            print(f"::warning::could not minimize an old report {node_id}: {error}")
            continue
        if done:
            folded += 1
        else:
            print(f"::warning::could not minimize an old report {node_id}: {reply.get('errors')}")
    return folded, len(stale)


def truncate(lines: list[str]) -> str:
    body = "\n".join(lines)
    if len(body.encode()) <= COMMENT_LIMIT:
        return body
    footer = ["", "_…report truncated to fit GitHub's comment limit._", lines[-1]]
    used = len("\n".join(footer).encode()) + 64
    kept: list[str] = []
    for line in lines[:-1]:
        size = len(line.encode()) + 1
        if used + size > COMMENT_LIMIT:
            break
        kept.append(line)
        used += size
    return "\n".join([*kept, *footer])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--current", type=pathlib.Path, default=pathlib.Path("ci-metrics"))
    parser.add_argument("--base", type=pathlib.Path, default=pathlib.Path("ci-metrics-base"))
    parser.add_argument("--jobs", type=pathlib.Path, default=pathlib.Path("jobs.json"))
    args = parser.parse_args()

    current = load_dir(args.current)
    base = load_dir(args.base)
    try:
        jobs = json.loads(args.jobs.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        jobs = []
    jobs = [j for j in jobs if "report" not in (j.get("name") or "")]
    lines = compose(current, base, jobs, os.environ["RUN_URL"])

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines).replace(MARKER, "").lstrip() + "\n")

    pr = os.environ.get("PR_NUMBER", "")
    if not pr:
        print("::notice::no pull request for this commit - report written to the run Summary only")
        return 0
    token = os.environ["GH_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    try:
        head = os.environ.get("HEAD_SHA", "")
        pull = request(token, f"{API}/repos/{repo}/pulls/{pr}")
        latest = (pull.get("head") or {}).get("sha", "")
        if head and latest and head != latest:
            print(f"::notice::run is for {head[:7]} but the PR head is {latest[:7]} - not posting")
            return 0
        folded, candidates = fold_previous(token, repo, pr)
        request(
            token, f"{API}/repos/{repo}/issues/{pr}/comments", "POST", {"body": truncate(lines)}
        )
        print(f"posted the report (minimized {folded}/{candidates} earlier one(s))")
    except Exception as error:
        print(
            f"::warning::could not post the CI report ({error}) - is pull-requests: write granted?"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
