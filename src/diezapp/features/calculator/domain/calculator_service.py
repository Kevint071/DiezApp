from .models import Distribution


def calculate_distribution(amount: float, fund_percentage: int) -> Distribution:
    envio_21 = amount * 0.21
    restante = amount * 0.79
    fondo_local = restante * (fund_percentage / 100)
    sostenimiento = amount - envio_21 - fondo_local
    return Distribution(
        amount=amount,
        envio_21=envio_21,
        restante=restante,
        fondo_local=fondo_local,
        sostenimiento=sostenimiento,
    )
