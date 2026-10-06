import pytest

from core.ficha import InspeccionNoEncontrada, armar_ficha
from core.render import render_html, render_pdf


def test_armar_ficha_mock_avisa_fig_3(repo, fuente):
    f = armar_ficha("1001", repo, fuente)
    assert all(f.fijas[k] is not None for k in ("general", "acceso_1", "acceso_2"))
    assert set(f.figuras) == {1, 2}
    assert any("Fig. 3" in a and "no tiene foto" in a for a in f.avisos)
    assert len(f.avisos) == 1


def test_id_inexistente(repo, fuente):
    with pytest.raises(InspeccionNoEncontrada):
        armar_ficha("no-existe", repo, fuente)


def test_html_tiene_datos_y_no_imprime_obs_interna(repo, fuente):
    html = render_html(armar_ficha("1001", repo, fuente))
    assert "1001" in html and "Av. Italia 3200 esq. Comercio" in html
    assert "12,3 m – Fisura longitudinal (Fig. 1)" in html
    assert "Sin foto" in html            # Fig. 3
    assert "olor desde hace" not in html  # obs_interna


def test_ubicacion_con_script_se_escapa(repo, fuente):
    insp = repo.obtener("1001")
    insp.ubicacion = "<script>alert(1)</script>"
    repo.guardar(insp)
    html = render_html(armar_ficha("1001", repo, fuente))
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_pdf_valido(repo, fuente):
    pytest.importorskip("weasyprint")
    pdf = render_pdf(render_html(armar_ficha("1001", repo, fuente)))
    assert pdf.startswith(b"%PDF") and len(pdf) > 5000


def test_fotos_de_patologias_de_a_2_en_16_9(repo, fuente):
    from core.render import contexto
    f = armar_ficha("1001", repo, fuente)
    filas = contexto(f)["filas_figuras"]
    assert len(filas) == 2 and all(len(fila) == 2 for fila in filas)   # 3 figuras -> filas de 2, la última con hueco
    assert filas[1][1] is None
    html = render_html(f)
    assert 'class="img-grid figuras"' in html and "padding-bottom: 56.25%" in html


def test_logo_en_la_ficha(repo, fuente):
    html = render_html(armar_ficha("1001", repo, fuente))
    assert "data:image/png;base64," in html and 'alt="Repipe"' in html


def test_imagenes_se_reducen_a_1920_de_ancho():
    import base64
    import io

    from PIL import Image

    from core.render import reducir_a_data_uri
    buf = io.BytesIO()
    Image.new("RGB", (4000, 3000), "gray").save(buf, "JPEG")
    uri = reducir_a_data_uri(buf.getvalue())
    img = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1])))
    assert img.width == 1920
