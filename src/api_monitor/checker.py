"""Vérifications HTTP de santé (latence, code status, erreurs réseau)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class CheckResult:
    """Résultat d'un check sur un endpoint."""

    name: str
    url: str
    ok: bool
    status_code: Optional[int]
    latency_ms: float
    error: Optional[str] = None


async def check_endpoint(
    name: str,
    url: str,
    *,
    method: str = "GET",
    timeout_seconds: float = 5.0,
    expected_status: int = 200,
) -> CheckResult:
    """
    Effectue une requête HTTP et vérifie le code de réponse.

    Args:
        name: identifiant lisible (ex. api-prod)
        url: URL à appeler
        method: GET par défaut
        timeout_seconds: délai max avant échec « timeout »
        expected_status: code HTTP attendu (souvent 200)
    """
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.request(method, str(url))
        latency_ms = (time.perf_counter() - start) * 1000
        ok = response.status_code == expected_status
        error = None
        if not ok:
            error = f"status {response.status_code} != {expected_status}"
        return CheckResult(
            name=name,
            url=str(url),
            ok=ok,
            status_code=response.status_code,
            latency_ms=round(latency_ms, 2),
            error=error,
        )
    except httpx.TimeoutException:
        latency_ms = (time.perf_counter() - start) * 1000
        return CheckResult(
            name=name,
            url=str(url),
            ok=False,
            status_code=None,
            latency_ms=round(latency_ms, 2),
            error="timeout",
        )
    except httpx.HTTPError as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return CheckResult(
            name=name,
            url=str(url),
            ok=False,
            status_code=None,
            latency_ms=round(latency_ms, 2),
            error=str(exc),
        )
