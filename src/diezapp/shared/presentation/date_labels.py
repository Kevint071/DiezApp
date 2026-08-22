"""Spanish date/time labels for the UI.

Kept out of ``datetime_utils`` because these are presentation strings, and out
of the system locale because Flet runs on platforms where ``es`` may not be
installed.
"""

from datetime import datetime, timedelta

from diezapp.shared.datetime_utils import local_now

MONTHS_SHORT = (
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
)
MONTHS_LONG = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
WEEKDAYS_SHORT = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")


def relative_label(value: datetime, now: datetime | None = None) -> str:
    """Human "hace X" label. Coarse on purpose: exactness lives in the full date."""
    now = now or local_now()
    seconds = (now - value).total_seconds()
    if seconds < 60:
        return "hace un momento"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"hace {minutes} min"
    hours = int(seconds // 3600)
    if hours < 24:
        return f"hace {hours} h"
    days = (now.date() - value.date()).days
    if days == 1:
        return "ayer"
    if days < 7:
        return f"hace {days} días"
    if days < 30:
        weeks = max(1, days // 7)
        return "hace 1 semana" if weeks == 1 else f"hace {weeks} semanas"
    if days < 365:
        months = max(1, days // 30)
        return "hace 1 mes" if months == 1 else f"hace {months} meses"
    years = max(1, days // 365)
    return "hace 1 año" if years == 1 else f"hace {years} años"


def period_label(value: datetime, now: datetime | None = None) -> str:
    """Bucket a datetime into the section header it belongs to."""
    now = now or local_now()
    today = now.date()
    day = value.date()
    if day == today:
        return "Hoy"
    if day == today - timedelta(days=1):
        return "Ayer"
    if (today - day).days < 7:
        return "Esta semana"
    if (day.year, day.month) == (today.year, today.month):
        return "Este mes"
    if day.year == today.year:
        return MONTHS_LONG[day.month - 1].capitalize()
    return f"{MONTHS_LONG[day.month - 1].capitalize()} {day.year}"


def short_date(value: datetime) -> str:
    """e.g. ``mié 11 feb``."""
    return (
        f"{WEEKDAYS_SHORT[value.weekday()]} {value.day} {MONTHS_SHORT[value.month - 1]}"
    )


def full_date(value: datetime) -> str:
    """e.g. ``11 de febrero de 2026``."""
    return f"{value.day} de {MONTHS_LONG[value.month - 1]} de {value.year}"


def clock(value: datetime) -> str:
    return value.strftime("%H:%M")
