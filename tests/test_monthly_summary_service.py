from diezapp.features.monthly_summary.domain.monthly_summary_service import (
    MonthlySummaryService,
)


class InMemoryCalculationRepository:
    def __init__(self, calculations):
        self.calculations = calculations

    def list(self):
        return list(self.calculations)


def _calculation(created_at, amount, fund_local):
    return {
        "created_at": created_at,
        "amount": amount,
        "sostenimiento": amount / 10,
        "envio_21": amount / 5,
        "fondo_local": fund_local,
    }


def test_monthly_summary_returns_empty_totals_for_empty_months():
    service = MonthlySummaryService(InMemoryCalculationRepository([]))

    assert service.month_calculations(2026, 8) == []
    assert service.month_totals(2026, 8) == {
        "amount": 0.0,
        "sostenimiento": 0.0,
        "envio_21": 0.0,
        "fondo_local": 0.0,
    }
    assert service.general_totals([]) == service.month_totals(2026, 8)


def test_monthly_summary_aggregates_multiple_months():
    calculations = [
        _calculation("2026-08-20T10:00:00+00:00", 200, 2),
        _calculation("2026-08-01T10:00:00+00:00", 100, 1),
        _calculation("2026-07-10T10:00:00+00:00", 50, 5),
    ]
    service = MonthlySummaryService(InMemoryCalculationRepository(calculations))

    assert [item["amount"] for item in service.month_calculations(2026, 8)] == [
        100,
        200,
    ]
    assert service.sum_month_totals([(2026, 8), (2026, 7)]) == {
        "amount": 350.0,
        "sostenimiento": 35.0,
        "envio_21": 70.0,
        "fondo_local": 8.0,
    }
    assert service.general_totals([(2026, 8), (2026, 7)]) == {
        "amount": 175.0,
        "sostenimiento": 17.5,
        "envio_21": 35.0,
        "fondo_local": 8.0,
    }
