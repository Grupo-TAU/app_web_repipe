import pytest

from core.fotos import ArchivoFoto, clasificar_archivos, clasificar_nombre, extraer_id_carpeta


@pytest.mark.parametrize("nombre,esperado", [
    ("General.jpg", ("fija", "general")),
    ("TAPA.png", ("fija", "tapa")),
    ("Cámara.jpeg", ("fija", "camara")),
    ("Camara.jpg", ("fija", "camara")),
    ("Fig_01.jpg", ("figura", 1)),
    ("Fig 02.jpg", ("figura", 2)),
    ("Figura-3.jpg", ("figura", 3)),
    ("4.jpg", ("figura", 4)),
    ("IMG_2031.jpg", None),
    ("0.jpg", None),
])
def test_clasificar_nombre(nombre, esperado):
    assert clasificar_nombre(nombre) == esperado


def test_duplicados_usa_el_primero_alfabetico_y_avisa():
    archivos = [ArchivoFoto("b", "Fig_2.jpg"), ArchivoFoto("a", "2.jpg"), ArchivoFoto("c", "IMG_1.jpg")]
    c = clasificar_archivos(archivos)
    assert c.figuras[2].nombre == "2.jpg"
    assert len(c.avisos) == 1 and "Fig. 2" in c.avisos[0]
    assert [a.nombre for a in c.sin_clasificar] == ["IMG_1.jpg"]


@pytest.mark.parametrize("texto,esperado", [
    ("https://drive.google.com/drive/folders/1w06qXz9hrVLtuoimGMzln-8m6FxYv2A3", "1w06qXz9hrVLtuoimGMzln-8m6FxYv2A3"),
    ("https://drive.google.com/drive/folders/1w06q_X-9?usp=sharing", "1w06q_X-9"),
    ("  1w06qXz9hrVLtuoimGMzln  ", "1w06qXz9hrVLtuoimGMzln"),
    ("", ""),
])
def test_extraer_id_carpeta(texto, esperado):
    assert extraer_id_carpeta(texto) == esperado
