import json

from diezapp.features.notes.domain.note_document import (
    lines,
    plain_text,
    preview,
    serialize,
    to_delta,
)


def test_plain_notes_become_a_single_insert():
    assert to_delta("Hola\nmundo", None) == [{"insert": "Hola\nmundo\n"}]
    assert to_delta("", None) == [{"insert": "\n"}]
    assert to_delta(None, None) == [{"insert": "\n"}]


def test_stored_delta_is_returned_as_is():
    delta = [{"insert": "Hola", "attributes": {"bold": True}}, {"insert": "\n"}]
    fmt = json.dumps({"v": 2, "delta": delta})

    assert to_delta("Hola", fmt) == delta


def test_corrupt_format_falls_back_to_the_plain_text():
    assert to_delta("Hola", "{not json") == [{"insert": "Hola\n"}]
    assert to_delta("Hola", '"weird"') == [{"insert": "Hola\n"}]


def test_legacy_per_line_format_is_converted():
    fmt = '[{"k":"h1","f":"serif"},{"k":"check","c":1,"b":1},{"k":"number"},{}]'

    delta = to_delta("Compra\nPan\nUno\nfin", fmt)

    assert delta == [
        {"insert": "Compra", "attributes": {"font": "Lora"}},
        {"insert": "\n", "attributes": {"header": 1}},
        {"insert": "Pan", "attributes": {"bold": True}},
        {"insert": "\n", "attributes": {"list": "checked"}},
        {"insert": "Uno"},
        {"insert": "\n", "attributes": {"list": "ordered"}},
        {"insert": "fin"},
        {"insert": "\n"},
    ]
    assert plain_text(delta) == "Compra\nPan\nUno\nfin"


def test_serialize_keeps_plain_notes_without_format():
    assert serialize([{"insert": "Hola\n"}]) == ("Hola", None)


def test_serialize_round_trips_formatted_notes():
    delta = [
        {"insert": "Hola "},
        {"insert": "mundo", "attributes": {"bold": True}},
        {"insert": "\n"},
    ]

    content, fmt = serialize(delta)

    assert content == "Hola mundo"
    assert to_delta(content, fmt) == delta


def test_lines_split_inserts_and_carry_block_attributes():
    delta = [
        {"insert": "a\nb", "attributes": {"bold": True}},
        {"insert": "\n", "attributes": {"list": "bullet", "bold": True}},
        {"insert": {"image": "x.png"}},
        {"insert": "c\n"},
    ]

    assert lines(delta) == [("a", {}), ("b", {"list": "bullet"}), ("c", {})]


def test_preview_shows_list_markers_and_restarts_numbering():
    delta = [
        {"insert": "Compra"},
        {"insert": "\n", "attributes": {"header": 1}},
        {"insert": "Pan"},
        {"insert": "\n", "attributes": {"list": "checked"}},
        {"insert": "Leche"},
        {"insert": "\n", "attributes": {"list": "unchecked"}},
        {"insert": "Uno"},
        {"insert": "\n", "attributes": {"list": "ordered"}},
        {"insert": "Dos"},
        {"insert": "\n", "attributes": {"list": "ordered"}},
        {"insert": "x\n"},
        {"insert": "Otra"},
        {"insert": "\n", "attributes": {"list": "ordered"}},
    ]

    assert preview(delta) == ("Compra\n☑ Pan\n☐ Leche\n1. Uno\n2. Dos\nx\n1. Otra")
