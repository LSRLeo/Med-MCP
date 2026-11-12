"""Common medical abbreviations, used to expand notes and to match values to source text."""

from __future__ import annotations

import re

ABBREVIATIONS: dict[str, str] = {
    # conditions
    "HTN": "hypertension",
    "DM": "diabetes mellitus",
    "T2DM": "type 2 diabetes mellitus",
    "CAD": "coronary artery disease",
    "CHF": "congestive heart failure",
    "COPD": "chronic obstructive pulmonary disease",
    "CKD": "chronic kidney disease",
    "AFib": "atrial fibrillation",
    "MI": "myocardial infarction",
    "GERD": "gastroesophageal reflux disease",
    "UTI": "urinary tract infection",
    "SOB": "shortness of breath",
    "CP": "chest pain",
    "HLD": "hyperlipidemia",
    # allergies
    "NKDA": "no known drug allergies",
    "NKA": "no known allergies",
    # frequency
    "QD": "daily",
    "BID": "twice daily",
    "TID": "three times daily",
    "QID": "four times daily",
    "QHS": "at bedtime",
    "PRN": "as needed",
    # routes
    "PO": "by mouth",
    "IV": "intravenous",
    "IM": "intramuscular",
    "SC": "subcutaneous",
    "SL": "sublingual",
    # vitals / misc
    "BP": "blood pressure",
    "HR": "heart rate",
    "RR": "respiratory rate",
    "SpO2": "oxygen saturation",
    "Hx": "history",
    "Pt": "patient",
    "y/o": "year old",
    "yo": "year old",
}

_LOOKUP = {k.lower(): v for k, v in ABBREVIATIONS.items()}
_REVERSE: dict[str, list[str]] = {}
for _abbr, _full in ABBREVIATIONS.items():
    _REVERSE.setdefault(_full.lower(), []).append(_abbr)


def expand(abbr: str) -> str | None:
    """Return the expansion of an abbreviation, or None if unknown."""
    return _LOOKUP.get(abbr.lower())


def abbreviations_for(term: str) -> list[str]:
    """Return known abbreviations for a full term, e.g. 'hypertension' -> ['HTN']."""
    return _REVERSE.get(term.lower(), [])


def variants(term: str) -> list[str]:
    """All spellings a term might appear as in a note: itself, its expansion, its abbreviations."""
    out = [term]
    if (full := expand(term)) is not None:
        out.append(full)
    out.extend(abbreviations_for(term))
    return out


def expand_text(text: str) -> str:
    """Append expansions after known abbreviations: 'HTN' -> 'HTN (hypertension)'."""

    def repl(m: re.Match[str]) -> str:
        word = m.group(0)
        full = expand(word)
        return f"{word} ({full})" if full else word

    return re.sub(r"\b[A-Za-z][A-Za-z0-9/]*\b", repl, text)
