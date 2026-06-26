from echoloop.types import CEFR_LEVELS_TYPE

# The six CEFR levels ordered from easiest to hardest.
CEFR_LEVELS: tuple[CEFR_LEVELS_TYPE, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")

# SM-2 easiness-factor lower bound.
_MIN_EF: float = 1.3
