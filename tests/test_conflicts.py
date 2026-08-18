from diezapp.features.conflicts.application.conflict_service import ConflictService


class InMemoryConflictRepository:
    def load(self, kind="calculations"):
        return {"conflicts": [], "pending_add": []}

    def save(self, conflicts, pending_add, kind="calculations"):
        pass

    def clear(self, kind="calculations"):
        pass


def conflict_service():
    return ConflictService(InMemoryConflictRepository())


class TestNotesDiffer:
    def test_identical_notes_do_not_differ(self):
        service = conflict_service()
        a = {"id": "1", "title": "Compras", "content": "Leche, pan"}
        b = {"id": "1", "title": "Compras", "content": "Leche, pan"}
        assert service.notes_differ(a, b) is False

    def test_title_only_change_is_detected_as_conflict(self):
        # Regression: previously only "content" was compared, so a title-only
        # edit was silently ignored instead of raising a conflict.
        service = conflict_service()
        a = {"id": "1", "title": "Compras", "content": "Leche, pan"}
        b = {"id": "1", "title": "Lista de compras", "content": "Leche, pan"}
        assert service.notes_differ(a, b) is True

    def test_content_only_change_is_detected_as_conflict(self):
        service = conflict_service()
        a = {"id": "1", "title": "Compras", "content": "Leche, pan"}
        b = {"id": "1", "title": "Compras", "content": "Leche, pan, huevos"}
        assert service.notes_differ(a, b) is True

    def test_both_title_and_content_change_is_detected_as_conflict(self):
        service = conflict_service()
        a = {"id": "1", "title": "Compras", "content": "Leche, pan"}
        b = {"id": "1", "title": "Lista", "content": "Huevos"}
        assert service.notes_differ(a, b) is True

    def test_missing_fields_default_to_none_and_compare_equal(self):
        assert conflict_service().notes_differ({}, {}) is False


class TestCalcsDiffer:
    def test_identical_calcs_do_not_differ(self):
        service = conflict_service()
        a = {
            "amount": 100,
            "envio_21": 21,
            "restante": 79,
            "fondo_local": 10,
            "sostenimiento": 5,
            "fund_percentage": 10,
        }
        b = dict(a)
        assert service.calculations_differ(a, b) is False

    def test_amount_change_is_detected_as_conflict(self):
        service = conflict_service()
        a = {"amount": 100, "fund_percentage": 10}
        b = {"amount": 200, "fund_percentage": 10}
        assert service.calculations_differ(a, b) is True
