"""Pydantic request / response schemas for the public API.

The council is a *moderation and verification* layer for public-intent
posts. Every schema below is aligned with the trust-provenance-moderation
doctrine: provenance > volume, HOT-only delivery, one lead one installer,
no AI-leadgen framing, no marketplace framing.
"""

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
# Council stages (generic 3-stage deliberation surface)
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


class CouncilQueryRequest(BaseModel):
    """Generic council query — any prompt the caller wants 3-stage analysis on."""

    query: str = Field(..., min_length=1, max_length=20_000)
    persist: bool = Field(
        default=False, description="If true, store the run as a conversation."
    )


# ---------------------------------------------------------------------------
# Source-quality review (generic, content-agnostic)
# ---------------------------------------------------------------------------


class ReviewScrapeRequest(BaseModel):
    """Ask the council to review a scraped sample for source quality and red flags."""

    sample: List[Dict[str, Any]] = Field(..., min_length=1, max_length=50)
    source_name: str = Field(default="unspecified scrape source", max_length=200)
    criteria: Optional[str] = Field(
        default=None,
        description="What 'good' looks like for this source (optional).",
    )


# ---------------------------------------------------------------------------
# Lead moderation — provenance + intent verification
# ---------------------------------------------------------------------------


# Doctrine-aligned controlled vocabularies.

LeadTemperature = Literal["HOT", "WARM", "OPP"]
"""HOT = explicit purchase intent + verifiable identity hook.
WARM = clear research intent, no immediate purchase signal.
OPP = plausible signal needing investigation.
(Doctrine §01.5; supersedes 'COLD' from generic SaaS scoring vocab.)"""

ConfidenceBand = Literal["high", "medium", "low"]
"""How confident the council is in its OWN classification (not a model_score).
Reviewer band (§01.5) is assigned downstream by a human, not the council."""

ProvenanceStatus = Literal["verified", "likely", "unverifiable", "rejected"]
"""verified   = source resolves, snippet matches, author signals are intact
likely     = mild gaps but on balance authentic homeowner intent
unverifiable = cannot independently confirm the source; do not deliver
rejected   = directory / marketplace / spam / non-homeowner — drop"""

SignalType = Literal[
    "INTENT_DIRECT",
    "INTENT_RESEARCH",
    "INTENT_QUOTE",
    "INTENT_PROBLEM",
    "INTENT_TIMELINE",
    "NONE",
]
"""Doctrine §01.4 signal taxonomy v0. Conversion is tracked per signal type."""

PurchaseWindow = Literal["<30 days", "30-90 days", "90+ days", "unknown"]
ValueBand = Literal["<5k EUR", "5-15k EUR", "15-30k EUR", "30k+ EUR", "unknown"]
SourceQuality = Literal["high", "medium", "low"]
DuplicateRisk = Literal["low", "medium", "high"]


class LeadCandidate(BaseModel):
    """A captured public post the council is asked to moderate.

    These are the five-thing fields (doctrine §00.2) plus optional context
    a scraper may supply. Extra fields are allowed so source-specific
    metadata (thread_id, votes, reply_count, …) is preserved.
    """

    model_config = ConfigDict(extra="allow")

    source_url: str = Field(..., max_length=2000)
    snippet: str = Field(..., min_length=1, max_length=4000,
                         description="Verbatim post text. Stored as-is; never paraphrased.")
    captured_at: str = Field(..., description="ISO-8601 UTC timestamp of capture.")

    source_platform: Optional[str] = Field(default=None, max_length=200)
    posted_at: Optional[str] = None
    snippet_lang: Optional[Literal["nl", "en", "other"]] = None
    region: Optional[str] = Field(default=None, max_length=200)
    niche: Optional[str] = Field(default=None, max_length=120)
    author_handle: Optional[str] = Field(default=None, max_length=200)
    candidate_id: Optional[str] = Field(default=None, max_length=120,
                                        description="Opaque scraper-side id for traceability.")


class LeadReview(BaseModel):
    """The council's moderation verdict on a single public-intent post.

    This is a *recommendation* surface. The accountable reviewer (doctrine
    §00.4, §01.5) assigns the final delivery band; nothing here ships to
    an installateur without human approval. Provenance > volume.
    """

    model_config = ConfigDict(protected_namespaces=())

    # --- Echoed-back provenance trail (five-thing rule, §00.2) ----------
    source_url: str
    verbatim_snippet: str = Field(
        default="", description="Verbatim post text, canonicalized (never paraphrased)."
    )
    captured_at: str = ""

    # --- Council classification -----------------------------------------
    lead_temperature: LeadTemperature = "OPP"
    confidence_band: ConfidenceBand = "low"
    provenance_status: ProvenanceStatus = "unverifiable"
    signal_type: SignalType = "NONE"

    # --- Council interpretation (free text, never paraphrasing) ---------
    intent_summary: str = Field(
        default="",
        description="One-sentence factual summary the reviewer could repeat.",
    )
    homeowner_motivation: str = Field(
        default="",
        description="What the homeowner is trying to solve, in their own framing.",
    )

    # --- Banded estimates (deterministic enums, not free-form numbers) --
    estimated_purchase_window: PurchaseWindow = "unknown"
    estimated_install_value_band: ValueBand = "unknown"

    # --- Trust / quality flags ------------------------------------------
    trust_flags: List[str] = Field(
        default_factory=list,
        description=(
            "Structured flags such as: directory_source, marketplace_source, "
            "outdated_thread, non_homeowner, speculative_language, "
            "unverifiable_author, decayed_url, spam_signals, off_topic."
        ),
    )
    review_required: bool = Field(
        default=True,
        description="True unless the lead is unambiguously deliverable as HOT.",
    )
    duplicate_risk: DuplicateRisk = "low"
    source_quality: SourceQuality = "low"

    # --- Reviewer explainability ----------------------------------------
    rejection_reason: str = Field(
        default="",
        description="Filled when the council declines to recommend delivery.",
    )
    reviewer_notes: str = Field(
        default="",
        description="Short note explaining the call (max 2 sentences).",
    )


class ModerateLeadRequest(BaseModel):
    """Submit a single captured post for council moderation."""

    candidate: LeadCandidate
    locale: str = Field(default="nl", max_length=10,
                        description="Output language for free-text fields.")
    strategy: Literal["fast", "council"] = Field(
        default="fast",
        description=("'fast' = single chairman call; cheap and deterministic. "
                     "'council' = full 3-stage deliberation; richer rationale."),
    )
    use_cache: bool = True


class TokenUsage(BaseModel):
    """OpenRouter usage block. All counts are integers."""

    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class ModerateLeadResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    candidate_id: Optional[str] = None
    review: LeadReview
    strategy: Literal["fast", "council"]
    model: str
    elapsed_ms: int
    json_parsed: bool
    usage: Optional[TokenUsage] = None
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
