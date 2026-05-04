"""
Ideas (for later)
* tool-tips on hover. e.g. when hovering over "combinability," say that this affects how well multiple antennae combine together, which can increase the total power beyond just the sum of the parts.

Hand-calculate:
"""

from flask import Flask, render_template, request
import json
from math import prod

from SignalStrength import (
    Vessel,
    DSN,
    direct_antennae as _direct_antennae,
    relay_antennae as _relay_antennae,
    tracking_stations,
    distances_to_kerbin,
    CommNetSettings,
    Difficulty,
)
from SignalStrength.antennae import Antenna
from SignalStrength.commnet import (
    compute_single_hop_signal_strength,
    compute_max_range,
    distance_orbit_to_orbit,
)
from SignalStrength.bodies import planet_radii

app = Flask(__name__)

bodies = list(planet_radii.keys())


def _fmt_power(power: float) -> str:
    if power >= 1e9:
        return f"{power/1e9:g} G"
    if power >= 1e6:
        return f"{power/1e6:g} M"
    if power >= 1e3:
        return f"{power/1e3:g} k"
    return f"{power:g}"


# Pre-built antenna option list passed to the template for building dropdowns
antenna_options = (
    [{"value": f"relay:{name}", "label": f"{name} ({_fmt_power(a.power)})", "group": "Relay", "power": a.power, "combinability": a.combinability}
     for name, a in _relay_antennae.items()]
    + [{"value": f"direct:{name}", "label": f"{name} ({_fmt_power(a.power)})", "group": "Direct", "power": a.power, "combinability": a.combinability}
       for name, a in _direct_antennae.items()]
)


UNIT_TO_M = {"m": 1, "km": 1_000, "au": 13_599_840_256}


def _dsn(level: int) -> DSN:
    key = f"Level {level}"
    antenna = tracking_stations[key]
    labeled = Antenna(f"Level {level} Tracking Station", antenna.power, antenna.combinability)
    return DSN(f"DSN {key}").add_antenna(labeled)


def _describe_vessel(v) -> str:
    return ", ".join(a.name for a in v.antennae) or "(no antennae)"


def _parse_vessel(prefix: str, form) -> Vessel | DSN:
    """Build a Vessel or DSN from prefixed form fields."""
    vessel_type = form.get(f"{prefix}_type", "direct")

    if vessel_type == "dsn":
        level = int(form.get(f"{prefix}_dsn_level", 3))
        return _dsn(level)

    # both "direct" and "relay" vessel types map to Vessel
    vessel = Vessel(prefix)
    try:
        antenna_list = json.loads(form.get(f"{prefix}_antenna_data", "[]"))
    except (json.JSONDecodeError, ValueError):
        antenna_list = []

    if len(antenna_list) > 10:
        raise ValueError(f"Too many antennae for {prefix} (max 10)")

    for entry in antenna_list:
        source = entry.get("source", "none")
        if source.startswith("relay:"):
            name = source[6:]
            if name not in _relay_antennae:
                raise ValueError(f"Unknown relay antenna: {name!r}")
            vessel.add_antenna(_relay_antennae[name])
        elif source.startswith("direct:"):
            name = source[7:]
            if name not in _direct_antennae:
                raise ValueError(f"Unknown direct antenna: {name!r}")
            vessel.add_antenna(_direct_antennae[name])
        elif source in ("custom_relay", "custom_direct"):
            power_unit = float(entry.get("power_unit", 1))
            power = float(entry.get("power", 0)) * power_unit
            combinability = float(entry.get("combinability", 0.75))
            label = "Custom (Relay)" if source == "custom_relay" else "Custom (Direct)"
            vessel.add_antenna(Antenna(label, power, combinability))

    if not vessel.antennae:
        raise ValueError(f"Vessel {prefix!r} has no antennae")

    return vessel


def _parse_settings(form) -> CommNetSettings:
    """Build CommNetSettings from form fields."""
    difficulty = form.get("difficulty", "normal")
    if difficulty == "easy":
        return CommNetSettings(Difficulty.EASY)
    elif difficulty == "normal":
        return CommNetSettings(Difficulty.NORMAL)
    elif difficulty == "moderate":
        return CommNetSettings(Difficulty.MODERATE)
    elif difficulty == "hard":
        return CommNetSettings(Difficulty.HARD)
    elif difficulty == "custom":
        try:
            rm = float(form.get("custom_range_modifier", 1.0))
        except ValueError:
            raise ValueError("Custom range modifier must be a number")
        if not 0 < rm <= 1:
            raise ValueError("Custom range modifier must be between 0 and 1")
        return CommNetSettings(Difficulty.CUSTOM, range_modifier=rm)
    else:
        raise ValueError(f"Unknown difficulty: {difficulty!r}")


