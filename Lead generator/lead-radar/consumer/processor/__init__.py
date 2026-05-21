"""Processor — clean, classify, score."""
from __future__ import annotations

from .cleaner import (
    clean_post,
    smart_summary,
    has_urgency,
    detect_province,
    generate_message,
)
from .intent_classifier import is_potential_lead, classify_post_kind
from .scorer import score_post
from .hardblock import check_hardblock, is_blocked, BlockResult
from .llm_verifier import (
    LlmVerdict, should_verify, verify_post, combine_score,
)
from .dedup import TextSignatureStore, shingles, jaccard
from .cross_run_dedup import (
    is_cross_run_duplicate,
    record_lead_signature,
    prune_store as prune_cross_run_store,
)
from .author_signature_dedup import (
    is_author_repeat,
    record_author_post,
    prune_author_store,
    SOURCES_WITH_AUTHOR,
)
from .source_weight import apply_source_weight, load_source_weights
from .sellability_gate import is_sellable, GateResult
from .recency_boost import apply_recency_boost, AGED_OUT

__all__ = [
    "clean_post", "smart_summary", "has_urgency",
    "detect_province", "generate_message",
    "is_potential_lead", "classify_post_kind", "score_post",
    "check_hardblock", "is_blocked", "BlockResult",
    "LlmVerdict", "should_verify", "verify_post", "combine_score",
    "TextSignatureStore", "shingles", "jaccard",
    "is_cross_run_duplicate", "record_lead_signature", "prune_cross_run_store",
    "is_author_repeat", "record_author_post", "prune_author_store", "SOURCES_WITH_AUTHOR",
    "apply_source_weight", "load_source_weights",
    "is_sellable", "GateResult",
    "apply_recency_boost", "AGED_OUT",
]
