from __future__ import annotations

from ai_impact_research.db.models import CANONICAL_TABLES, MODEL_REQUIRED_COLUMNS

CORE_TABLES = {table: sorted(MODEL_REQUIRED_COLUMNS[table]) for table in CANONICAL_TABLES}
