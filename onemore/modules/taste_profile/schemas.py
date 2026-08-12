from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, SecretStr, field_validator

from onemore.core.schemas import APIModel


class SourceProfile(APIModel):
    nickname: str | None = None
    avatar_url: str | None = None
    uid: str | None = None
    sec_uid: str | None = None


class ProgressView(APIModel):
    phase: str
    current: int = 0
    total: int | None = None
    percent: float | None = None
    message: str = ""
    qr_scanned: bool | None = None
    phone_masked: str | None = None
    code_sent: bool | None = None


class CollectionView(APIModel):
    api_pages: int = 0
    items_collected: int = 0
    has_more: bool = True


class TagScoreView(APIModel):
    key: str
    label: str
    score: float


class DomainScoreView(APIModel):
    key: str
    label: str
    score: float


class InterestFacetView(APIModel):
    domain: str
    facet: str
    label: str
    source: str | None = None
    question_id: str | None = None


class SampleSummaryView(APIModel):
    items: int = 0
    unique_authors: int = 0
    api_pages: int = 0
    calibrated: bool = False
    calibrated_at: str | None = None
    interest_facets: list[InterestFacetView] = Field(default_factory=list)
    generation: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    persona: str | None = None
    matching_hints: list[str] = Field(default_factory=list)
    tone: str | None = None
    llm_error: str | None = None


class TasteProfileResultView(APIModel):
    """Final / provisional taste profile returned by taste APIs."""

    status: str = "READY"
    primary_tag: TagScoreView
    secondary_tags: list[TagScoreView] = Field(default_factory=list)
    interest_domains: list[DomainScoreView] = Field(default_factory=list)
    interest_facets: list[InterestFacetView] = Field(default_factory=list)
    dimensions: dict[str, float] = Field(default_factory=dict)
    summary: str = ""
    persona: str | None = None
    matching_hints: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    calibrated: bool = False
    calibrated_at: str | None = None
    sample: SampleSummaryView | dict[str, Any] = Field(default_factory=dict)
    source: str = "douyin"
    model_version: str = "taste-v2"
    visibility: str = "members"


class QuestionOptionView(APIModel):
    id: str
    label: str


class QuestionView(APIModel):
    id: str
    type: str = "single_choice"
    prompt: str
    required: bool = True
    options: list[QuestionOptionView]


class ImportSessionView(APIModel):
    id: str
    source: str = "douyin"
    status: str
    qr_image_data_url: str | None = None
    qr_version: int = 0
    qr_expires_at: datetime | None = None
    expires_at: datetime
    source_profile: SourceProfile | None = None
    progress: ProgressView
    collection: CollectionView | None = None
    candidate_tags: list[TagScoreView] = Field(default_factory=list)
    question_count: int = 0
    # Embedded quiz JSON when READY and not yet calibrated (iOS can render immediately).
    questions: dict[str, Any] | None = None
    result: TasteProfileResultView | dict[str, Any] | None = None
    error: dict[str, str] | None = None


class QRLoginView(APIModel):
    import_id: str
    status: str
    qr_image_data_url: str | None = None
    qr_version: int = 0
    qr_expires_at: datetime | None = None
    qr_image_url: str
    phone_code: str
    verify: str
    error: dict[str, str] | None = None


class LoginVerificationView(APIModel):
    import_id: str
    status: str
    verified: bool
    authenticated_at: datetime | None = None
    source_profile: SourceProfile | None = None
    next: str
    error: dict[str, str] | None = None


class PhoneCodeRequest(APIModel):
    phone: SecretStr
    country_code: str = "86"

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: SecretStr) -> SecretStr:
        phone = value.get_secret_value()
        if not phone.isdigit() or not 5 <= len(phone) <= 20:
            raise ValueError("手机号格式不正确")
        return value

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, value: str) -> str:
        normalized = value.lstrip("+")
        if not normalized.isdigit() or not 1 <= len(normalized) <= 4:
            raise ValueError("国家或地区代码格式不正确")
        return normalized


class PhoneCodeSubmit(APIModel):
    code: SecretStr

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: SecretStr) -> SecretStr:
        code = value.get_secret_value()
        if not code.isdigit() or not 4 <= len(code) <= 8:
            raise ValueError("验证码格式不正确")
        return value


class PhoneLoginView(APIModel):
    import_id: str
    status: str
    phone_masked: str | None = None
    code_sent: bool = False
    verified: bool = False
    authenticated_at: datetime | None = None
    submit_code: str
    verify: str
    error: dict[str, str] | None = None


class ImportCreateRequest(APIModel):
    profile_url: str | None = None
    max_items: int = Field(default=0, ge=0)
    force: bool = False


class ImportItemAuthor(APIModel):
    nickname: str = ""
    uid: str = ""
    sec_uid: str = ""


class ImportItemStatistics(APIModel):
    likes: int = 0
    comments: int = 0
    collects: int = 0
    shares: int = 0


class ImportItemView(APIModel):
    aweme_id: str
    kind: str
    url: str
    title: str = ""
    description: str = ""
    hashtags: list[str] = Field(default_factory=list)
    platform_tags: list[str] = Field(default_factory=list)
    author: ImportItemAuthor = Field(default_factory=ImportItemAuthor)
    published_at: str | None = None
    duration_seconds: float | None = None
    statistics: ImportItemStatistics = Field(default_factory=ImportItemStatistics)
    is_aigc: bool = False


class ItemsPageView(APIModel):
    items: list[ImportItemView] = Field(default_factory=list)
    next_cursor: int = 0
    has_more: bool = False


class QuestionsView(APIModel):
    """JSON quiz package for native iOS.

    iOS loads this, renders single-choice questions, then POSTs answers to
    ``submit_path`` (or POST /profile/imports/{id}/answers).
    """

    schema_version: str = "taste-quiz-v1"
    import_id: str
    candidate_tags: list[TagScoreView] = Field(default_factory=list)
    questions: list[QuestionView] = Field(default_factory=list)
    calibrated: bool = False
    optional: bool = True
    min_answers: int = 3
    max_answers: int = 5
    intro: str = ""
    submit_path: str = ""


class QuizAnswerIn(APIModel):
    question_id: str
    option_id: str


class QuizAnswersRequest(APIModel):
    answers: list[QuizAnswerIn] = Field(min_length=3, max_length=5)
