"""Run the extractor over data/notes and compare to data/labels. Prints accuracy per field.

Calls the API once per note (plus retries), so each run costs money.
Usage: uv run python eval/run_eval.py [--limit N]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from extractor import extract  # noqa: E402
from schema import ClinicalNote  # noqa: E402

NOTES = ROOT / "data" / "notes"
LABELS = ROOT / "data" / "labels"

SCALAR_FIELDS = ["patient_age", "patient_sex", "no_known_allergies"]
LIST_FIELDS = ["diagnoses", "allergies"]


MED_ATTRS = ("dose", "route", "frequency")


def norm(v):
    return v.strip().lower() if isinstance(v, str) else v


def norm_med(v):
    """'p.o.' == 'PO', '10mg' == '10 mg', 'q.8h. p.r.n.' == 'q8h prn'."""
    return re.sub(r"[\s.]", "", v).lower() if isinstance(v, str) else v


def match_medications(pred: list, gold: list) -> dict[str, float]:
    """Pair each gold med with an unused predicted med of the same name (best attribute
    overlap first), so the same drug at two doses is scored as two entries."""
    unused = list(pred)
    hits = dict.fromkeys(MED_ATTRS, 0)
    for g in gold:
        same_name = [p for p in unused if norm(p.name) == norm(g.name)]
        if not same_name:
            continue
        best = max(
            same_name,
            key=lambda p: sum(norm_med(getattr(p, a)) == norm_med(getattr(g, a)) for a in MED_ATTRS),
        )
        unused.remove(best)
        for a in MED_ATTRS:
            hits[a] += norm_med(getattr(best, a)) == norm_med(getattr(g, a))
    return {f"medications.{a}": hits[a] / len(gold) for a in MED_ATTRS}


def set_f1(pred: list, gold: list) -> float:
    p, g = {norm(x) for x in pred}, {norm(x) for x in gold}
    if not p and not g:
        return 1.0
    tp = len(p & g)
    if tp == 0:
        return 0.0
    prec, rec = tp / len(p), tp / len(g)
    return 2 * prec * rec / (prec + rec)


def score(pred: ClinicalNote, gold: ClinicalNote) -> dict[str, float]:
    s: dict[str, float] = {}
    for f in SCALAR_FIELDS:
        s[f] = float(norm(getattr(pred, f)) == norm(getattr(gold, f)))
    for f in LIST_FIELDS:
        s[f] = set_f1(getattr(pred, f), getattr(gold, f))
    for f in type(gold.vitals).model_fields:
        s[f"vitals.{f}"] = float(getattr(pred.vitals, f) == getattr(gold.vitals, f))
    s["medications.name"] = set_f1(
        [m.name for m in pred.medications], [m.name for m in gold.medications]
    )
    if gold.medications:
        s.update(match_medications(pred.medications, gold.medications))
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    totals: dict[str, list[float]] = defaultdict(list)
    note_paths = sorted(NOTES.glob("*.txt"))[: args.limit]
    for path in note_paths:
        label_path = LABELS / f"{path.stem}.json"
        if not label_path.exists():
            print(f"skip {path.stem}: no label")
            continue
        gold = ClinicalNote.model_validate_json(label_path.read_text())
        result = extract(path.read_text())
        for k, v in score(result.note, gold).items():
            totals[k].append(v)
        print(f"{path.stem}: attempts={result.attempts} issues={len(result.issues)}")

    print("\nField accuracy")
    for k in sorted(totals):
        vals = totals[k]
        print(f"  {k:<28} {sum(vals) / len(vals):6.1%}  (n={len(vals)})")


if __name__ == "__main__":
    main()
