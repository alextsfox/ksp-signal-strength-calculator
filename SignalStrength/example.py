"""
Example: Eve surface probe → relay orbit 1 → relay orbit 2 → Kerbin DSN

Setup:
  - Eve Probe on Eve's surface with a Communotron 16-S
  - Relay 1: RA-15 in a 500 km orbit above Eve
  - Relay 2: RA-15 in the same orbit, with LOS to Kerbin
             (Eve radius = 700 km, so max orbit-to-orbit distance ≈ 2400 km)
  - Kerbin DSN Level 3 tracking station
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from SignalStrength import (
    Vessel,
    DSN,
    CommNetSettings,
    direct_antennae,
    relay_antennae,
    tracking_stations,
    compute_signal_strength,
    distances_to_kerbin,
)
from SignalStrength.commnet import (
    distance_orbit_to_orbit,
    compute_max_range,
)

settings = CommNetSettings.normal()

# ── Vessels ────────────────────────────────────────────────────────────────
probe = Vessel("Eve Probe").add_antenna(direct_antennae["Communotron 16-S"])
d_surface_to_relay = 15e6
relay1 = Vessel("Relay 1 (500 km orbit)").add_antenna(relay_antennae["RA-15 Relay Antenna"])
d_relay_to_relay = distance_orbit_to_orbit("Eve", 15e6, angle_deg=120)
relay2 = Vessel("Relay 2 (500 km orbit, LOS Kerbin)").add_antenna(relay_antennae["RA-15 Relay Antenna"])
d_relay_to_kerbin = distances_to_kerbin["Eve"][1]  # worst case (maximum distance)
dsn = DSN("Kerbin DSN Lv2").add_antenna(tracking_stations["Level 3"])

path = [
    (probe,  d_surface_to_relay),
    (relay1, d_relay_to_relay),
    (relay2, d_relay_to_kerbin),
    (dsn,    0),  # destination — distance ignored
]

strength = compute_signal_strength(path, settings)

# ── Results ────────────────────────────────────────────────────────────────
print("=== Communication path ===")
vessels = [probe, relay1, relay2, dsn]
distances = [d_surface_to_relay, d_relay_to_relay, d_relay_to_kerbin]
labels = ["Eve surface → Relay 1", "Relay 1 → Relay 2", "Relay 2 → Kerbin DSN"]

for label, va, vb, dist in zip(labels, vessels, vessels[1:], distances):
    max_r = compute_max_range(va, vb, settings)
    from SignalStrength.commnet import compute_single_hop_signal_strength
    hop_strength = compute_single_hop_signal_strength(va, vb, dist, settings)
    print(f"  {label}")
    print(f"    Distance  : {dist/1e6:,.3f} Mm")
    print(f"    Max range : {max_r/1e6:,.3f} Mm")
    print(f"    Hop strength: {hop_strength:.1%}")

print()
print(f"End-to-end signal strength: {strength:.1%}")
