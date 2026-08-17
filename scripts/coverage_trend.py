#!/usr/bin/env python3
"""Render a coverage trend chart from the Codecov commit history.

Codecov's own trend chart reads an aggregated timeseries that is only
backfilled some time after a repository is activated. The per-commit coverage
is available immediately through the v2 API, so this renders the same story
from it and writes a self-contained SVG.

Usage: scripts/coverage_trend.py [--repo owner/name] [--branch main] [-o PATH]
"""
import argparse
import json
import urllib.request

API = "https://api.codecov.io/api/v2/github/{owner}/repos/{repo}/commits"

W, H = 900, 360
PAD_L, PAD_R, PAD_T, PAD_B = 60, 30, 30, 70


def fetch(owner: str, repo: str, branch: str, limit: int):
    url = f"{API.format(owner=owner, repo=repo)}?branch={branch}&page_size=100"
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.load(response)
    points = [
        (c["commitid"][:7], (c.get("message") or "").splitlines()[0], c["totals"]["coverage"])
        for c in payload.get("results", [])
        if c.get("totals") and c["totals"].get("coverage") is not None
    ]
    points.reverse()  # oldest first
    return points[-limit:]


def render(points, out_path: str) -> None:
    if len(points) < 2:
        raise SystemExit("need at least two commits with coverage")

    lo = min(p[2] for p in points)
    hi = max(p[2] for p in points)
    span = max(hi - lo, 1.0)
    lo, hi = max(0.0, lo - span * 0.1), min(100.0, hi + span * 0.1)

    def x(i):
        return PAD_L + i * (W - PAD_L - PAD_R) / (len(points) - 1)

    def y(value):
        return H - PAD_B - (value - lo) * (H - PAD_T - PAD_B) / (hi - lo)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        'font-family="ui-sans-serif, system-ui, sans-serif">',
        '<style>'
        ':root{color-scheme:light dark}'
        '.bg{fill:#ffffff}.axis{stroke:#d0d7de}.grid{stroke:#eaeef2}'
        '.lbl{fill:#57606a;font-size:11px}.val{fill:#1f2328;font-size:11px}'
        '.line{fill:none;stroke:#2da44e;stroke-width:2.5}'
        '@media (prefers-color-scheme: dark){'
        '.bg{fill:#0d1117}.axis{stroke:#30363d}.grid{stroke:#21262d}'
        '.lbl{fill:#8b949e}.val{fill:#e6edf3}}'
        '</style>',
        f'<rect class="bg" width="{W}" height="{H}"/>',
    ]

    for step in range(5):
        value = lo + (hi - lo) * step / 4
        yy = y(value)
        parts.append(f'<line class="grid" x1="{PAD_L}" y1="{yy:.1f}" x2="{W - PAD_R}" y2="{yy:.1f}"/>')
        parts.append(f'<text class="lbl" x="{PAD_L - 8}" y="{yy + 4:.1f}" text-anchor="end">{value:.0f}%</text>')

    path = " ".join(
        f"{'M' if i == 0 else 'L'}{x(i):.1f},{y(p[2]):.1f}" for i, p in enumerate(points)
    )
    parts.append(f'<path class="line" d="{path}"/>')

    for i, (sha, _subject, value) in enumerate(points):
        cx, cy = x(i), y(value)
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="#2da44e"/>')
        parts.append(f'<text class="val" x="{cx:.1f}" y="{cy - 10:.1f}" text-anchor="middle">{value:.1f}</text>')
        parts.append(
            f'<text class="lbl" x="{cx:.1f}" y="{H - PAD_B + 18:.1f}" text-anchor="end" '
            f'transform="rotate(-40 {cx:.1f} {H - PAD_B + 18:.1f})">{sha}</text>'
        )

    parts.append(f'<line class="axis" x1="{PAD_L}" y1="{H - PAD_B}" x2="{W - PAD_R}" y2="{H - PAD_B}"/>')
    parts.append(f'<line class="axis" x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{H - PAD_B}"/>')
    parts.append('</svg>')

    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(parts) + "\n")
    print(f"{out_path}: {len(points)} commits, {points[0][2]:.2f}% -> {points[-1][2]:.2f}%")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="wansiedler/codecov_ros2_demo")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("-o", "--output", default="docs/coverage-trend.svg")
    args = parser.parse_args()
    owner, repo = args.repo.split("/", 1)
    render(fetch(owner, repo, args.branch, args.limit), args.output)


if __name__ == "__main__":
    main()
