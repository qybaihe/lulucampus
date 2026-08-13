from __future__ import annotations

from datetime import datetime

from pydantic import Field, HttpUrl, model_validator

from onemore.core.schemas import APIModel
from onemore.modules.competitions.recommendation import RECOMMENDATION_TIER_PATTERN


class SnapshotCompetition(APIModel):
    external_key: str = Field(min_length=3, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    verification_status: str = Field(min_length=1, max_length=32)
    registration_deadline: datetime | None = None
    submission_deadline: datetime | None = None
    stages: list[dict] = Field(default_factory=list)
    mode: str = Field(default="online", max_length=32)
    location: str | None = Field(default=None, max_length=256)
    rewards: str | None = Field(default=None, max_length=2000)
    registration_url: HttpUrl
    source_url: HttpUrl
    priority: int = Field(default=0, ge=0, le=100)
    tracks: list[str] = Field(default_factory=list, max_length=30)
    required_skills: list[str] = Field(default_factory=list, max_length=50)
    team_size_min: int = Field(default=2, ge=1, le=100)
    team_size_max: int = Field(default=5, ge=1, le=100)
    eligibility: list[str] = Field(default_factory=list, max_length=30)
    participation_mode: str | None = Field(
        default=None, pattern="^(individual|team|individual_or_team)$"
    )
    registration_mode: str = Field(
        default="direct", pattern="^(direct|school_coordinated|school_notice)$"
    )
    registration_instructions: str | None = Field(default=None, max_length=2000)
    fee_note: str | None = Field(default=None, max_length=1000)
    # Storage code only. User-facing label/description are derived at read time.
    recommendation_tier: str = Field(default="B", pattern=RECOMMENDATION_TIER_PATTERN)
    verified_at: datetime | None = None

    @model_validator(mode="after")
    def validate_team_size(self) -> SnapshotCompetition:
        if self.team_size_min > self.team_size_max:
            raise ValueError("team_size_min 不能大于 team_size_max")
        if self.participation_mode is None:
            self.participation_mode = "individual" if self.team_size_max == 1 else "team"
        if self.participation_mode == "individual" and (
            self.team_size_min != 1 or self.team_size_max != 1
        ):
            raise ValueError("个人赛的队伍人数必须为 1")
        if self.participation_mode == "team" and self.team_size_max < 2:
            raise ValueError("团队赛的最大队伍人数必须至少为 2")
        for field_name in (
            "registration_deadline",
            "submission_deadline",
            "verified_at",
        ):
            value = getattr(self, field_name)
            if value is not None and value.tzinfo is None:
                raise ValueError(f"{field_name} 必须包含时区")
        if (
            self.registration_deadline
            and self.submission_deadline
            and self.registration_deadline > self.submission_deadline
        ):
            raise ValueError("报名截止时间不能晚于提交截止时间")
        return self


class CompetitionSnapshot(APIModel):
    snapshot_version: str = Field(min_length=1, max_length=64)
    generated_at: datetime
    items: list[SnapshotCompetition]

    @model_validator(mode="after")
    def validate_snapshot_time(self) -> CompetitionSnapshot:
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at 必须包含时区")
        for item in self.items:
            if item.verified_at and item.verified_at > self.generated_at:
                raise ValueError(f"{item.external_key}.verified_at 不能晚于 generated_at")
            if (
                item.verification_status.strip().lower() in {"actionable", "verified_actionable", "可行动"}
                and item.registration_deadline
                and item.registration_deadline <= self.generated_at
            ):
                raise ValueError(f"{item.external_key} 在快照生成时已经过报名截止")
        return self


class CompetitionSkillView(APIModel):
    key: str
    label: str
    weight: float


class CompetitionConstraintView(APIModel):
    team_size_min: int
    team_size_max: int
    eligibility: list[str]


class RecommendationTierView(APIModel):
    """User-facing recommendation tier catalog entry (filter chips + footnotes)."""

    code: str = Field(description="Stable storage/filter code: A | B | C")
    label: str = Field(description="Short Chinese label for UI chips")
    description: str = Field(description="One-line explanation for footnotes / empty states")
    sort_order: int = Field(description="Ascending order for filter UI (A first)")


class CompetitionView(APIModel):
    id: str
    name: str
    registration_deadline: datetime | None
    submission_deadline: datetime | None
    stages: list[dict]
    mode: str
    location: str | None
    rewards: str | None
    registration_url: str
    source_url: str
    priority: int
    tracks: list[str]
    required_skills: list[CompetitionSkillView]
    team_constraints: CompetitionConstraintView
    participation_mode: str
    registration_mode: str
    registration_instructions: str | None
    fee_note: str | None
    recommendation_tier: str = Field(
        description="Stable code A|B|C for filter query params; not a difficulty rank"
    )
    recommendation_label: str = Field(
        description="User-facing label: 优先推荐 / 可报名 / 补充参考"
    )
    recommendation_description: str = Field(
        description="Short user-facing explanation of this recommendation tier"
    )
    verified_at: datetime | None
    team_forming_supported: bool
    collaboration_action: str
    # Present when the caller is logged in and has a Douyin taste profile.
    taste_fit: float | None = None
    taste_fit_label: str | None = None
    taste_fit_reasons: list[str] = Field(default_factory=list)
    recruit_hints: list[str] = Field(default_factory=list)
    recruit_gap_count: int = 0
    recruit_gap_labels: list[str] = Field(default_factory=list)


class IngestResult(APIModel):
    snapshot_version: str
    accepted: int
    rejected_unverified: int
    deduplicated: int
    ids: list[str]


class CompetitionTeamView(APIModel):
    """招募中的赛事队伍（匿名结构：只有规模、池内人数与角色缺口，无成员身份）。"""

    id: str
    title: str
    gathering_type: str
    status: str
    location: str | None = None
    campus: str | None = None
    start_at: datetime | None = None
    target_size: int
    member_count: int
    required_roles: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    goal: str | None = None
    missing_count: int = 0
    missing_roles: list[str] = Field(default_factory=list)
    filled_roles: list[str] = Field(default_factory=list)
    roster_highlights: list[str] = Field(default_factory=list)
