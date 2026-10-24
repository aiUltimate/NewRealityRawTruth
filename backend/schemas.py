from typing import Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator


class EvidenceItem(BaseModel):
    excerpt: str = Field(description="Short exact excerpt from supplied page text, or empty when no excerpt applies.")
    observation: str = Field(description="What is directly observable in the supplied material.")
    interpretation: str = Field(description="A plausible interpretation, clearly distinguished from the observation.")
    confidence: Literal["low", "medium", "high"] = "low"


class IncentiveLens(BaseModel):
    rating: int = Field(ge=0, le=100, description="Heuristic strength of evidenced incentive signals, not a deception score.")
    likely_beneficiaries: list[str] = []
    observable_incentives: list[str] = []
    hypotheses: list[str] = []
    evidence: list[EvidenceItem] = []
    unknowns: list[str] = []


class SpinLens(BaseModel):
    score: int = Field(ge=0, le=100, description="Heuristic amount of evidenced framing signals; not a truthfulness score.")
    techniques: list[str] = []
    omissions_to_check: list[str] = []
    emotional_triggers: list[str] = []
    evidence: list[EvidenceItem] = []
    unknowns: list[str] = []


class PsychologyLens(BaseModel):
    observed_dynamics: list[str] = []
    possible_mechanisms: list[str] = []
    coordination_assessment: str = "No assessment possible without relevant evidence."
    evidence: list[EvidenceItem] = []
    unknowns: list[str] = []


class RealityLens(BaseModel):
    plain_language_summary: str
    factual_claims: list[str] = []
    causal_mechanisms: list[str] = []
    supported_conclusions: list[str] = []
    unresolved_questions: list[str] = []
    evidence_limitations: list[str] = []


class AnalysisResult(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    title: str = ""
    url: str
    domain: str
    analyzed_at: str
    provider: str
    summary: str
    incentives: IncentiveLens
    spin: SpinLens
    psychology: PsychologyLens
    raw_truth: RealityLens
    overall_confidence: Literal["low", "medium", "high"] = "low"
    caveats: list[str] = []


class AnalyzeRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    title: str = Field(default="", max_length=500)
    text: str = Field(min_length=40, max_length=18000)
    comments: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Page text must not be blank.")
        return value.strip()


class AnalyzeResponse(BaseModel):
    analysis_id: int
    result: AnalysisResult
