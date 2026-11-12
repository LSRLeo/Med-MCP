"""Calls Claude to extract a ClinicalNote, retrying with feedback when validation fails."""

from __future__ import annotations

from dataclasses import dataclass, field

import anthropic
from dotenv import load_dotenv

from schema import ClinicalNote
from validator import validate

load_dotenv()

MODEL = "claude-opus-5-5"
MAX_RETRIES = 2

SYSTEM_PROMPT = """\
You extract structured data from clinical notes.

Rules:
- Only record values that are explicitly stated in the note. If a field is not stated, leave it null or empty. Never infer or estimate.
- Copy drug names, doses, and diagnoses as they appear in the note (abbreviations like HTN are fine).
- Convert temperature to Celsius only if the note gives it in Fahrenheit; otherwise copy it.
- Set no_known_allergies to true only if the note says NKDA, NKA, or "no known allergies".
"""


class ExtractionError(Exception):
    pass


@dataclass
class ExtractionResult:
    note: ClinicalNote
    issues: list[str] = field(default_factory=list)  # remaining issues after the last attempt
    attempts: int = 1


def extract(
    note_text: str,
    client: anthropic.Anthropic | None = None,
    max_retries: int = MAX_RETRIES,
) -> ExtractionResult:
    client = client or anthropic.Anthropic()
    prompt = f"<note>\n{note_text}\n</note>"

    for attempt in range(1, max_retries + 2):
        response = client.messages.parse(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            output_format=ClinicalNote,
        )
        if response.stop_reason == "refusal":
            raise ExtractionError(f"Model declined the request: {response.stop_details}")
        if response.stop_reason == "max_tokens" or response.parsed_output is None:
            raise ExtractionError(f"No parseable output (stop_reason={response.stop_reason})")

        note: ClinicalNote = response.parsed_output
        issues = validate(note, note_text)
        if not issues or attempt > max_retries:
            return ExtractionResult(note=note, issues=issues, attempts=attempt)

        # Retry as a fresh request: the note, the previous attempt, and what was wrong with it.
        prompt = (
            f"<note>\n{note_text}\n</note>\n\n"
            f"<previous_extraction>\n{note.model_dump_json(indent=2)}\n</previous_extraction>\n\n"
            "A checker found these problems with the previous extraction:\n"
            + "\n".join(f"- {i}" for i in issues)
            + "\n\nRe-read the note and return a corrected extraction. Remove any value that "
            "is not stated in the note; keep values that are correct."
        )

    raise AssertionError("unreachable")
