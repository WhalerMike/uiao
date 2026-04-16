"""
Byte-safe patch: narrow drift-scan.yml scope from full repo to canon/.

Changes `--path . \` to `--path canon/ \` in both step blocks of
.github/workflows/drift-scan.yml without touching line endings (CRLF preserved).

Expected: exactly 2 replacements.

Usage:
    python patch_drift_scan_scope.py
"""

from pathlib import Path
import sys

TARGET = Path(r"C:\Users\whale\uiao-core\.github\workflows\drift-scan.yml")
OLD = b"--path . \\"
NEW = b"--path canon/ \\"
EXPECTED = 2


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found", file=sys.stderr)
        return 2

    original = TARGET.read_bytes()
    found = original.count(OLD)
    if found != EXPECTED:
        print(
            f"ERROR: expected {EXPECTED} occurrences of {OLD!r}, found {found}",
            file=sys.stderr,
        )
        return 3

    patched = original.replace(OLD, NEW)
    after = patched.count(NEW)
    if after < EXPECTED:
        print(
            f"ERROR: after replace, {NEW!r} count = {after} (expected >= {EXPECTED})",
            file=sys.stderr,
        )
        return 4

    TARGET.write_bytes(patched)
    print(f"patched: {TARGET}")
    print(f"  bytes: {len(original)} -> {len(patched)}")
    print(f"  replacements: {found}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
