"""Tests simples du module checker."""

import pytest

from api_monitor.checker import check_endpoint


@pytest.mark.asyncio
async def test_httpbin_status_200():
    """Vérifie qu'une URL publique répond avec le code attendu."""
    result = await check_endpoint(
        "httpbin-test",
        "https://httpbin.org/status/200",
        timeout_seconds=10.0,
        expected_status=200,
    )
    assert result.ok is True
    assert result.status_code == 200
    assert result.error is None
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_wrong_status_detected():
    """Un mauvais code HTTP doit marquer le check en échec."""
    result = await check_endpoint(
        "httpbin-404",
        "https://httpbin.org/status/404",
        timeout_seconds=10.0,
        expected_status=200,
    )
    assert result.ok is False
    assert result.status_code == 404
    assert "404" in (result.error or "")
