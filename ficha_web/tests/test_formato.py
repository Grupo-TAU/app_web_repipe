from datetime import date

from core import formato


def test_numero():
    assert formato.numero(42.5) == "42,5"
    assert formato.numero(300.0, 1) == "300"
    assert formato.numero(27.0) == "27"
    assert formato.numero(12.34) == "12,34"
    assert formato.numero(None) == "—"


def test_fecha():
    assert formato.fecha(date(2026, 9, 5)) == "05/09/2026"
    assert formato.fecha(None) == "—"


def test_texto():
    assert formato.texto(None) == "—"
    assert formato.texto("  ") == "—"
    assert formato.texto("Hormigón") == "Hormigón"
