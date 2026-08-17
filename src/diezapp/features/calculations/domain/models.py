from typing import TypedDict


class Calculation(TypedDict):
    id: str
    created_at: str
    amount: float
    envio_21: float
    restante: float
    fondo_local: float
    sostenimiento: float
    fund_percentage: int
    updated_at: str | None
