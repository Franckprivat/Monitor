"""État en mémoire par endpoint (OK / DOWN, cooldown des alertes)."""

from dataclasses import dataclass, field


@dataclass
class EndpointState:
    """Dernier état connu d'un endpoint surveillé."""

    last_ok: bool = True
    last_alert_at: float = 0.0
    consecutive_failures: int = 0


@dataclass
class MonitorState:
    """Registre de tous les endpoints."""

    endpoints: dict[str, EndpointState] = field(default_factory=dict)

    def get(self, name: str) -> EndpointState:
        if name not in self.endpoints:
            self.endpoints[name] = EndpointState()
        return self.endpoints[name]
