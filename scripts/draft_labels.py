"""Draft labels for unlabeled notes by running the extractor. YOU must review them.

Writes to data/labels_draft/ (not data/labels/) so unreviewed drafts never count in the eval.
After correcting a draft, move it into data/labels/.

Calls the API once per note (plus retries), so it costs money.
Usage: uv run python scripts/draft_labels.py [--only mts_01 mts_02 ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from extractor import ExtractionError, extract  # noqa: E402

NOTES = ROOT / "data" / "notes"
LABELS = ROOT / "data" / "labels"
DRAFTS = ROOT / "data" / "labels_draft"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="note ids to draft (default: all unlabeled)")
    args = ap.parse_args()

    DRAFTS.mkdir(parents=True, exist_ok=True)
    for path in sorted(NOTES.glob("*.txt")):
        note_id = path.stem
        if args.only and note_id not in args.only:
            continue
        if (LABELS / f"{note_id}.json").exists() or (DRAFTS / f"{note_id}.json").exists():
            continue  # already labeled or drafted
        try:
            result = extract(path.read_text())
        except ExtractionError as e:
            print(f"{note_id}: FAILED - {e}")
            continue
        (DRAFTS / f"{note_id}.json").write_text(result.note.model_dump_json(indent=2) + "\n")
        status = "ok" if not result.issues else f"{len(result.issues)} issue(s) - check these:"
        print(f"{note_id}: attempts={result.attempts} {status}")
        for issue in result.issues:
            print(f"    - {issue}")

    print(f"\nDrafts are in {DRAFTS.relative_to(ROOT)}/. Correct each one against its note,")
    print("then move it to data/labels/ so run_eval.py uses it.")


if __name__ == "__main__":
    main()
