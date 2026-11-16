"""Card colours a note can wear in the list (stored as the key)."""

# key: (label, light theme, dark theme). The dark shades are saturated enough
# to read as their colour on a dark screen, and still dark enough for the
# light card text (title >= 7:1, date and preview >= 4.5:1).
NOTE_COLORS: dict[str, tuple[str, str, str]] = {
    "red": ("Rojo", "#FDE2E1", "#8F1D2C"),
    "orange": ("Naranja", "#FFEDD5", "#88350E"),
    "yellow": ("Amarillo", "#FEF3C7", "#6E4B05"),
    "green": ("Verde", "#DCFCE7", "#155C33"),
    "teal": ("Turquesa", "#CCFBF1", "#0F5A55"),
    "blue": ("Azul", "#DBEAFE", "#1E40AF"),
    "purple": ("Morado", "#EDE9FE", "#5B21B6"),
    "pink": ("Rosa", "#FCE7F3", "#8E1D57"),
}

# Secondary text on a card, coloured or not. The theme's muted grey looks
# washed out on the cards (and drops under 4.5:1 on the light pastels).
_MUTED = {True: "#475569", False: "#CBD5E1"}  # slate-600 / slate-300
_PREVIEW = {True: "#334155", False: "#E2E8F0"}  # slate-700 / slate-200


def note_bgcolor(key: str | None, light: bool, default: str) -> str:
    """The card background for a colour key; unknown keys fall back."""
    entry = NOTE_COLORS.get(key or "")
    if entry is None:
        return default
    return entry[1] if light else entry[2]


def note_muted(light: bool) -> str:
    """The date and the menu icon on a card."""
    return _MUTED[light]


def note_preview(light: bool) -> str:
    """The text preview under a note's title."""
    return _PREVIEW[light]
