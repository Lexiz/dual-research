"""Spec 0036 — per-turn web-search audit data layer.

Provider-neutral schema, normalisers (Anthropic + OpenAI), and validation
rules. Downstream consumers (the aggregator, the UI server, tests) read
from this module; raw provider responses never escape ``normalize``.
"""

from dual_research.audit.normalize import (
    normalize_anthropic_search_audit,
    normalize_openai_search_audit,
)
from dual_research.audit.schema import (
    Citation,
    ConsultedSource,
    ToolEvent,
    TurnSearchAudit,
    TurnSearchFlags,
    audit_from_dict,
    audit_to_dict,
)
from dual_research.audit.validate import (
    normalize_url,
    validate_search_audit,
)

__all__ = [
    "Citation",
    "ConsultedSource",
    "ToolEvent",
    "TurnSearchAudit",
    "TurnSearchFlags",
    "audit_from_dict",
    "audit_to_dict",
    "normalize_anthropic_search_audit",
    "normalize_openai_search_audit",
    "normalize_url",
    "validate_search_audit",
]
