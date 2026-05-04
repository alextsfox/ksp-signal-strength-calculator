from dataclasses import dataclass, field
from enum import Enum


@dataclass
class Antenna:
    name: str
    power: float
    combinability: float = 0.75


relay_antennae: dict[str, Antenna] = {
    "HG-5 High Gain Antenna": Antenna("HG-5 High Gain Antenna", 5e6, 0.75),
    "RA-2 Relay Antenna": Antenna("RA-2 Relay Antenna", 2e9, 0.75),
    "RA-15 Relay Antenna": Antenna("RA-15 Relay Antenna", 15e9, 0.75),
    "RA-100 Relay Antenna": Antenna("RA-100 Relay Antenna", 100e9, 0.75),
}

direct_antennae: dict[str, Antenna] = {
    "Communotron 16": Antenna("Communotron 16", 500e3, 1.00),
    "Communotron 16-S": Antenna("Communotron 16-S", 500e3, 0.00),
    "Communotron DTS-M1": Antenna("Communotron DTS-M1", 2e9, 0.75),
    "Communotron HG-55": Antenna("Communotron HG-55", 15e9, 0.75),
    "Communotron 88-88": Antenna("Communotron 88-88", 100e9, 0.75),
}

tracking_stations: dict[str, Antenna] = {
    "Level 1": Antenna("Level 1", 2e9),
    "Level 2": Antenna("Level 2", 50e9),
    "Level 3": Antenna("Level 3", 250e9),
}
