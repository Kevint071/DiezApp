from diezapp.features.calculator.domain.calculator_service import (
    calculate_distribution,
)


def test_calculate_distribution_uses_configured_fund_percentage():
    distribution = calculate_distribution(1000, 10)

    assert distribution.envio_21 == 210
    assert distribution.restante == 790
    assert distribution.fondo_local == 79
    assert distribution.sostenimiento == 711


def test_calculate_distribution_handles_zero_amount():
    distribution = calculate_distribution(0, 10)

    assert distribution.amount == 0
    assert distribution.envio_21 == 0
    assert distribution.restante == 0
    assert distribution.fondo_local == 0
    assert distribution.sostenimiento == 0


def test_calculate_distribution_allows_zero_fund_percentage():
    distribution = calculate_distribution(1000, 0)

    assert distribution.fondo_local == 0
    assert distribution.sostenimiento == 790


def test_calculate_distribution_handles_high_fund_percentage():
    distribution = calculate_distribution(1000, 100)

    assert distribution.fondo_local == 790
    assert distribution.sostenimiento == 0
