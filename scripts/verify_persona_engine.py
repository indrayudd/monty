"""Verify persona engine returns structurally valid notes for all 5 personas."""
import sys
from notes_streamer.persona_engine import generate_next_note, PersonaOverrides

NAMES = ["Arjun Nair", "Diya Malhotra", "Kiaan Gupta", "Mira Shah", "Saanvi Verma"]

def main() -> int:
    failures: list[str] = []
    for name in NAMES:
        try:
            note = generate_next_note(name, overrides=PersonaOverrides(slider=0.0))
        except Exception as e:
            failures.append(f"{name}: exception {e!r}")
            continue
        if note.get("name") != name:
            failures.append(f"{name}: returned wrong name {note.get('name')!r}")
        body = note.get("body") or ""
        if not body.startswith("Name:"):
            failures.append(f"{name}: body missing 'Name:' header")
        if name not in body:
            failures.append(f"{name}: body missing the child's name")

    # Inject test
    try:
        emerg = generate_next_note("Mira Shah", overrides=PersonaOverrides(inject_next="emergency"))
        if emerg.get("severity_hint") != "red":
            failures.append("emergency inject did not set severity_hint=red")
    except Exception as e:
        failures.append(f"emergency inject exception: {e!r}")

    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print(f"OK — generated {len(NAMES)} notes + 1 emergency inject")
    return 0

if __name__ == "__main__":
    sys.exit(main())
