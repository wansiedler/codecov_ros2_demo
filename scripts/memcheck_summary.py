#!/usr/bin/env python3
"""Print a readable summary of valgrind memcheck XML reports.

valgrind --xml=yes silences its own text output, so without this a memcheck run
shows only the gtest output and every finding stays inside the report file.

Usage: scripts/memcheck_summary.py [directory]
"""

import pathlib
import sys
# The reports are written by the valgrind run this script just performed, not
# fetched from anywhere, so the stdlib parser is not exposed to hostile XML.
import xml.etree.ElementTree as ElementTree  # nosec B405


def describe(error: ElementTree.Element) -> str:
    """One line for a single finding: what happened and where."""
    kind = error.findtext("kind", "?")
    what = error.findtext("what") or error.findtext("xwhat/text") or ""
    frame = error.find("stack/frame")
    where = ""
    if frame is not None:
        function = frame.findtext("fn", "?")
        source = frame.findtext("file", "?")
        line = frame.findtext("line", "?")
        where = f" at {function} ({source}:{line})"
    return f"  {kind}: {what}{where}"


def main() -> int:
    directory = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "memcheck")
    reports = sorted(directory.glob("*.xml"))
    if not reports:
        print(f"no memcheck reports in {directory}")
        return 0

    total = 0
    for report in reports:
        # nosemgrep: python.lang.security.use-defused-xml-parse.use-defused-xml-parse
        errors = ElementTree.parse(report).getroot().findall("error")  # nosec B314
        total += len(errors)
        name = report.stem
        if not errors:
            print(f"{name}: clean")
            continue
        print(f"{name}: {len(errors)} error(s)")
        for error in errors:
            print(describe(error))

    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
