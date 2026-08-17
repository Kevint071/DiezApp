from diezapp.features.calculator.domain.calculator_service import (
    calculate_distribution,
)


def test_calculate_distribution_uses_configured_fund_percentage():
    distribution = calculate_distribution(1000, 10)

    assert distribution.envio_21 == 210
    assert distribution.restante == 790
    assert distribution.fondo_local == 79
    assert distribution.sostenimiento == 711
