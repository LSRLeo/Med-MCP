from schema import ClinicalNote, Medication
from tracing import _windows_after, find_snippet, trace_note


def test_route_traced_to_its_own_medication():
    text = "MEDICATIONS: amlodipine 5 mg PO daily, Claritin 10 mg PO daily."
    note = ClinicalNote(
        medications=[
            Medication(name="amlodipine", dose="5 mg", route="PO"),
            Medication(name="Claritin", dose="10 mg", route="PO"),
        ]
    )
    traces = trace_note(note, text)
    assert traces["medications[0].route"].start == text.index("PO")
    assert traces["medications[1].route"].start == text.index("PO", text.index("Claritin"))


def test_same_drug_mentioned_twice_uses_matching_mention():
    text = (
        "In the ER she received Compazine 5 mg IV.\n"
        "Discharged on Compazine 10 mg p.o. q.8h. p.r.n."
    )
    note = ClinicalNote(medications=[Medication(name="Compazine", dose="10 mg", route="p.o.")])
    traces = trace_note(note, text)
    assert traces["medications[0].dose"].start == text.index("10 mg")
    assert traces["medications[0].route"].start == text.index("p.o.")


def test_window_stops_at_end_of_line():
    text = "metformin 500 mg BID\nlisinopril 10 mg PO daily"
    [(lo, hi)] = list(_windows_after(text, "metformin"))
    assert text[lo:hi] == "metformin 500 mg BID"


def test_falls_back_to_whole_note_when_not_near_name():
    text = "Meds: aspirin.\nAll medications are taken by mouth (PO)."
    span = find_snippet(text, "PO", "medications[0].route", near="aspirin")
    assert span is not None and span.start == text.index("PO")
