import json

import pytest

from diezapp.features.notes.domain.note_document import (
    lines,
    plain_text,
    preview,
    serialize,
    to_delta,
)
from diezapp.features.notes.domain.note_table import (
    format_cents,
    parse_cents,
    parse_ledger,
    text_lines,
    total_cents,
)


def _ledger(date="15/11/2026", rows=(("Arriendo", "1.200.000"), ("Luz", "85.500,5"))):
    return json.dumps(
        {"date": date, "rows": [{"description": d, "value": v} for d, v in rows]}
    )


@pytest.mark.parametrize(
    ("text", "cents"),
    [
        ("1.200.000", 120_000_000),
        ("$ 1.200.000", 120_000_000),
        ("85.500,5", 8_550_050),
        ("0,99", 99),
        (",5", 50),
        ("-50.000", -5_000_000),
        ("7", 700),
    ],
)
def test_parse_cents_reads_dot_thousands_and_comma_decimals(text, cents):
    assert parse_cents(text) == cents


@pytest.mark.parametrize("text", ["", "  ", "-", "abc", "1,2,3", "1,234", "1-2"])
def test_parse_cents_rejects_blank_and_invalid_text(text):
    assert parse_cents(text) is None


def test_format_cents_matches_the_app_currency_style():
    assert format_cents(120_000_000) == "$1.200.000"
    assert format_cents(8_550_050) == "$85.500,50"
    assert format_cents(-5_000_000) == "-$50.000"
    assert format_cents(0) == "$0"


def test_total_skips_blank_and_invalid_values():
    ledger = parse_ledger(
        _ledger(rows=(("A", "1.000"), ("B", ""), ("C", "abc"), ("D", "-250,5")))
    )

    assert total_cents(ledger) == 74_950


def test_parse_ledger_tolerates_corrupt_data():
    assert parse_ledger("{nope") == {"date": "", "rows": []}
    assert parse_ledger('{"rows": [1, {"value": 5}]}') == {
        "date": "",
        "rows": [{"description": "", "value": "5"}],
    }


def test_text_lines_list_date_rows_and_total():
    assert text_lines(_ledger()) == [
        "Tabla · 15/11/2026",
        "Arriendo — 1.200.000",
        "Luz — 85.500,5",
        "Total: $1.285.500,50",
    ]
    assert text_lines(_ledger(date="", rows=())) == ["Tabla", "Total: $0"]


def test_notes_with_only_a_table_keep_their_format():
    delta = [{"insert": {"ledger": _ledger()}}, {"insert": "\n"}]

    content, fmt = serialize(delta)

    assert fmt is not None
    assert to_delta(content, fmt) == delta
    assert content.startswith("Tabla · 15/11/2026")


def test_table_text_reaches_search_and_preview():
    delta = [
        {"insert": "Gastos\n"},
        {"insert": {"ledger": _ledger(rows=(("Agua", "40.000"),))}},
        {"insert": "\nfin\n"},
    ]

    assert plain_text(delta) == (
        "Gastos\nTabla · 15/11/2026\nAgua — 40.000\nTotal: $40.000\nfin"
    )
    assert preview(delta).startswith("Gastos\nTabla · 15/11/2026\nAgua — 40.000")


def test_table_lines_close_with_the_embed_newline():
    delta = [
        {"insert": {"ledger": _ledger(rows=())}},
        {"insert": "\n"},
        {"insert": "fin\n"},
    ]

    assert lines(delta) == [
        ("Tabla · 15/11/2026", {}),
        ("Total: $0", {}),
        ("fin", {}),
    ]


def test_date_separators_split_the_rows_but_not_the_total():
    raw = json.dumps(
        {
            "date": "15/11/2026",
            "rows": [
                {"description": "Pan", "value": "5.000"},
                {"date": "16/11/2026"},
                {"description": "Leche", "value": "4.500"},
                {"date": ""},
            ],
        }
    )

    ledger = parse_ledger(raw)

    assert ledger["rows"][1] == {"date": "16/11/2026"}
    assert total_cents(ledger) == 950_000
    assert text_lines(raw) == [
        "Tabla · 15/11/2026",
        "Pan — 5.000",
        "16/11/2026",
        "Leche — 4.500",
        "Total: $9.500",
    ]
