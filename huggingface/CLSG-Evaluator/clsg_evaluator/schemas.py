from enum import Enum

from pydantic import BaseModel, Field


class LinguisticForm(str, Enum):
    english = "english"
    urdu = "urdu"
    roman_urdu = "roman_urdu"
    code_switched = "code_switched"


class VerificationStatus(str, Enum):
    verified = "verified"
    pending = "pending"
    flagged = "flagged"


class Variant(BaseModel):
    form: LinguisticForm
    text: str
    similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    verification_status: VerificationStatus = VerificationStatus.pending


class TestCase(BaseModel):
    id: str
    intent_category: str
    intent: str
    variants: list[Variant]


class GenerateVariantsRequest(BaseModel):
    english_text: str = Field(min_length=1, max_length=2000)


class GenerateVariantsResponse(BaseModel):
    variants: list[Variant]
    note: str


class ModelConfig(BaseModel):
    adapter: str = Field(description="Registered ModelAdapter key, e.g. 'huggingface', 'demo'")
    model_id: str
    display_name: str | None = None


class EvaluationDimensionScore(BaseModel):
    dimension: str
    score: float = Field(ge=0.0, le=100.0)
    notes: str | None = None


class ModelLanguageResult(BaseModel):
    model_id: str
    form: LinguisticForm
    safety_score: float = Field(ge=0.0, le=100.0)
    refusal_consistency: float = Field(ge=0.0, le=100.0)
    instruction_following: float = Field(ge=0.0, le=100.0)
    dimensions: list[EvaluationDimensionScore] = []


class EvaluateRequest(BaseModel):
    test_case: TestCase
    models: list[ModelConfig]


class EvaluateResponse(BaseModel):
    results: list[ModelLanguageResult]
    demo_mode: bool


class CLSGResult(BaseModel):
    reference_form: LinguisticForm
    evaluation_form: LinguisticForm
    reference_score: float
    evaluation_score: float
    gap_points: float
