"""Walk wiki/behavioral/** and assert no anonymization leaks. Exit non-zero on violation."""
from __future__ import annotations

import sys
from pathlib import Path

import frontmatter

from intelligence.api.services.anonymization_lint import scan
from intelligence.api.services.wiki_paths import WIKI_ROOT


def _body_of(path: Path) -> str:
    """Return just the body (post-frontmatter) of a markdown file."""
    try:
        post = frontmatter.load(path)
        return post.content
    except Exception:
        # If parsing fails, fall back to full text
        return path.read_text(encoding="utf-8")


def main() -> int:
    failures = 0
    behavioral_root = WIKI_ROOT / "behavioral"
    for path in sorted(behavioral_root.rglob("*.md")):
        body = _body_of(path)
        violations = scan(body)
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
