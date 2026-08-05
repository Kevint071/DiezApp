from utils.conflicts import calcs_differ, notes_differ


class TestNotesDiffer:
    def test_identical_notes_do_not_differ(self):
        a = {"id": "1", "title": "Compras", "content": "Leche, pan"}
        b = {"id": "1", "title": "Compras", "content": "Leche, pan"}
        assert notes_differ(a, b) is False

    def test_title_only_change_is_detected_as_conflict(self):
        # Regression: previously only "content" was compared, so a title-only
        # edit was silently ignored instead of raising a conflict.
        a = {"id": "1", "title": "Compras", "content": "Leche, pan"}
        b = {"id": "1", "title": "Lista de compras", "content": "Leche, pan"}
        assert notes_differ(a, b) is True

    def test_content_only_change_is_detected_as_conflict(self):
        a = {"id": "1", "title": "Compras", "content": "Leche, pan"}
        b = {"id": "1", "title": "Compras", "content": "Leche, pan, huevos"}
        assert notes_differ(a, b) is True

    def test_both_title_and_content_change_is_detected_as_conflict(self):
        a = {"id": "1", "title": "Compras", "content": "Leche, pan"}
        b = {"id": "1", "title": "Lista", "content": "Huevos"}
        assert notes_differ(a, b) is True

    def test_missing_fields_default_to_none_and_compare_equal(self):
        assert notes_differ({}, {}) is False


class TestCalcsDiffer:
    def test_identical_calcs_do_not_differ(self):
        a = {
            "amount": 100,
            "envio_21": 21,
            "restante": 79,
            "fondo_local": 10,
            "sostenimiento": 5,
            "fund_percentage": 10,
        }
        b = dict(a)
        assert calcs_differ(a, b) is False

    def test_amount_change_is_detected_as_conflict(self):
        a = {"amount": 100, "fund_percentage": 10}
        b = {"amount": 200, "fund_percentage": 10}
        assert calcs_differ(a, b) is True
