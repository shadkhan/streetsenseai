"""Pydantic schemas matching the Street Manager Open Data API v7 response shapes
and the AWS SNS/SQS notification envelope used for event delivery.

These are external-API shapes — not domain models. The services layer normalises
them into the domain types defined in schemas/domain.py.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SMGeometry(BaseModel):
    """GeoJSON geometry as returned by the Street Manager API."""

    type: str
    coordinates: list[Any]


class SMPermitV7(BaseModel):
    """Single permit object from the Street Manager API v7.

    Field names match the API v7 JSON keys exactly.
    Only the fields required for the domain StreetWork model are declared;
    unknown fields are ignored via model_config.
    """

    model_config = {"extra": "ignore"}

    permit_reference_number: str
    works_reference_number: str = ""
    usrn: str = ""
    street_name: str = ""
    area_name: str = ""  # highway authority
    promoter_organisation: str = ""
    promoter_swa_code: str = ""  # promoter licence number
    work_category: str = ""
    traffic_management_type: str = ""
    restriction_type: str = ""
    proposed_start_date: str = ""
    proposed_end_date: str = ""
    actual_start_date_time: str | None = None
    actual_end_date_time: str | None = None
    permit_status: str = "submitted"
    geometry: SMGeometry | None = None


class SMWorksListV7(BaseModel):
    """Paginated works list from GET /works."""

    works: list[SMPermitV7] = Field(default_factory=list)
    pagination_cursor: str | None = None
    total: int | None = None


class SMEventPayload(BaseModel):
    """Street Manager event notification — the inner payload within an SNS message.

    Published when a permit lifecycle event occurs (work start, work stop,
    permit granted, etc.).
    """

    event_reference: int
    event_type: str
    object_type: str | None = None
    object_reference: str | None = None  # permit_reference_number
    event_time: datetime


class SNSNotificationEnvelope(BaseModel):
    """AWS SNS notification envelope as delivered to an SQS queue.

    DfT's Street Manager SNS topic wraps each SM event in this standard
    SNS envelope. The inner SM payload is a JSON string in the Message field.
    """

    model_config = {"extra": "ignore"}

    Type: Literal["Notification", "SubscriptionConfirmation", "UnsubscribeConfirmation"]
    MessageId: str
    TopicArn: str
    Message: str  # JSON-encoded string; use parse_message() to decode
    Timestamp: datetime
    Signature: str | None = None
    SigningCertURL: str | None = None
    SubscribeURL: str | None = None  # present on SubscriptionConfirmation only

    def parse_message(self) -> SMEventPayload:
        return SMEventPayload.model_validate_json(self.Message)
