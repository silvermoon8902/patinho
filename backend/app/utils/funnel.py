"""
Lightweight funnel/event logging.

Emits structured one-line JSON to the backend logger so Daniel (or any
operator) can `docker logs ... | grep '"funnel"'` to inspect drop-off
points without standing up a separate analytics service. Cheap, no
schema, no third-party SDK. When we're past the early-test phase we can
upgrade this to a real events table or pipe it to PostHog/Plausible.
"""
from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger("patinho.funnel")


def track(
    event: str,
    user_id: UUID | str | None = None,
    **payload: Any,
) -> None:
    """Record one funnel event. Never raises."""
    try:
        record = {
            "funnel": event,
            "user_id": str(user_id) if user_id else None,
            **payload,
        }
        logger.info(json.dumps(record, default=str))
    except Exception:
        # Funnel tracking must never break a real request.
        logger.warning("funnel.track failed for event=%s", event)
