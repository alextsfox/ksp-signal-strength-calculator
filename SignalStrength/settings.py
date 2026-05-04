from enum import Enum


class Difficulty(Enum):
    EASY = "easy"
    NORMAL = "normal"
    MODERATE = "moderate"
    HARD = "hard"
    CUSTOM = "custom"


class CommNetSettings:
    """
    Global CommNet settings that affect signal calculations.

    Attributes:
        range_modifier: Multiplier applied to non-DSN antenna power before computing vessel power.
            - Easy/Normal: 1.0
            - Moderate: 0.8
            - Hard: 0.65
            - Custom: user-supplied value
        dsn_modifier: Multiplier applied to DSN (tracking station) power. Default 1.0.
    """

    _RANGE_MODIFIERS: dict[Difficulty, float] = {
        Difficulty.EASY: 1.0,
        Difficulty.NORMAL: 1.0,
        Difficulty.MODERATE: 0.8,
        Difficulty.HARD: 0.65,
    }

    def __init__(
        self,
        difficulty: Difficulty = Difficulty.NORMAL,
        range_modifier: float | None = None,
        dsn_modifier: float = 1.0,
    ):
        """
        Parameters:
            difficulty: Preset difficulty level. If CUSTOM, range_modifier must be provided.
            range_modifier: Override for the range modifier (required when difficulty=CUSTOM).
            dsn_modifier: Scale factor for DSN (tracking station) power. Defaults to 1.0.
        """
        if difficulty == Difficulty.CUSTOM:
            if range_modifier is None:
                raise ValueError("range_modifier must be provided when difficulty is CUSTOM")
            self.range_modifier = range_modifier
        else:
            self.range_modifier = self._RANGE_MODIFIERS[difficulty]

        self.dsn_modifier = dsn_modifier

    @classmethod
    def normal(cls) -> "CommNetSettings":
        return cls(Difficulty.NORMAL)

    @classmethod
    def moderate(cls) -> "CommNetSettings":
        return cls(Difficulty.MODERATE)

    @classmethod
    def hard(cls) -> "CommNetSettings":
        return cls(Difficulty.HARD)


# ---------------------------------------------------------------------------
# Module-level default
# ---------------------------------------------------------------------------

_default_settings: CommNetSettings = CommNetSettings.normal()


def get_default_settings() -> CommNetSettings:
    """Return the current module-level default CommNetSettings."""
    return _default_settings


def set_default_settings(settings: CommNetSettings) -> None:
    """
    Set the module-level default CommNetSettings used whenever an explicit
    ``settings`` argument is omitted.

    Example::

        from SignalStrength.settings import set_default_settings, CommNetSettings
        set_default_settings(CommNetSettings.hard())
    """
    global _default_settings
    _default_settings = settings
