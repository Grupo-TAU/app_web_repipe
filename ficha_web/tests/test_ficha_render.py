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
