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
    messages: list[dict] = [{"role": "user", "content": f"<note>\n{note_text}\n</note>"}]

    for attempt in range(1, max_retries + 2):
        response = client.messages.parse(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=messages,
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

        # Feed the problems back and ask for a corrected extraction.
        messages.append({"role": "assistant", "content": response.content})
        messages.append(
            {
                "role": "user",
                "content": "Your extraction has these problems:\n"
                + "\n".join(f"- {i}" for i in issues)
                + "\nRe-read the note and return a corrected extraction. "
                "Remove any value that is not stated in the note.",
            }
        )

    raise AssertionError("unreachable")
