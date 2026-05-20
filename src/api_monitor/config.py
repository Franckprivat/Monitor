"""Chargement et validation de la configuration (YAML + variables d'environnement)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class EndpointConfig(BaseModel):
    name: str
    url: HttpUrl
    method: str = "GET"
    timeout_seconds: float = 5.0
    expected_status: int = 200
    interval_seconds: int = 60


class AlertsConfig(BaseModel):
    enabled: bool = True
    slack_webhook_url: Optional[str] = None
    alert_cooldown_seconds: int = 300


class DefaultsConfig(BaseModel):
    timeout_seconds: float = 5.0
    expected_status: int = 200
    interval_seconds: int = 60
    alert_cooldown_seconds: int = 300


class AppConfig(BaseModel):
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    endpoints: list[EndpointConfig]
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)


class EnvSettings(BaseSettings):
    """Variables lues depuis le fichier .env (à la racine du projet)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    slack_webhook_url: Optional[str] = None
    log_level: str = "INFO"


def _expand_env(value: str) -> str:
    """Remplace ${NOM_VAR} par la valeur de l'environnement."""
    if value.startswith("${") and value.endswith("}"):
        key = value[2:-1]
        return os.environ.get(key, "")
    return value


def load_config(path: Path, env_file: Path | None = None) -> AppConfig:
    """
    Charge config.yaml et fusionne les secrets depuis .env.

    Raises:
        FileNotFoundError: si le fichier YAML n'existe pas.
        ValueError: si le YAML est invalide ou vide.
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"Fichier de configuration introuvable : {path}\n"
            f"Vérifiez le chemin passé avec -c (ex. -c config.yaml depuis la racine du projet)."
        )

    if env_file is None:
        env_file = path.parent / ".env"
    if env_file.is_file():
        load_dotenv(env_file)

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not raw or not isinstance(raw, dict):
        raise ValueError(f"Le fichier {path} est vide ou n'est pas un objet YAML valide.")

    env = EnvSettings()

    alerts = raw.setdefault("alerts", {})
    webhook = alerts.get("slack_webhook_url", "")
    if isinstance(webhook, str) and webhook.startswith("${"):
        alerts["slack_webhook_url"] = env.slack_webhook_url or _expand_env(webhook) or None
    elif env.slack_webhook_url:
        alerts["slack_webhook_url"] = env.slack_webhook_url

    for ep in raw.get("endpoints", []):
        if isinstance(ep, dict):
            for key, val in list(ep.items()):
                if isinstance(val, str):
                    ep[key] = _expand_env(val)

    cfg = AppConfig.model_validate(raw)

    for ep in cfg.endpoints:
        if ep.timeout_seconds <= 0:
            ep.timeout_seconds = cfg.defaults.timeout_seconds
        if ep.interval_seconds <= 0:
            ep.interval_seconds = cfg.defaults.interval_seconds

    if cfg.alerts.alert_cooldown_seconds <= 0:
        cfg.alerts.alert_cooldown_seconds = cfg.defaults.alert_cooldown_seconds

    return cfg
