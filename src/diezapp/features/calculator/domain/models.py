from dataclasses import dataclass


@dataclass(frozen=True)
class Distribution:
    amount: float
    envio_21: float
    restante: float
    fondo_local: float
    sostenimiento: float
