#!/usr/bin/env python3
"""Regenerate the hash-pinned requirement files used by the workflows.

OpenSSF Scorecard's pinned-dependencies check wants pip installs pinned by
hash, not only by version. pip's --require-hashes needs every transitive
dependency pinned too, so this resolves each tool and writes one file per tool.

Every wheel hash of a release is listed rather than the one that happens to
match this machine: the CI containers run a different platform and Python
version, and pip accepts any of the listed hashes for the file it picks.

Usage: scripts/lock_requirements.py
"""
import json
import pathlib
import subprocess
import sys
import urllib.request

TOOLS = {
    "commitizen": "commitizen==4.1.0",
    "clang-format": "clang-format==22.1.8",
    "gprof2dot": "gprof2dot==2025.4.14",
}

OUTPUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "requirements"


def resolve(spec: str) -> list[tuple[str, str]]:
    """Returns the full dependency closure of `spec` as (name, version) pairs."""
    report = pathlib.Path(f"/tmp/pip-report-{spec.split('==')[0]}.json")
    subprocess.run(
        ["python3", "-m", "pip", "install", "--dry-run", "--ignore-installed",
         "--quiet", "--only-binary", ":all:", "--report", str(report), spec],
        check=True,
    )
    data = json.loads(report.read_text())
    return sorted((i["metadata"]["name"], i["metadata"]["version"]) for i in data["install"])


def wheel_hashes(name: str, version: str) -> list[str]:
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    with urllib.request.urlopen(url, timeout=30) as response:
        files = json.load(response)["urls"]
    return sorted({f["digests"]["sha256"] for f in files if f["packagetype"] == "bdist_wheel"})


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    for tool, spec in TOOLS.items():
        packages = resolve(spec)
        lines = [
            "# Generated with scripts/lock_requirements.py - pip --require-hashes",
            f"# Tool: {spec}",
            "",
        ]
        for name, version in packages:
            hashes = wheel_hashes(name, version)
            if not hashes:
                sys.exit(f"no wheels published for {name} {version}")
            lines.append(
                f"{name}=={version} \\\n"
                + " \\\n".join(f"    --hash=sha256:{h}" for h in hashes)
            )
        path = OUTPUT_DIR / f"{tool}.txt"
        path.write_text("\n".join(lines) + "\n")
        print(f"{path.name}: {len(packages)} packages")


if __name__ == "__main__":
    main()
