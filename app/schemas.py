from pydantic import BaseModel, Field


class Fix(BaseModel):
    explanation: str
    commands: list[str] = []


class Issue(BaseModel):
    resource: str
    symptom: str
    root_cause: str
    evidence: list[str] = Field(min_length=1)   # no claim without evidence
    fix: Fix
    confidence: float = Field(ge=0, le=1)       # must be between 0 and 1


class Diagnosis(BaseModel):
    summary: str
    issues: list[Issue]