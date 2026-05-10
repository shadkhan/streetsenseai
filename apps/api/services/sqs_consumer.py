"""Street Manager SNS/SQS event consumer.

DfT's Street Manager Open Data publishes permit lifecycle events to an AWS SNS
topic. Registered subscribers receive those events via an SQS queue. This module
polls the queue, decodes the SNS notification envelope, and extracts the permit
reference for downstream processing.

Delivery flow:
  SM event → SNS topic (DfT-managed) → SQS queue (our account) → this consumer
       → process_sm_event Celery task → StreetManagerClient.get_work()

Prerequisites (one-off setup):
  1. Create an SQS queue in eu-west-2
  2. Register the queue ARN with DfT via the Street Manager developer portal
  3. Confirm the SNS subscription (handled automatically in poll())
  4. Set STREET_MANAGER_SQS_QUEUE_URL in .env.local
  5. Set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY (or use IAM role on EC2/ECS)
"""
from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import settings
from schemas.street_manager import SMEventPayload, SNSNotificationEnvelope

logger = logging.getLogger(__name__)

_MAX_MESSAGES = 10
_WAIT_TIME_SECONDS = 20  # long-poll — reduces empty-response API calls


class SQSConsumer:
    """Polls the Street Manager SQS queue and decodes SNS notification envelopes.

    Designed for use in Celery tasks (synchronous). The boto3 client is
    injected to allow mock substitution in tests.
    """

    def __init__(self, sqs_client: Any = None) -> None:
        self._sqs = sqs_client or boto3.client(
            "sqs",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        self._queue_url = settings.street_manager_sqs_queue_url

    # ── Queue operations ───────────────────────────────────────────────────────

    def poll(self) -> list[dict[str, Any]]:
        """Poll the SQS queue and return raw SQS message dicts (up to 10).

        Uses long-polling (WaitTimeSeconds=20) to reduce empty responses.
        Returns an empty list if the queue URL is not configured or the
        SQS call fails — never raises to the Celery task caller.
        """
        if not self._queue_url:
            logger.warning("STREET_MANAGER_SQS_QUEUE_URL not configured — skipping poll")
            return []

        try:
            response = self._sqs.receive_message(
                QueueUrl=self._queue_url,
                MaxNumberOfMessages=_MAX_MESSAGES,
                WaitTimeSeconds=_WAIT_TIME_SECONDS,
                AttributeNames=["All"],
            )
        except ClientError as exc:
            logger.error("SQS receive_message failed: %s", exc)
            return []

        return response.get("Messages", [])  # type: ignore[no-any-return]

    def delete_message(self, receipt_handle: str) -> None:
        """Delete a processed message from the queue.

        Must be called after every message, whether processing succeeded or
        failed — SQS will redeliver un-deleted messages after the visibility
        timeout expires.
        """
        if not self._queue_url:
            return
        try:
            self._sqs.delete_message(
                QueueUrl=self._queue_url,
                ReceiptHandle=receipt_handle,
            )
        except ClientError as exc:
            logger.error("SQS delete_message failed (handle=%s): %s", receipt_handle[:16], exc)

    # ── Message parsing ────────────────────────────────────────────────────────

    def decode_notification(self, sqs_message: dict[str, Any]) -> SNSNotificationEnvelope | None:
        """Parse an SQS message body into an SNS notification envelope.

        Returns None and logs a warning for malformed messages. The caller
        should still delete the message from the queue to avoid redelivery loops.
        """
        try:
            body = json.loads(sqs_message["Body"])
            return SNSNotificationEnvelope.model_validate(body)
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            logger.warning(
                "Failed to decode SQS message %s: %s",
                sqs_message.get("MessageId", "?"),
                exc,
            )
            return None

    def extract_permit_reference(self, notification: SNSNotificationEnvelope) -> str | None:
        """Extract the permit reference from an SNS notification's SM event payload.

        Handles SubscriptionConfirmation messages by logging the confirm URL.
        Returns None for non-Notification message types and for events with
        no object_reference (e.g. bulk-upload events).
        """
        if notification.Type == "SubscriptionConfirmation":
            # SNS sends this once when the subscription is first created.
            # DfT requires manual confirmation via the SubscribeURL.
            logger.info(
                "SNS SubscriptionConfirmation received — confirm at: %s",
                notification.SubscribeURL,
            )
            return None

        if notification.Type != "Notification":
            return None

        try:
            event: SMEventPayload = notification.parse_message()
        except Exception as exc:
            logger.warning(
                "Failed to parse SM event from MessageId=%s: %s",
                notification.MessageId,
                exc,
            )
            return None

        if not event.object_reference:
            logger.warning(
                "SM event %s (%s) has no object_reference",
                event.event_reference,
                event.event_type,
            )
            return None

        logger.info(
            "SM event %s: type=%s permit=%s",
            event.event_reference,
            event.event_type,
            event.object_reference,
        )
        return event.object_reference
