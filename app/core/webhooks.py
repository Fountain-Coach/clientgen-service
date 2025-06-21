import asyncio
import logging
from typing import Dict
from pydantic import HttpUrl
import httpx
import backoff

logger = logging.getLogger(__name__)

class WebhookManager:
    def __init__(self):
        self._webhooks: Dict[str, HttpUrl] = {}
        self._sent_notifications = []  # store sent payloads for test inspection

    def add_webhook(self, webhook_id: str, callback_url: HttpUrl):
        self._webhooks[webhook_id] = callback_url
        logger.info(f"Webhook added: {webhook_id} -> {callback_url}")

    def remove_webhook(self, webhook_id: str) -> bool:
        removed = self._webhooks.pop(webhook_id, None) is not None
        if removed:
            logger.info(f"Webhook removed: {webhook_id}")
        else:
            logger.warning(f"Attempted to remove nonexistent webhook: {webhook_id}")
        return removed

    def get_webhooks(self) -> Dict[str, HttpUrl]:
        return dict(self._webhooks)

    def get_sent_notifications(self):
        return list(self._sent_notifications)

    def clear_sent_notifications(self):
        self._sent_notifications.clear()

    @backoff.on_exception(
        backoff.expo,
        (httpx.RequestError, httpx.HTTPStatusError),
        max_tries=5,
        jitter=backoff.full_jitter,
        on_backoff=lambda details: logger.warning(
            f"Backing off webhook POST to {details['args'][1]} after {details['tries']} tries"
        )
    )
    async def _post_webhook(self, client: httpx.AsyncClient, url: str, data: dict):
        logger.debug(f"Sending webhook POST to {url}")
        response = await client.post(url, json=data, timeout=10.0)
        response.raise_for_status()
        logger.info(f"Webhook POST successful: {url} [{response.status_code}]")

    async def notify_webhooks(self, event_data: dict):
        if not self._webhooks:
            logger.info("No webhooks registered; skipping notification.")
            return

        async with httpx.AsyncClient() as client:
            tasks = []
            for webhook_id, url in self._webhooks.items():
                task = asyncio.create_task(
                    self._notify_single(client, webhook_id, str(url), event_data)
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for webhook_id, result in zip(self._webhooks.keys(), results):
                if isinstance(result, Exception):
                    logger.error(f"Webhook notification failed for {webhook_id}: {result}")
                else:
                    self._sent_notifications.append({
                        "webhook_id": webhook_id,
                        "url": self._webhooks[webhook_id],
                        "payload": event_data
                    })

    async def _notify_single(self, client: httpx.AsyncClient, webhook_id: str, url: str, data: dict):
        try:
            await self._post_webhook(client, url, data)
        except Exception as e:
            logger.error(f"Notification to webhook {webhook_id} at {url} failed: {e}")

webhook_manager = WebhookManager()
