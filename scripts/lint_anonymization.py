"""Walk wiki/behavioral/** and assert no anonymization leaks. Exit non-zero on violation."""
from __future__ import annotations

import sys
from pathlib import Path

from intelligence.api.services.anonymization_lint import scan
from intelligence.api.services.wiki_paths import WIKI_ROOT


def main() -> int:
    failures = 0
    behavioral_root = WIKI_ROOT / "behavioral"
    for path in sorted(behavioral_root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        violations = scan(text)
        if violations:
            failures += 1
            print(f"[LEAK] {path.relative_to(WIKI_ROOT)}")
            for v in violations:
                print(f"   - {v.kind}: '{v.match}' (...{v.snippet}...)")
    if failures:
        print(f"\nFAILED — {failures} files leaked.")
        return 1
    print("OK — no anonymization leaks under wiki/behavioral/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
