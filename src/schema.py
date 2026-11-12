"""Pydantic models for structured clinical note data.

Every field is optional or defaults to empty: the model must leave a field
empty rather than guess when the note doesn't state it.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Medication(BaseModel):
    name: str = Field(description="Drug name as written, e.g. 'lisinopril'")
    dose: Optional[str] = Field(None, description="Dose with units, e.g. '10 mg'")
    route: Optional[str] = Field(None, description="e.g. 'PO', 'IV'")
    frequency: Optional[str] = Field(None, description="e.g. 'BID', 'daily'")


class Vitals(BaseModel):
    systolic_bp: Optional[int] = Field(None, description="mmHg")
    diastolic_bp: Optional[int] = Field(None, description="mmHg")
    heart_rate: Optional[int] = Field(None, description="beats per minute")
    respiratory_rate: Optional[int] = Field(None, description="breaths per minute")
    temperature_c: Optional[float] = Field(None, description="degrees Celsius")
    spo2: Optional[int] = Field(None, description="oxygen saturation, percent")


class ClinicalNote(BaseModel):
    patient_age: Optional[int] = Field(None, description="Age in years")
    patient_sex: Optional[Literal["male", "female", "other"]] = None
    chief_complaint: Optional[str] = None
    diagnoses: list[str] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    allergies: list[str] = Field(
        default_factory=list,
        description="Allergen names. Empty if NKDA or not mentioned.",
    )
    no_known_allergies: bool = Field(
        False, description="True only if the note explicitly says NKDA / no known allergies"
    )
    vitals: Vitals = Field(default_factory=Vitals)
