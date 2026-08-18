#!/usr/bin/env python3
"""Remove gcov's exception edges from an lcov tracefile.

GCC records, for every call that could throw, a branch for the path taken when
it does. Nothing in this workspace throws, so those edges are never taken and
cannot be taken by a test - they made up 47 of 145 branches here and held branch
coverage at 68 % while every branch the code actually chooses between was
covered.

Dropping them is not the same as hiding a gap: a real branch is a decision the
code makes, an exception edge is an unwind path the compiler emits. lcov has an
option for this, `no_exception_branch`, but on GCC 13 it discards every branch
record instead of only the exception ones, so the filtering happens here.

Usage: scripts/strip_exception_branches.py coverage.info
"""

import pathlib
import sys


def strip(text: str) -> str:
    out: list[str] = []
    found = hit = 0
    for line in text.splitlines():
        if line.startswith("BRDA:"):
            # BRDA:<line>,<block>,<branch>,<taken>; gcov names an exception
            # block "e" followed by the block number.
            _, block, _, taken = line[5:].split(",")
            if block.startswith("e"):
                continue
            found += 1
            hit += taken not in ("-", "0")
            out.append(line)
        elif line.startswith("BRF:"):
            out.append(f"BRF:{found}")
        elif line.startswith("BRH:"):
            out.append(f"BRH:{hit}")
        elif line == "end_of_record":
            out.append(line)
            found = hit = 0
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    path = pathlib.Path(sys.argv[1])
    before = path.read_text(encoding="utf-8")
    after = strip(before)
    path.write_text(after, encoding="utf-8")
    removed = before.count("\nBRDA:") - after.count("\nBRDA:")
    print(f"{path}: dropped {removed} exception edges")
    return 0


if __name__ == "__main__":
    sys.exit(main())
