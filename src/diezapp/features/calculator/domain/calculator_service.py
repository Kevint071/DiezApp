from decimal import ROUND_HALF_UP, Decimal

from .models import Distribution

ENVIO_RATE = Decimal("0.21")


def _round_peso(value: Decimal) -> Decimal:
    return value.quantize(Decimal(1), rounding=ROUND_HALF_UP)


def calculate_distribution(amount: float, fund_percentage: int) -> Distribution:
    # Only envío and fondo local are rounded; restante and sostenimiento are
    # what's left over, so every split adds up to the peso.
    total = Decimal(str(amount))
    envio_21 = _round_peso(total * ENVIO_RATE)
    restante = total - envio_21
    fondo_local = _round_peso(restante * fund_percentage / 100)
    sostenimiento = restante - fondo_local
    return Distribution(
        amount=amount,
        envio_21=float(envio_21),
        restante=float(restante),
        fondo_local=float(fondo_local),
        sostenimiento=float(sostenimiento),
    )
