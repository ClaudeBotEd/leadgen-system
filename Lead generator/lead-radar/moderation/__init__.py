"""Lead Radar moderation layer.

The AI side of the trust-provenance-moderation doctrine. Wraps the
`services/llm-council` moderation endpoint so the scraper/exporter
pipeline can:

  - submit each captured public post to council moderation
  - persist APPROVED leads (HOT + verified + high confidence + no flags)
    to data/moderation/approved_leads.jsonl
  - fire `event: lead.approved` webhooks for downstream automation

The package is fully optional — if LEAD_RADAR_MODERATION_ENABLED is not
set the exporter behaves exactly as before. There is no outreach
generation: copy is humans-only.
"""

from .config import ModerationConfig, get_config
from .council_client import CouncilClient, CouncilClientError
from .crm_store import approved_path, evaluate_approval, save_approved
from .moderation import (
    ModerationResult,
    ModerationSummary,
    moderate_one,
    moderate_posts,
)
from .webhooks import emit_webhook

__all__ = [
    "CouncilClient",
    "CouncilClientError",
    "ModerationConfig",
    "ModerationResult",
    "ModerationSummary",
    "approved_path",
    "emit_webhook",
    "evaluate_approval",
    "get_config",
    "moderate_one",
    "moderate_posts",
    "save_approved",
]
