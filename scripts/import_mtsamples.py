"""Pick a varied set of MTSamples notes and write them to data/notes/ as .txt files.

Free (no API calls). Deterministic: the same seed picks the same notes.
Usage: uv run python scripts/import_mtsamples.py [--n 20] [--seed 42]
"""

from __future__ import annotations

import argparse
import csv
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "mtsamples.csv"
NOTES_DIR = ROOT / "data" / "notes"

# Specialties whose notes usually contain meds / allergies / vitals.
SPECIALTIES = [
    "Consult - History and Phy.",
    "General Medicine",
    "SOAP / Chart / Progress Notes",
    "Discharge Summary",
    "Emergency Room Reports",
    "Cardiovascular / Pulmonary",
    "Office Notes",
    "Nephrology",
    "Gastroenterology",
    "Neurology",
    "Endocrinology",
    "Hematology - Oncology",
]

MIN_CHARS, MAX_CHARS = 800, 6000


HEADER = r"[A-Z][A-Z0-9 /&()'-]{2,}:"


def is_useful(text: str) -> bool:
    """Keep notes with a medications section, an allergies section, and vitals."""
    has_meds = re.search(r"MEDICATIONS?\s*:", text) is not None
    has_allergies = re.search(r"ALLERG(Y|IES)\s*:", text) is not None
    has_vitals = re.search(
        r"blood pressure|\bBP\b|pulse|heart rate|VITAL SIGNS", text, re.IGNORECASE
    ) is not None
    return has_meds and has_allergies and has_vitals


def clean(text: str) -> str:
    """Undo the Kaggle export's flattening (sections joined by '.,' and 'HEADER:,').
    Only whitespace and separator commas change; the clinical text is untouched."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r":\s*,\s*", ": ", text)  # "ALLERGIES:, None" -> "ALLERGIES: None"
    # ".,REVIEW OF SYSTEMS:" -> ".\n\nREVIEW OF SYSTEMS:"
    text = re.sub(rf"(?<=[.\"')])\s*,\s*(?={HEADER})", "\n\n", text)
    # ".,2. Item" -> ".\n2. Item" (numbered lists)
    text = re.sub(r"(?<=\.)\s*,\s*(?=\d+\.\s)", "\n", text)
    text = re.sub(r"\.\s*,\s*", ". ", text)  # any other leftover ".,"
    return text.strip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    csv.field_size_limit(sys.maxsize)
    by_specialty: dict[str, list[dict]] = defaultdict(list)
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            spec = row["medical_specialty"].strip()
            text = row["transcription"].strip()
            if "template" in row["sample_name"].lower():
                continue  # fill-in-the-blank templates, not real notes
            if spec in SPECIALTIES and MIN_CHARS <= len(text) <= MAX_CHARS and is_useful(text):
                by_specialty[spec].append(row)

    rng = random.Random(args.seed)
    for rows in by_specialty.values():
        rng.shuffle(rows)

    # Round-robin across specialties so no single one dominates.
    picked: list[dict] = []
    seen_text: set[str] = set()
    while len(picked) < args.n and any(by_specialty.values()):
        for spec in SPECIALTIES:
            if len(picked) >= args.n:
                break
            while by_specialty.get(spec):
                row = by_specialty[spec].pop()
                key = row["transcription"].strip()[:200]
                if key not in seen_text:  # MTSamples has duplicate notes across specialties
                    seen_text.add(key)
                    picked.append(row)
                    break

    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    for i, row in enumerate(picked, 1):
        note_id = f"mts_{i:02d}"
        (NOTES_DIR / f"{note_id}.txt").write_text(clean(row["transcription"]))
        print(f"{note_id}  {row['medical_specialty'].strip():<32} {row['sample_name'].strip()}")
    print(f"\nWrote {len(picked)} notes to {NOTES_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
