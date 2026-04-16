"""Path conventions and slugification for the wiki/ directory.

All wiki/-relative path construction goes through this module. No other
service should hand-build wiki paths — that's how the anonymization wall
gets bypassed by accident.
"""
from __future__ import annotations

from pathlib import Path
import re

WIKI_ROOT = Path(__file__).resolve().parents[3] / "wiki"

BEHAVIORAL_TYPES = (
    "setting_events",
    "antecedents",
    "behaviors",
    "functions",
    "brain_states",
    "responses",
    "protective_factors",
)


def slugify(text: str) -> str:
    """Return a lowercase, kebab-case slug. Stable across runs."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def behavioral_node_path(node_type: str, slug: str) -> Path:
    """Path to a behavioral node markdown file."""
    if node_type not in BEHAVIORAL_TYPES:
        raise ValueError(f"unknown behavioral type: {node_type}")
    return WIKI_ROOT / "behavioral" / node_type / f"{slug}.md"


def behavioral_edge_path(
    src_type: str, src_slug: str, rel: str, dst_type: str, dst_slug: str
) -> Path:
    """Path to a behavioral edge markdown file."""
    name = f"{src_type}--{src_slug}--{rel}--{dst_type}--{dst_slug}.md"
    return WIKI_ROOT / "behavioral" / "_edges" / name


def student_dir(student_name: str) -> Path:
    """Folder for a given student. Underscores in folder names."""
    folder = student_name.replace(" ", "_")
    return WIKI_ROOT / "students" / folder


def incident_path(student_name: str, ingested_at_iso: str, slug: str) -> Path:
    """Path to one incident page. ingested_at_iso is ISO 8601."""
    # YYYY-MM-DDTHH:MM:SS... -> YYYY-MM-DD-HHMM
    date_part = ingested_at_iso[:10]
    time_part = ingested_at_iso[11:16].replace(":", "")
    name = f"{date_part}-{time_part}-{slug}.md"
    return student_dir(student_name) / "incidents" / name


def persona_path(student_name: str) -> Path:
    folder = student_name.replace(" ", "_")
    return WIKI_ROOT / "personas" / f"{folder}.md"


def source_paper_path(openalex_id: str) -> Path:
    safe_id = openalex_id.split("/")[-1]
    return WIKI_ROOT / "sources" / "openalex" / f"{safe_id}.md"
