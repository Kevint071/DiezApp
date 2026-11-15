"""The dated table a note can embed (a Quill block embed of type ``ledger``).

The Delta stores it as ``{"insert": {"ledger": "<json>"}}``, where the JSON is
``{"date": "15/11/2026", "rows": [{"description": "...", "value": "..."}]}``.
A row ``{"date": "16/11/2026"}`` is a date that separates the rows after it;
the total still adds every value in the table.
Values keep the text the user typed (``1.200.000``, ``-50.000``, ``12,5``):
dots group thousands and a comma starts the decimals, like the calculator.
The flutter side (``packages/flet-note-editor/.../ledger.dart``) parses them
with the same rules; keep both in sync.
"""

import json

LEDGER = "ledger"


def parse_ledger(raw) -> dict:
    """``{"date": str, "rows": [...]}``; rows are ``{"description", "value"}``
    or, for a separator, ``{"date"}``."""
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        data = None
    if not isinstance(data, dict):
        data = {}
    rows = []
    for row in data.get("rows") or []:
        if isinstance(row, dict) and "date" in row:
            rows.append({"date": str(row.get("date") or "")})
        elif isinstance(row, dict):
            rows.append(
                {
                    "description": str(row.get("description") or ""),
                    "value": str(row.get("value") or ""),
                }
            )
    return {"date": str(data.get("date") or ""), "rows": rows}


def parse_cents(text: str) -> int | None:
    """``"1.234,5"`` → ``123450``; ``None`` when blank or not a number."""
    s = "".join(ch for ch in text if not ch.isspace()).replace("$", "")
    s = s.replace(".", "")
    negative = s.startswith("-")
    if negative:
        s = s[1:]
    whole, _, frac = s.partition(",")
    if not whole and not frac:
        return None
    if not (whole or "0").isdigit() or (frac and not frac.isdigit()):
        return None
    if len(frac) > 2 or "," in frac:
        return None
    cents = int(whole or "0") * 100 + int(frac.ljust(2, "0") or "0")
    return -cents if negative else cents


def format_cents(cents: int) -> str:
    """``123450`` → ``"$1.234,50"``; whole amounts drop the decimals."""
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    text = f"{whole:,}".replace(",", ".")
    if frac:
        text += f",{frac:02d}"
    return f"{sign}${text}"


def total_cents(ledger: dict) -> int:
    return sum(
        parse_cents(row["value"]) or 0 for row in ledger["rows"] if "value" in row
    )


def text_lines(raw) -> list[str]:
    """Plain text for search and the list preview."""
    ledger = parse_ledger(raw)
    date = ledger["date"].strip()
    result = [f"Tabla · {date}" if date else "Tabla"]
    for row in ledger["rows"]:
        if "date" in row:
            if row["date"].strip():
                result.append(row["date"].strip())
            continue
        cells = [row["description"].strip(), row["value"].strip()]
        if any(cells):
            result.append(" — ".join(cell for cell in cells if cell))
    result.append(f"Total: {format_cents(total_cents(ledger))}")
    return result
