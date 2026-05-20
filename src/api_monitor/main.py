"""
Point d'entrée : boucle de monitoring des endpoints configurés.

Exemple :
    python -m api_monitor.main -c config.yaml
(depuis la racine du projet, avec PYTHONPATH=src)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from .alerter import AlertDispatcher
from .checker import check_endpoint
from .config import EnvSettings, load_config
from .logger import get_logger, log_check_result, setup_logging


async def run_once(cfg, alerter: AlertDispatcher, logger) -> None:
    """Exécute un tour de checks sur tous les endpoints."""
    for ep in cfg.endpoints:
        result = await check_endpoint(
            ep.name,
            str(ep.url),
            method=ep.method,
            timeout_seconds=ep.timeout_seconds,
            expected_status=ep.expected_status,
        )
        log_check_result(logger, result)
        details = (
            f"url={result.url} status={result.status_code} "
            f"latency={result.latency_ms}ms error={result.error}"
        )
        await alerter.notify(ep.name, result.ok, details)


async def run_loop(config_path: Path) -> None:
    env = EnvSettings()
    setup_logging(env.log_level)
    logger = get_logger()

    try:
        cfg = load_config(config_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Erreur de configuration : {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if not cfg.endpoints:
        print(
            "Aucun endpoint dans config.yaml — ajoutez au moins une entrée sous 'endpoints:'.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    alerter = AlertDispatcher(
        slack_webhook_url=cfg.alerts.slack_webhook_url,
        cooldown_seconds=cfg.alerts.alert_cooldown_seconds,
        enabled=cfg.alerts.enabled,
    )

    interval = min(ep.interval_seconds for ep in cfg.endpoints)
    logger.info(
        "monitor_demarre",
        interval_seconds=interval,
        endpoints=[ep.name for ep in cfg.endpoints],
    )

    while True:
        await run_once(cfg, alerter, logger)
        await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Surveillance de santé d'API (HTTP, logs JSON, alertes Slack optionnelles).",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Chemin vers le fichier YAML (défaut : config.yaml à la racine du projet)",
    )
    args = parser.parse_args()
    config_path = Path(args.config).resolve()

    try:
        asyncio.run(run_loop(config_path))
    except KeyboardInterrupt:
        print("\nArrêt demandé (Ctrl+C). Au revoir !")


if __name__ == "__main__":
    main()
