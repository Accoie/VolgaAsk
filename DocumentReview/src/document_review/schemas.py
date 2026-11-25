from pydantic import BaseModel, ConfigDict, Field, StrictBool


class CheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    safe: StrictBool


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location: str = Field(min_length=1)
    description: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)


class ReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1)
    remarks: list[Finding]
    errors: list[Finding]
    recommendations: list[str]


class CombinedReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    legal: ReviewResult
    accounting: ReviewResult


class ReviewError(Exception):
    """Ошибка проверки документа."""
