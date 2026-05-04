from __future__ import annotations
from .antennae import Antenna
from .settings import CommNetSettings, get_default_settings


class GenericVessel:
    """
    Base class for any node in a CommNet communication path.

    Subclasses must implement `effective_power` to apply the appropriate
    game-settings modifier for their vessel type.

    Attributes:
        name: Human-readable name.
        antennae: List of fitted antennae.
    """

    def __init__(self, name: str):
        self.name = name
        self.antennae: list[Antenna] = []

    def add_antenna(self, antenna: Antenna) -> "GenericVessel":
        """Add an antenna to this vessel. Returns self for chaining."""
        self.antennae.append(antenna)
        return self

    def _compute_power(self, modifier: float = 1.0) -> float:
        """Vessel power with each antenna's power scaled by `modifier` before combining."""
        if not self.antennae:
            return 0.0
        scaled = [a.power * modifier for a in self.antennae]
        strongest = max(scaled)
        total = sum(scaled)
        ace = sum(a.combinability * p for a, p in zip(self.antennae, scaled)) / total
        return strongest * (total / strongest) ** ace

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r}, antennae={[a.name for a in self.antennae]})"


class Vessel(GenericVessel):
    """
    A probe or crewed spacecraft.

    Antenna power is scaled by the range modifier from CommNetSettings
    (1.0 on normal, 0.8 on moderate, 0.65 on hard).
    """

    def effective_power(self, settings: CommNetSettings | None = None) -> float:
        if settings is None:
            settings = get_default_settings()
        return self._compute_power(settings.range_modifier)


class DSN(GenericVessel):
    """
    A Deep Space Network ground station (tracking station).

    Antenna power is scaled by the DSN modifier from CommNetSettings
    and is unaffected by the range modifier.
    """
    def effective_power(self, settings: CommNetSettings | None = None) -> float:
        if settings is None:
            settings = get_default_settings()
        return self._compute_power(settings.dsn_modifier)
