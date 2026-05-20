"""Configuration des logs structurés en JSON (structlog)."""

from __future__ import annotations

import logging
import sys

import structlog

from .checker import CheckResult


def setup_logging(level: str = "INFO") -> None:
    """Active les logs JSON sur la sortie standard."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger():
    return structlog.get_logger()


def log_check_result(logger, result: CheckResult) -> None:
    """Enregistre un événement health_check avec tous les champs utiles."""
    logger.info(
        "health_check",
        endpoint=result.name,
        url=result.url,
        ok=result.ok,
        status_code=result.status_code,
        latency_ms=result.latency_ms,
        error=result.error,
    )
