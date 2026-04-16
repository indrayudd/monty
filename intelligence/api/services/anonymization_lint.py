"""Anonymization lint for wiki/behavioral/** writes.

Scans content for known student names, educator names, dates, and ages
that would identify a specific child. Used by wiki_writer before any
write under wiki/behavioral/.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

# Keep in sync with the persona set. Updated when personas are added/removed.
KNOWN_STUDENT_NAMES = {
    "Arjun Nair",
    "Diya Malhotra",
    "Kiaan Gupta",
    "Mira Shah",
    "Saanvi Verma",
}

# Educators referenced in observation notes. Update if persona engine adds more.
KNOWN_EDUCATOR_NAMES = {
    "Amrita Maitra",
    "Sajitha Kandathil",
    "Yogitha M",
    "Hima Brijeshkumar Savaj",
    "Nandini Rao",
    "Meera Iyer",
    "Pooja Menon",
    "Anjali Deshmukh",
}

DATE_REGEX = re.compile(
    r"\b(20\d{2}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b"
)
TIME_REGEX = re.compile(r"\b\d{1,2}:\d{2}\b")


@dataclass
class LintViolation:
    kind: str        # "student_name" | "educator_name" | "date" | "time"
    match: str
    snippet: str


def scan(content: str) -> list[LintViolation]:
    """Return a list of violations. Empty list = clean."""
    violations: list[LintViolation] = []

    for name in KNOWN_STUDENT_NAMES:
        if name in content:
            violations.append(LintViolation("student_name", name, _snippet(content, name)))
        # Also catch first names alone (Mira, Arjun, ...)
        first = name.split()[0]
        if re.search(rf"\b{re.escape(first)}\b", content):
            violations.append(LintViolation("student_name", first, _snippet(content, first)))

    for name in KNOWN_EDUCATOR_NAMES:
        if name in content:
            violations.append(LintViolation("educator_name", name, _snippet(content, name)))

    for m in DATE_REGEX.finditer(content):
        violations.append(LintViolation("date", m.group(0), _snippet(content, m.group(0))))

    for m in TIME_REGEX.finditer(content):
        violations.append(LintViolation("time", m.group(0), _snippet(content, m.group(0))))

    return violations


def _snippet(content: str, match: str) -> str:
    idx = content.find(match)
    if idx < 0:
        return ""
    start = max(0, idx - 30)
    end = min(len(content), idx + len(match) + 30)
    return content[start:end].replace("\n", " ")


def assert_clean(content: str, *, file_path: Path) -> None:
    """Raise AnonymizationLeak if any violations found."""
    violations = scan(content)
    if violations:
        raise AnonymizationLeak(file_path, violations)


class AnonymizationLeak(Exception):
    def __init__(self, file_path: Path, violations: list[LintViolation]):
        self.file_path = file_path
        self.violations = violations
        msg_lines = [f"Anonymization leak in {file_path}:"]
        for v in violations:
            msg_lines.append(f"  - {v.kind}: '{v.match}'  (...{v.snippet}...)")
        super().__init__("\n".join(msg_lines))
