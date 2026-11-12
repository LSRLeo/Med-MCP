"""Extractor tests with a fake client, so they run offline and cost nothing."""

from types import SimpleNamespace

import pytest

from extractor import ExtractionError, extract
from schema import ClinicalNote, Medication

NOTE = "45 yo M. Meds: metformin 500 mg PO BID."


def _response(parsed, stop_reason="end_turn"):
    return SimpleNamespace(
        parsed_output=parsed, stop_reason=stop_reason, stop_details=None, content=[]
    )


class FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.messages = SimpleNamespace(parse=self._parse)

    def _parse(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


def test_returns_on_first_valid_attempt():
    good = ClinicalNote(patient_age=45, medications=[Medication(name="metformin")])
    client = FakeClient([_response(good)])
    result = extract(NOTE, client=client)
    assert result.attempts == 1 and result.issues == []
    assert len(client.calls) == 1


def test_retries_with_feedback_when_invented_value():
    bad = ClinicalNote(medications=[Medication(name="insulin")])
    good = ClinicalNote(medications=[Medication(name="metformin")])
    client = FakeClient([_response(bad), _response(good)])
    result = extract(NOTE, client=client)
    assert result.attempts == 2 and result.issues == []
    feedback = client.calls[1]["messages"][-1]["content"]
    assert "insulin" in feedback


def test_gives_up_after_max_retries_and_reports_issues():
    bad = ClinicalNote(medications=[Medication(name="insulin")])
    client = FakeClient([_response(bad)] * 3)
    result = extract(NOTE, client=client, max_retries=2)
    assert result.attempts == 3 and result.issues


def test_refusal_raises():
    client = FakeClient([_response(None, stop_reason="refusal")])
    with pytest.raises(ExtractionError):
        extract(NOTE, client=client)
