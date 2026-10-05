import pytest

from core.fotos import ArchivoFoto, clasificar_archivos, clasificar_nombre, extraer_id_carpeta


@pytest.mark.parametrize("nombre,esperado", [
    ("general.jpg", ("fija", "general")),
    ("General.JPG", ("fija", "general")),
    ("acceso_1.jpg", ("fija", "acceso_1")),
    ("Acceso 2.png", ("fija", "acceso_2")),
    ("acceso-02.jpeg", ("fija", "acceso_2")),
    ("acceso_3.jpg", None),
    ("acceso.jpg", None),
    ("1.jpg", ("figura", 1)),
    ("04.jpg", ("figura", 4)),
    ("Fig_01.jpg", ("figura", 1)),
    ("Figura-3.jpg", ("figura", 3)),
    ("IMG_2031.jpg", None),
    ("v3.jpeg", None),
    ("0.jpg", None),
])
def test_clasificar_nombre(nombre, esperado):
    assert clasificar_nombre(nombre) == esperado


def test_duplicados_usa_el_primero_alfabetico_y_avisa():
    archivos = [ArchivoFoto("b", "Fig_2.jpg"), ArchivoFoto("a", "2.jpg"), ArchivoFoto("c", "IMG_1.jpg")]
    archivos += [ArchivoFoto("d", "acceso_1.jpg"), ArchivoFoto("e", "Acceso 1.jpg")]
    c = clasificar_archivos(archivos)
    assert c.figuras[2].nombre == "2.jpg"
    assert c.fijas["acceso_1"].nombre == "Acceso 1.jpg"   # orden alfabético sin distinguir mayúsculas
    assert len(c.avisos) == 2 and any("Fig. 2" in a for a in c.avisos) and any("Acceso 1" in a for a in c.avisos)
    assert [a.nombre for a in c.sin_clasificar] == ["IMG_1.jpg"]


@pytest.mark.parametrize("texto,esperado", [
    ("https://drive.google.com/drive/folders/1w06qXz9hrVLtuoimGMzln-8m6FxYv2A3", "1w06qXz9hrVLtuoimGMzln-8m6FxYv2A3"),
    ("https://drive.google.com/drive/folders/1w06q_X-9?usp=sharing", "1w06q_X-9"),
    ("  1w06qXz9hrVLtuoimGMzln  ", "1w06qXz9hrVLtuoimGMzln"),
    ("", ""),
])
def test_extraer_id_carpeta(texto, esperado):
    assert extraer_id_carpeta(texto) == esperado
