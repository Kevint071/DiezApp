import math

import pytest

from diezapp.features.calculator.application.calculate_distribution import (
    CalculateDistribution,
)


def test_calculate_distribution_delegates_to_domain():
    result = CalculateDistribution().execute(1000, 10)

    assert result.amount == 1000
    assert result.fondo_local == 79


@pytest.mark.parametrize("amount", [-1, math.inf, -math.inf, math.nan])
def test_calculate_distribution_rejects_invalid_amount(amount):
    with pytest.raises(ValueError, match="amount"):
        CalculateDistribution().execute(amount, 10)


@pytest.mark.parametrize("percentage", [-1, 101])
def test_calculate_distribution_rejects_invalid_percentage(percentage):
    with pytest.raises(ValueError, match="fund_percentage"):
        CalculateDistribution().execute(1000, percentage)
