"""Lead Radar AI intelligence layer.

Wraps the llm-council service so the scraper/exporter pipeline can:
  - score each scraped lead with structured JSON output
  - generate cold email + LinkedIn opener + follow-up sequence
  - persist qualified leads to the CRM store
  - fire n8n-ready webhooks for downstream automation

Public surface:
  from intelligence import enrich_leads, CouncilClient, IntelligenceConfig

The package is fully optional — if LEAD_RADAR_INTELLIGENCE_ENABLED is not
set the exporter behaves exactly as before.
"""

from .config import IntelligenceConfig, get_config
from .council_client import CouncilClient, CouncilClientError
from .crm_store import qualified_path, save_qualified
from .enrichment import EnrichmentResult, enrich_leads, enrich_one
from .webhooks import emit_webhook

__all__ = [
    "CouncilClient",
    "CouncilClientError",
    "EnrichmentResult",
    "IntelligenceConfig",
    "emit_webhook",
    "enrich_leads",
    "enrich_one",
    "get_config",
    "qualified_path",
    "save_qualified",
]
