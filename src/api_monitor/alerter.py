"""Envoi d'alertes Slack avec anti-spam (cooldown) et notification de reprise."""

from __future__ import annotations

import time
from typing import Optional

import httpx
import structlog

from .state import MonitorState

logger = structlog.get_logger()


class AlertDispatcher:
    """Décide quand alerter et envoie les messages Slack si configuré."""

    def __init__(
        self,
        *,
        slack_webhook_url: Optional[str],
        cooldown_seconds: int = 300,
        enabled: bool = True,
    ):
        self.slack_webhook_url = (slack_webhook_url or "").strip() or None
        self.cooldown_seconds = cooldown_seconds
        self.enabled = enabled
        self.state = MonitorState()

        if self.enabled and not self.slack_webhook_url:
            logger.info(
                "alertes_slack_desactivees",
                raison="SLACK_WEBHOOK_URL non défini — les checks continuent sans alerte.",
            )

    def should_alert(self, name: str, ok: bool) -> tuple[bool, Optional[str]]:
        """
        Retourne (envoyer_alerte?, type).

        type peut être 'down' (panne), 'recovery' (retour OK), ou None.
        """
        st = self.state.get(name)
        now = time.time()

        if ok:
            if not st.last_ok:
                st.last_ok = True
                st.consecutive_failures = 0
                return True, "recovery"
            st.last_ok = True
            return False, None

        st.consecutive_failures += 1
        if st.last_ok:
            st.last_ok = False
            st.last_alert_at = now
            return True, "down"

        if now - st.last_alert_at >= self.cooldown_seconds:
            st.last_alert_at = now
            return True, "down"

        return False, None

    async def send_slack(self, text: str) -> None:
        if not self.enabled or not self.slack_webhook_url:
            return
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    self.slack_webhook_url,
                    json={"text": text},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("echec_envoi_slack", erreur=str(exc))

    async def notify(self, name: str, ok: bool, details: str) -> None:
        send, kind = self.should_alert(name, ok)
        if not send:
            return
        if kind == "down":
            msg = f":red_circle: *DOWN* `{name}`\n{details}"
        else:
            msg = f":green_circle: *RECOVERY* `{name}`\n{details}"
        await self.send_slack(msg)
