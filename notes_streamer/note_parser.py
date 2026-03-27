from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParsedNote:
    name: str
    behavior_label: str
    body: str
    source_path: Path
    raw_text: str


class NoteParseError(ValueError):
    """Raised when a note file does not match the canonical format."""


def _behavior_label_from_filename(path: Path) -> str:
    stem = path.stem
    if stem.startswith("neutral_"):
        return "Neutral"
    if stem.startswith("problematic_"):
        return "Problematic"
    raise NoteParseError(f"Unable to infer behavior label from filename: {path.name}")


def _name_from_first_line(raw_text: str, path: Path) -> str:
    first_line, _, _ = raw_text.partition("\n")
    if first_line.startswith("Name: "):
        return first_line.split(": ", 1)[1].strip()
    raise NoteParseError(f"Missing Name header in note file: {path.name}")


def _body_from_raw_text(raw_text: str, path: Path) -> str:
    _, separator, remainder = raw_text.partition("\n\n")
    if not separator:
        raise NoteParseError(f"Missing blank line separator in note file: {path.name}")
    body = remainder.strip()
    if not body:
        raise NoteParseError(f"Missing body text in note file: {path.name}")
    return body


def parse_note_file(path: Path) -> ParsedNote:
    raw_text = path.read_text(encoding="utf-8").strip()
    if not raw_text:
        raise NoteParseError(f"Empty note file: {path}")

    name = _name_from_first_line(raw_text, path)
    body = _body_from_raw_text(raw_text, path)

    return ParsedNote(
        name=name,
        behavior_label=_behavior_label_from_filename(path),
        body=body,
        source_path=path,
        raw_text=raw_text,
    )