def _parse_hop_distance(idx: int, form):
    """Return (label, dist_best_m, dist_worst_m) for hop index idx."""
    hop_type = form.get(f"hop{idx}_type")

    if hop_type == "surface_to_orbit":
        body = form.get(f"hop{idx}_sto_body", "")
        alt_raw = float(form.get(f"hop{idx}_sto_altitude", 100_000))
        alt_unit = form.get(f"hop{idx}_sto_alt_unit", "m")
        if alt_unit not in UNIT_TO_M:
            raise ValueError(f"Unknown altitude unit: {alt_unit!r}")
        altitude = alt_raw * UNIT_TO_M[alt_unit]
        return f"{body} surface → orbit at {altitude/1000:.0f} km", altitude, altitude

    elif hop_type == "orbit_to_orbit":
        body = form.get(f"hop{idx}_oto_body", "")
        alt_raw = float(form.get(f"hop{idx}_oto_altitude", 100_000))
        alt_unit = form.get(f"hop{idx}_oto_alt_unit", "m")
        if alt_unit not in UNIT_TO_M:
            raise ValueError(f"Unknown altitude unit: {alt_unit!r}")
        altitude = alt_raw * UNIT_TO_M[alt_unit]
        angle = float(form.get(f"hop{idx}_oto_angle") or 120)
        dist = distance_orbit_to_orbit(body, altitude, angle)
        return f"{body} orbit at {altitude/1000:.0f} km, {angle:.1f}° sep.", dist, dist

    elif hop_type == "body_to_dsn":
        body = form.get(f"hop{idx}_dsn_body", "")
        if body not in distances_to_kerbin:
            raise ValueError(f"No distance data for {body!r}")
        min_dist, max_dist = distances_to_kerbin[body]
        return f"{body} → Kerbin", min_dist, max_dist

    elif hop_type == "raw_distance":
        raw = float(form.get(f"hop{idx}_rd_distance", 1))
        unit = form.get(f"hop{idx}_rd_unit", "km")
        if unit not in UNIT_TO_M:
            raise ValueError(f"Unknown unit: {unit!r}")
        dist = raw * UNIT_TO_M[unit]
        return f"Raw distance: {raw:g} {unit}", dist, dist

    else:
        raise ValueError(f"Unknown hop type for hop {idx + 1}: {hop_type!r}")


def _render(results=None, error=None, form_state=None):
    return render_template(
        "index.html",
        bodies=bodies,
        dsn_levels=[1, 2, 3],
        antenna_options=antenna_options,
        planet_radii=planet_radii,
        results=results,
        error=error,
        form_state=form_state or {},
    )


@app.get("/")
def index_get():
    return _render()


@app.post("/")
def index_post():
    f = request.form
    form_state = f.to_dict()

    try:
        settings = _parse_settings(f)
        num_hops = int(f.get("num_hops", 1))
        if not 1 <= num_hops <= 5:
            raise ValueError("Number of hops must be between 1 and 5")

        vessels = [_parse_vessel(f"v{i}", f) for i in range(num_hops + 1)]

        hop_results = []
        for i in range(num_hops):
            label, dist_best, dist_worst = _parse_hop_distance(i, f)
            va, vb = vessels[i], vessels[i + 1]
            max_range = compute_max_range(va, vb, settings)
            signal_best = compute_single_hop_signal_strength(va, vb, dist_best, settings)
            signal_worst = compute_single_hop_signal_strength(va, vb, dist_worst, settings)
            hop_results.append({
                "label": label,
                "vessel_a": _describe_vessel(va),
                "vessel_b": _describe_vessel(vb),
                "max_range_mm": max_range / 1e6,
                "signal_best": signal_best,
                "signal_worst": signal_worst,
                "is_range": dist_best != dist_worst,
                "dist_best_mm": dist_best / 1e6,
                "dist_worst_mm": dist_worst / 1e6,
            })

        agg_best = prod(h["signal_best"] for h in hop_results)
        agg_worst = prod(h["signal_worst"] for h in hop_results)
        results = {
            "hops": hop_results,
            "aggregate": {
                "signal_best": agg_best,
                "signal_worst": agg_worst,
                "has_range": any(h["is_range"] for h in hop_results),
            },
        }

    except (KeyError, ValueError) as e:
        return _render(error=str(e), form_state=form_state), 400

    return _render(results=results, form_state=form_state)


if __name__ == "__main__":
    app.run(debug=True)
