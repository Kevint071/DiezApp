"""Card colours a note can wear in the list (stored as the key)."""

# key: (label, light theme, dark theme). On light pastels the theme's muted
# grey drops under 4.5:1, so coloured cards use a darker one (note_muted).
NOTE_COLORS: dict[str, tuple[str, str, str]] = {
    "red": ("Rojo", "#FDE2E1", "#4A1F1F"),
    "orange": ("Naranja", "#FFEDD5", "#45290F"),
    "yellow": ("Amarillo", "#FEF3C7", "#3D340E"),
    "green": ("Verde", "#DCFCE7", "#14382A"),
    "teal": ("Turquesa", "#CCFBF1", "#113936"),
    "blue": ("Azul", "#DBEAFE", "#1A2C4E"),
    "purple": ("Morado", "#EDE9FE", "#2D2350"),
    "pink": ("Rosa", "#FCE7F3", "#451B35"),
}


def note_bgcolor(key: str | None, light: bool, default: str) -> str:
    """The card background for a colour key; unknown keys fall back."""
    entry = NOTE_COLORS.get(key or "")
    if entry is None:
        return default
    return entry[1] if light else entry[2]


# slate-600: >= 6:1 on every light pastel above.
_MUTED_ON_LIGHT_COLOR = "#475569"


def note_muted(key: str | None, light: bool, default: str) -> str:
    """Secondary text (date, preview) on a card of that colour."""
    if light and key in NOTE_COLORS:
        return _MUTED_ON_LIGHT_COLOR
    return default
