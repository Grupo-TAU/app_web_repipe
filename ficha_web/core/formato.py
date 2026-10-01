"""Formateo es-UY: coma decimal, fechas dd/mm/aaaa, nulos como —."""
from datetime import date

NULO = "—"


def texto(valor) -> str:
    if valor is None or str(valor).strip() == "":
        return NULO
    return str(valor)


def numero(valor, max_decimales: int = 2) -> str:
    """42.5 -> '42,5'; 300.0 -> '300'; None -> '—'."""
    if valor is None:
        return NULO
    s = f"{float(valor):.{max_decimales}f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def fecha(valor: date | None) -> str:
    return valor.strftime("%d/%m/%Y") if valor else NULO
