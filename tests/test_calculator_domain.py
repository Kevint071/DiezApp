import pytest

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


def test_calculate_distribution_parts_add_up_to_the_peso():
    # 2.354.345 at 1%: rounding each float on its own showed restante
    # 1.859.933 but fondo + sostenimiento 1.859.932 — one peso lost.
    distribution = calculate_distribution(2_354_345, 1)

    assert distribution.envio_21 == 494_412
    assert distribution.restante == 1_859_933
    assert distribution.fondo_local == 18_599
    assert distribution.sostenimiento == 1_841_334
    assert distribution.fondo_local + distribution.sostenimiento == (
        distribution.restante
    )
    assert distribution.envio_21 + distribution.restante == distribution.amount


@pytest.mark.parametrize("amount", [1, 7, 99, 1_001, 123_457, 2_354_345, 9_999_999])
@pytest.mark.parametrize("percentage", [0, 1, 7, 10, 33, 50, 99, 100])
def test_calculate_distribution_is_always_whole_pesos_that_add_up(amount, percentage):
    distribution = calculate_distribution(amount, percentage)

    for value in (
        distribution.envio_21,
        distribution.restante,
        distribution.fondo_local,
        distribution.sostenimiento,
    ):
        assert value == int(value)
    assert distribution.envio_21 + distribution.restante == amount
    assert distribution.fondo_local + distribution.sostenimiento == (
        distribution.restante
    )


def test_calculate_distribution_rounds_half_pesos_up():
    # 0.21 * 50 = 10.5 → 11 (not banker's rounding to 10).
    assert calculate_distribution(50, 10).envio_21 == 11
