#!/usr/bin/env python3
# Copyright 2026 Alexander Paul Wansiedler
# SPDX-License-Identifier: Apache-2.0
"""Every source file carries a copyright line and an SPDX license identifier.

The OpenSSF Best Practices gold criteria ask for both in each source file; a
hook is what keeps that true after the day it was made true. A file passes
when its first 20 lines contain a `Copyright` line and
`SPDX-License-Identifier: Apache-2.0`. Generated files, data and Markdown are
not source and are not checked.

Usage: scripts/check_spdx.py FILE...   (pre-commit passes the files)
"""

import pathlib
import sys

SPDX = "SPDX-License-Identifier: Apache-2.0"
HEAD_LINES = 20


def check(path: pathlib.Path) -> str | None:
    try:
        head = path.read_text(encoding="utf-8", errors="replace").splitlines()[:HEAD_LINES]
    except OSError as error:
        return str(error)
    text = "\n".join(head)
    missing = [
        what for what, needle in (("copyright", "Copyright"), ("SPDX", SPDX)) if needle not in text
    ]
    return f"missing {' and '.join(missing)} in the first {HEAD_LINES} lines" if missing else None


def main(argv: list[str]) -> int:
    failures = 0
    for name in argv:
        problem = check(pathlib.Path(name))
        if problem:
            print(f"{name}: {problem}")
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
