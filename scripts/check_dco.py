#!/usr/bin/env python3
# Copyright 2026 Alexander Paul Wansiedler
# SPDX-License-Identifier: Apache-2.0
"""Every commit carries a Developer Certificate of Origin sign-off.

The sign-off is the `Signed-off-by: Name <email>` trailer `git commit -s`
adds; by adding it the author certifies https://developercertificate.org.
As a commit-msg hook this checks the message being written; in CI it checks
every commit of the pull request range.

Usage: scripts/check_dco.py MESSAGE_FILE        (pre-commit, commit-msg stage)
       scripts/check_dco.py --range BASE..HEAD  (CI)
"""

import pathlib
import re
import subprocess  # nosec B404 - fixed argv, no shell
import sys

TRAILER = re.compile(r"^Signed-off-by: .+ <.+@.+>$", re.MULTILINE)
HINT = "add the trailer with `git commit -s` (or `git commit --amend -s` for the last commit)"


def check_message(text: str) -> bool:
    return bool(TRAILER.search(text))


def check_range(rev_range: str) -> int:
    out = subprocess.run(  # nosec B603 B607 - fixed argv
        ["git", "log", "--format=%H%x00%s%x00%B%x1e", rev_range],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    bad = []
    for record in filter(None, out.split("\x1e")):
        sha, subject, body = record.lstrip("\n").split("\x00", 2)
        if not check_message(body):
            bad.append(f"  {sha[:7]} {subject}")
    if bad:
        print("commit(s) without a Signed-off-by trailer:")
        print("\n".join(bad))
        print(HINT)
        return 1
    print("every commit in the range is signed off")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "--range":
        return check_range(argv[1])
    if len(argv) == 1:
        if check_message(pathlib.Path(argv[0]).read_text(encoding="utf-8")):
            return 0
        print(f"commit message has no Signed-off-by trailer; {HINT}")
        return 1
    print(__doc__.strip().splitlines()[-2:], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
