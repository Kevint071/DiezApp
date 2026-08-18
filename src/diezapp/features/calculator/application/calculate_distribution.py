import math

from diezapp.features.calculator.domain.calculator_service import (
    calculate_distribution,
)
from diezapp.features.calculator.domain.models import Distribution


class CalculateDistribution:
    def execute(self, amount: float, fund_percentage: int) -> Distribution:
        if not math.isfinite(amount) or amount < 0:
            raise ValueError("amount must be a finite, non-negative number")
        if not 0 <= fund_percentage <= 100:
            raise ValueError("fund_percentage must be between 0 and 100")
        return calculate_distribution(amount, fund_percentage)
