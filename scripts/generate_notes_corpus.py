from __future__ import annotations

from pathlib import Path
import argparse
import random
import re


CHILDREN = [
    "Aavya Chaudhary",
    "Reya Kori Desai",
    "Navisha Yadav",
    "Trishika",
    "Shaurya Savaj",
    "Aarav Mehta",
    "Ira Patel",
    "Kabir Sinha",
    "Mira Shah",
    "Vihaan Joshi",
    "Anaya Rao",
    "Rian Kapoor",
    "Saanvi Verma",
    "Arjun Nair",
    "Inaaya Khan",
    "Atharv Iyer",
    "Diya Malhotra",
    "Dev Patel",
    "Nina Bose",
    "Kiaan Gupta",
]

EDUCATORS = [
    "Amrita Maitra",
    "Sajitha Kandathil",
    "Yogitha M",
    "Hima Brijeshkumar Savaj",
    "Nandini Rao",
    "Meera Iyer",
    "Pooja Menon",
    "Anjali Deshmukh",
]

NEUTRAL_SCENES = [
    "carefully selected a familiar material from the shelf and settled into it without needing a second invitation",
    "repeated the same sequence several times until the motion became smooth and confident",
    "moved through the activity at an unhurried pace and stayed with the work cycle for its full length",
    "watched a presentation, then quietly returned to the material and repeated the steps in order",
    "carried the tray with both hands, placed it carefully on the rug, and worked with a steady, purposeful rhythm",
]

NEUTRAL_DETAIL_1 = [
    "The child's hands stayed controlled, and when a piece did not fit correctly, they paused, looked closely, and corrected the placement on their own.",
    "The educator gave a brief demonstration at the start, then stepped back while the child continued with visible concentration.",
    "There was no need for repeated redirection; the child used the room well, selected the next step, and stayed oriented to the task.",
    "The material was returned to the shelf in sequence, with the child checking that each piece was placed back where it belonged.",
]

NEUTRAL_DETAIL_2 = [
    "Nearby movement and conversation did not interrupt the work, and the child kept returning to the task after only a quick glance around the room.",
    "The child accepted a small prompt with ease and then carried the remainder of the sequence independently.",
    "The pace remained calm from beginning to end, and the child appeared comfortable repeating the work without adult intervention.",
    "The interaction with the material was careful and deliberate, showing a clear understanding of the routine and the expected order.",
]

NEUTRAL_OUTCOME = [
    "By the end of the observation, the child looked settled and satisfied, with the work completed and the environment left orderly.",
    "The work cycle ended quietly, and the child transitioned away from the material without resistance or disruption.",
    "The observation showed consistent attention to the task and a strong ability to sustain effort in the Montessori environment.",
    "The child maintained a calm body, used the material respectfully, and rejoined the classroom rhythm smoothly after finishing.",
]

PROBLEM_SCENES = [
    "had difficulty settling into the work cycle and moved restlessly between materials without completing a clear sequence",
    "called out repeatedly while peers were working and needed several reminders about the classroom voice level",
    "became frustrated when the material did not go as expected and began to push the tray and speak sharply",
    "struggled during a transition and showed an unsettled body, with repeated stopping, starting, and returning to the same spot",
    "approached a peer's work without waiting and had to be redirected several times around personal space and turn-taking",
]

PROBLEM_DETAIL_1 = [
    "The educator knelt beside the child, named the limit clearly, and gave a short, calm reminder before stepping back.",
    "A nearby peer was moved to a different spot while the child was helped to slow down and reset the work area.",
    "The child was offered a pause and a chance to breathe, then guided back toward the task with close adult support.",
    "The adult repeated the expectation in simple language and stayed close while the child tried to re-enter the activity safely.",
]

PROBLEM_DETAIL_2 = [
    "There were moments of compliance, but they were brief, and the child drifted back into the same pattern of interruption soon after.",
    "The child needed more than one intervention before the behavior softened enough for the work to continue.",
    "Even after redirection, the child remained dysregulated for a while and required the adult to stay nearby.",
    "The behavior affected the surrounding area, so the educator kept the interaction short and focused on immediate safety and boundaries.",
]

PROBLEM_OUTCOME = [
    "Eventually the child was able to settle, though the observation made clear that the transition was uneven and required adult support.",
    "The situation de-escalated after repeated limit-setting, but the child did not return to the work with the same calmness seen in other observations.",
    "The note reflects a pattern of difficulty managing frustration in the moment, especially when the activity changed or when the peer environment became busy.",
    "The child ended the observation in a more settled state, but only after sustained support and several clear reminders.",
]


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def wrap_paragraph(sentence_parts: list[str]) -> str:
    return " ".join(sentence_parts)


def build_note(index: int, rng: random.Random) -> tuple[str, str]:
    neutral = index < 50
    child = CHILDREN[index % len(CHILDREN)]
    educator = EDUCATORS[index % len(EDUCATORS)]

    if neutral:
        scene = rng.choice(NEUTRAL_SCENES)
        title_bits = [
            "quiet work",
            "steady repetition",
            "focused observation",
            "independent practice",
            "careful material use",
        ]
        title = rng.choice(title_bits)
        para1 = f"{child} {scene} during the morning work period. The observation started with a calm body and a clear choice of material, and the child stayed oriented to the task without needing the educator to restart the sequence."
        para2 = wrap_paragraph(
            [
                rng.choice(NEUTRAL_DETAIL_1),
                rng.choice(NEUTRAL_DETAIL_2),
            ]
        )
        para3 = wrap_paragraph(
            [
                rng.choice(NEUTRAL_OUTCOME),
                f"{educator} noted that the child remained available for follow-up work and did not show resistance when the material was put away.",
            ]
        )
        body = "\n\n".join([para1, para2, para3])
        behavior = "Neutral"
    else:
        scene = rng.choice(PROBLEM_SCENES)
        title_bits = [
            "transition difficulty",
            "circle time disruption",
            "peer boundary concern",
            "frustration at the shelf",
            "voice level reminder",
        ]
        title = rng.choice(title_bits)
        para1 = f"{child} {scene} in a way that was noticeable to the room. {educator} was already nearby and had to intervene early because the behavior escalated faster than the surrounding children could ignore it."
        para2 = wrap_paragraph(
            [
                rng.choice(PROBLEM_DETAIL_1),
                rng.choice(PROBLEM_DETAIL_2),
            ]
        )
        para3 = wrap_paragraph(
            [
                rng.choice(PROBLEM_OUTCOME),
                "The note does not add a plan or extra interpretation; it simply captures the observed behavior, the immediate adult response, and the child's condition by the end of the moment.",
            ]
        )
        body = "\n\n".join([para1, para2, para3])
        behavior = "Problematic"

    filename = f"{behavior.lower()}_{index + 1:03d}_{slugify(title)}.txt"
    content = f"Name: {child}\n\n{body}\n"
    return filename, content


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate verbose Montessori observation notes.")
    parser.add_argument("--output-dir", type=Path, default=Path("notes_streamer/notes"))
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for existing in args.output_dir.glob("*.txt"):
        existing.unlink()

    for index in range(args.count):
        filename, content = build_note(index, rng)
        (args.output_dir / filename).write_text(content, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
