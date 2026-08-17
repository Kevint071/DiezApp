from diezapp.features.conflicts.application.conflict_service import ConflictService


class InMemoryConflictRepository:
    def __init__(self):
        self.data = {}

    def load(self, kind="calculations"):
        return self.data.get(kind, {"conflicts": [], "pending_add": []})

    def save(self, conflicts, pending_add, kind="calculations"):
        self.data[kind] = {
            "conflicts": conflicts,
            "pending_add": pending_add,
        }

    def clear(self, kind="calculations"):
        self.data.pop(kind, None)


def test_conflict_service_saves_counts_and_clears_by_kind():
    repository = InMemoryConflictRepository()
    service = ConflictService(repository)
    conflicts = [{"existing": {"id": "1"}, "imported": {"id": "1"}}]

    service.save(conflicts, [{"id": "2"}], kind="notes")

    assert service.count("notes") == 1
    assert service.load("notes")["pending_add"] == [{"id": "2"}]
    service.clear("notes")
    assert service.count("notes") == 0