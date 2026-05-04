"""
Core CommNet signal-strength calculations.

All functions accept an optional CommNetSettings; when omitted, normal difficulty
(no modifiers) is assumed.

Distance helpers
----------------
Convenience function lets you express distances in physical terms rather than
looking up raw numbers:

    distance_orbit_to_orbit(body, altitude_m, angle_deg)
        Distance between two vessels in the same circular orbit around `body`
        separated by `angle_deg` degrees (useful for relay satellites in the same
        orbital shell).

Signal path helpers
-------------------
    compute_signal_strength(path, settings)
        High-level entry point: accepts a list of (Vessel, distance) pairs that
        describe the communication path from source to destination.  The *last*
        entry's distance is ignored (the destination vessel has no outbound hop).

        Alternatively, pass a pre-built list of (Vessel, Vessel, distance) tuples
        for explicit hop specification.

    compute_signal_strength_from_hops(hops, settings)
        Lower-level function: accepts a list of (vessel_a, vessel_b, distance_m)
        tuples representing each communication hop.
"""

from __future__ import annotations
from math import sqrt, pi, cos, acos, sin
from typing import Union
from .vessels import Vessel
from .settings import CommNetSettings, get_default_settings
from .bodies import planet_radii


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------

def distance_orbit_to_orbit(body: str, altitude_m: float, angle_deg: float) -> float:
    """
    Chord distance (m) between two vessels in the *same* circular orbit around
    `body` separated by `angle_deg` degrees.

    Parameters:
        body: Name of the celestial body (must be in planet_radii).
        altitude_m: Orbital altitude above the surface in metres.
        angle_deg: Angular separation between the two vessels (0-180 degrees).
    """
    radius = planet_radii[body] + altitude_m
    angle_rad = angle_deg * pi / 180.0
    return 2 * radius * abs(sin(angle_rad / 2))


# ---------------------------------------------------------------------------
# Core signal computation
# ---------------------------------------------------------------------------

def compute_max_range(
    vessel_a: Vessel,
    vessel_b: Vessel,
    settings: CommNetSettings | None = None,
) -> float:
    """
    Maximum communication range (m) between two vessels.

    range = sqrt(power_a * power_b)
    """
    if settings is None:
        settings = get_default_settings()
    return sqrt(vessel_a.effective_power(settings) * vessel_b.effective_power(settings))


def compute_single_hop_signal_strength(
    vessel_a: Vessel,
    vessel_b: Vessel,
    distance_m: float,
    settings: CommNetSettings | None = None,
) -> float:
    """
    Signal strength [0, 1] for a single communication hop.
    Returns 0.0 if the distance exceeds the maximum range.
    """
    max_range = compute_max_range(vessel_a, vessel_b, settings)
    if max_range <= 0 or distance_m >= max_range:
        return 0.0
    x = 1.0 - distance_m / max_range
    return -2 * x**3 + 3 * x**2


# ---------------------------------------------------------------------------
# Multi-hop helpers
# ---------------------------------------------------------------------------

Hop = tuple[Vessel, Vessel, float]  # (vessel_a, vessel_b, distance_m)

def compute_signal_strength_from_hops(
    hops: list[Hop],
    settings: CommNetSettings | None = None,
) -> float:
    """
    Compute the end-to-end signal strength as the product of per-hop strengths.

    Parameters:
        hops: List of (vessel_a, vessel_b, distance_m) tuples.
        settings: CommNetSettings to apply.

    Returns:
        Signal strength in [0, 1].
    """
    result = 1.0
    for vessel_a, vessel_b, dist in hops:
        result *= compute_single_hop_signal_strength(vessel_a, vessel_b, dist, settings)
    return result


def compute_signal_strength(
    path: list[tuple[Vessel, float]],
    settings: CommNetSettings | None = None,
) -> float:
    """
    Compute end-to-end signal strength from an ordered communication path.

    Parameters:
        path: Ordered list of (vessel, distance_to_next_vessel) pairs.
              The last vessel is the destination; its distance value is ignored.
              Must contain at least 2 entries.
        settings: CommNetSettings to apply.

    Returns:
        Signal strength in [0, 1].

    Example::

        from SignalStrength import (
            Vessel, CommNetSettings,
            direct_antennae, relay_antennae, tracking_stations,
            compute_signal_strength, distance_surface_to_orbit, distance_orbit_to_orbit,
        )

        # Build vessels
        probe = Vessel("Eve Probe").add_antenna(direct_antennae["Communotron DTS-M1"])
        relay1 = Vessel("Relay 1").add_antenna(relay_antennae["RA-15 Relay Antenna"])
        relay2 = Vessel("Relay 2").add_antenna(relay_antennae["RA-15 Relay Antenna"])
        dsn    = Vessel("DSN", is_dsn=True).add_antenna(tracking_stations["Level 3"])

        # Distances
        d1 = distance_surface_to_orbit("Eve", 500_000)          # surface → relay1
        d2 = distance_orbit_to_orbit("Eve", 500_000, angle_deg) # relay1  → relay2
        d3 = distances_to_kerbin["Eve"][1]                       # relay2  → DSN

        strength = compute_signal_strength(
            [(probe, d1), (relay1, d2), (relay2, d3), (dsn, 0)],
            settings=CommNetSettings.normal(),
        )
        print(f"Signal strength: {strength:.1%}")
    """
    if len(path) < 2:
        raise ValueError("path must contain at least 2 (vessel, distance) pairs")

    hops: list[Hop] = [
        (path[i][0], path[i + 1][0], path[i][1])
        for i in range(len(path) - 1)
    ]
    return compute_signal_strength_from_hops(hops, settings)
