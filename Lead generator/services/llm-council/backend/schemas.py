"""Pydantic request / response schemas for the public API."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=20_000)


class ConversationMetadata(BaseModel):
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Council stages
# ---------------------------------------------------------------------------


class ModelError(BaseModel):
    """Structured upstream-error info attached to a failed council stage."""

    kind: str
    status: Optional[int] = None
    message: str
    fallback_model: Optional[str] = None


class ModelResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model: str
    response: str
    error: Optional[ModelError] = None


class RankingResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model: str
    ranking: str
    parsed_ranking: List[str] = Field(default_factory=list)


class AggregateRanking(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model: str
    average_rank: float
    rankings_count: int


class CouncilMetadata(BaseModel):
    label_to_model: Dict[str, str] = Field(default_factory=dict)
    aggregate_rankings: List[AggregateRanking] = Field(default_factory=list)


class CouncilOutput(BaseModel):
    stage1: List[ModelResponse]
    stage2: List[RankingResponse]
    stage3: ModelResponse
    metadata: CouncilMetadata


# ---------------------------------------------------------------------------
# Domain endpoints: lead intelligence
# ---------------------------------------------------------------------------


class CouncilQueryRequest(BaseModel):
    """Generic council query — any prompt the caller wants 3-stage analysis on."""

    query: str = Field(..., min_length=1, max_length=20_000)
    persist: bool = Field(
        default=False, description="If true, store the run as a conversation."
    )


class LeadInput(BaseModel):
    """Minimal lead shape — accepts any JSON-compatible record."""

    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    domain: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None


class AnalyzeLeadRequest(BaseModel):
    lead: LeadInput
    objective: str = Field(
        default="qualify this lead for outbound outreach",
        description="What the caller wants the council to decide.",
    )
    locale: str = Field(default="en", description="Output language (e.g. 'en', 'nl').")


class GenerateOutreachRequest(BaseModel):
    lead: LeadInput
    angle: str = Field(
        default="warm intro, value-led",
        description="High-level positioning the council should reflect.",
    )
    channel: Literal["email", "linkedin", "sms"] = "email"
    locale: str = "en"
    tone: str = Field(default="professional, direct, friendly")
    max_length_chars: int = Field(default=900, ge=100, le=4000)


class ReviewScrapeRequest(BaseModel):
    """Ask the council to review scraped records for quality and red flags."""

    sample: List[Dict[str, Any]] = Field(..., min_length=1, max_length=50)
    source_name: str = Field(default="unspecified scrape source", max_length=200)
    criteria: Optional[str] = Field(
        default=None,
        description="What 'good' looks like for this scrape (optional).",
    )


# ---------------------------------------------------------------------------
# Lead intelligence — structured scoring + outreach sequence
# ---------------------------------------------------------------------------


class ScoreLeadRequest(BaseModel):
    """Structured scoring request — single lead in, structured intel out."""

    lead: LeadInput
    objective: str = Field(
        default="qualify this lead for outbound AI-automation outreach",
        max_length=400,
    )
    locale: str = Field(default="en", max_length=10)
    strategy: Literal["fast", "council"] = Field(
        default="fast",
        description="'fast' = single chairman call. 'council' = full 3-stage deliberation.",
    )
    use_cache: bool = True


class LeadIntelligence(BaseModel):
    """Structured intelligence dict matching the lead-radar consumer contract."""

    model_config = ConfigDict(protected_namespaces=())

    company_name: str = ""
    lead_quality_score: int = Field(default=0, ge=0, le=10)
    automation_fit_score: int = Field(default=0, ge=0, le=10)
    estimated_budget: str = ""
    urgency_score: int = Field(default=0, ge=0, le=10)
    outbound_potential: int = Field(default=0, ge=0, le=10)
    ai_opportunities: List[str] = Field(default_factory=list)
    pain_points: List[str] = Field(default_factory=list)
    recommended_offer: str = ""
    best_outreach_angle: str = ""
    recommended_channel: Literal["email", "linkedin", "sms", "phone"] = "email"
    confidence_score: int = Field(default=0, ge=0, le=10)
    rationale: str = ""


class ScoreLeadResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    lead_id: Optional[str] = None
    intelligence: LeadIntelligence
    strategy: Literal["fast", "council"]
    model: str
    elapsed_ms: int
    json_parsed: bool
    error: Optional[ModelError] = None


class FollowUpStep(BaseModel):
    day: int = Field(default=3, ge=0, le=90)
    channel: Literal["email", "linkedin", "sms", "phone"] = "email"
    subject: str = ""
    body: str = ""


class ColdEmail(BaseModel):
    subject: str = ""
    body: str = ""


class OutreachSequence(BaseModel):
    cold_email: ColdEmail = Field(default_factory=ColdEmail)
    linkedin_opener: str = ""
    follow_up_sequence: List[FollowUpStep] = Field(default_factory=list)
    cta_suggestions: List[str] = Field(default_factory=list)


class GenerateSequenceRequest(BaseModel):
    lead: LeadInput
    analysis: LeadIntelligence
    locale: str = "en"
    tone: str = "professional, direct, friendly"
    use_cache: bool = True


class GenerateSequenceResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    lead_id: Optional[str] = None
    sequence: OutreachSequence
    model: str
    elapsed_ms: int
    json_parsed: bool
    error: Optional[ModelError] = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthStatus(BaseModel):
    status: Literal["ok", "degraded"]
    service: str = "llm-council"
    version: str
    env: str
    council_models: List[str]
    chairman_model: str
    openrouter_configured: bool
