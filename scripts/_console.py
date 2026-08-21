"""Console helpers shared by the scripts in this directory.

Canon prose carries characters a Windows console codepage (cp1252) cannot
encode: ``→`` U+2192, the non-breaking hyphen ``‑`` U+2011, box-drawing, and
en/em dashes. Any script that writes that content to stdout dies with
``UnicodeEncodeError`` on Windows while passing in CI, where GitHub runners are
Linux/UTF-8.

The failure mode is worse than a crash, which is why this helper exists rather
than a note in a README. ``print`` / ``sys.stdout.write`` raises **partway
through emitting** — everything before the offending character has already been
flushed. A script listing findings therefore prints a truncated list and then
dies, and if the caller pipes into ``grep`` or ``wc`` the traceback goes to
stderr and is easy to miss. The run reads as *"there were fewer results"*
rather than as *"this crashed"*. That is a measure-the-blast-radius bug: it
under-reports exactly when there is most to report.

See issue #1433.
"""

from __future__ import annotations

import sys


def use_utf8_stdout() -> None:
    """Make stdout UTF-8 and non-fatal, so output can never truncate mid-emit.

    ``errors="replace"`` is the load-bearing half: even if a character still
    slips through, the process degrades one glyph cosmetically instead of
    dying with a partial write. Call once at the top of ``main()``.

    A no-op where the stream does not support reconfiguration (a plain pipe
    substituted in tests, for instance).
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
