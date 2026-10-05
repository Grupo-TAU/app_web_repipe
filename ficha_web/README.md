# ficha_web — fichas de inspección sin QGIS

App web (Streamlit) con dos funciones:

1. **Formulario** para cargar/editar inspecciones, guardadas en **Supabase**.
2. **Ficha PDF**: ingresás el ID de inspección → vista previa (datos de Supabase, fotos de Google Drive) → descarga del PDF.

La lógica vive en `core/` (sin Streamlit); `pages/`, `app.py` y `ui.py` solo la invocan.

## Modo mock (sin Supabase ni Drive)

Es lo más rápido para probar. Con Docker (recomendado; WeasyPrint necesita Pango, que en Windows es complicado):

```bash
docker compose up --build
```

Abrir <http://localhost:8501>. Sin `.env` arranca en modo mock con la inspección `1001` y fotos de ejemplo (`fixtures/fotos/1001/`; la Fig. 3 falta a propósito para ver el recuadro «Sin foto» y el aviso). Los datos mock viven en memoria: se pierden al reiniciar.

## Configuración real

```bash
cp .env.example .env     # completar y poner USE_MOCK=0
```

| Variable | Qué es |
| --- | --- |
| `SUPABASE_URL`, `SUPABASE_KEY` | URL del proyecto y clave **publicable** (nunca la `service_role`) |
| `GOOGLE_SA_JSON_PATH` o `GOOGLE_SA_JSON` | JSON de la cuenta de servicio (ruta, o su contenido) |
| `DRIVE_PARENT_FOLDER_ID` | ID de la carpeta `05 - INSPECCIONES` |
| `USE_MOCK` | `1` = modo mock |
| `FOTOS_LOCAL_DIR` | Carpeta de fotos para modo mock |

Preparación de los servicios: `docs/02_supabase_setup.md` (ejecutar `supabase/migrations/0001_init.sql` y después `0002_opciones_y_figura_unica.sql`, crear usuarios, desactivar registro abierto) y `docs/03_drive_fotos_setup.md` (cuenta de servicio y permiso de Lector).

Con Docker, para Drive montar el JSON como volumen de solo lectura (ver comentario en `docker-compose.yml`) y apuntar `GOOGLE_SA_JSON_PATH` a la ruta dentro del contenedor.

## Hosting en Streamlit Community Cloud

1. Subir el repo a GitHub (`Grupo-TAU/app_web_repipe`).
2. En <https://share.streamlit.io> → **Create app** → elegir el repo, rama `main`, archivo principal `ficha_web/app.py`.
3. **Advanced settings**: Python 3.12 y pegar en **Secrets** el contenido de `ficha_web/.streamlit/secrets.toml.example` con los valores reales (`USE_MOCK = "0"`).
4. **Deploy**. Las librerías de sistema para WeasyPrint salen de `packages.txt` (raíz del repo).

Limitaciones: la app se duerme tras unos días sin uso (despierta en segundos) y al recargar la página hay que volver a iniciar sesión.

## Tests

```bash
docker compose run --rm --no-deps -v "${PWD}:/app" app pytest -q
```

## Verificar Drive

```bash
python scripts/test_drive.py <ruta_al_json> <url_o_id_de_carpeta>
```

## Convención de nombres de fotos

`general.jpg`, `acceso_1.jpg`, `acceso_2.jpg` (fotos fijas) y `1.jpg`, `2.jpg`, `3.jpg`… (una por figura, según `nro_figura`); cualquier extensión de imagen. Se toleran variantes como `Acceso 1` o `04`. Las reglas están al inicio de `core/fotos.py`.

## Notas

- La app **no guarda estado local**: todo está en Supabase y Drive, así que puede moverse de la PC/servidor de la oficina a un hosting accesible desde internet sin cambiar código.
- Fuera de la v1 (ganchos dejados): croquis (`{# TODO croquis #}` en la plantilla), subida de fotos, roles, lotes, historial, uso desde el campo.
- Las fotos de ejemplo se regeneran con `python scripts/generar_fixtures.py`.

## Decisiones

- **Plantilla** basada en `Informe-OS-provisional.html` (original en `templates/Informe-OS-provisional.original.html`), no en `Informe-OS.html`. Ese archivo no traía barra de etiqueta de foto (`.fig-label-bar`), ni Acceso/Diámetro/Largo: se agregaron.
- **Página**: no hay `.qpt` en el repo; A4 vertical, márgenes 12 mm (`PAGINA` / `MARGEN` para cambiarlos).
- **Recuadro 4:3** (`padding-bottom: 75%` + `position:absolute`): se verificó que WeasyPrint lo renderiza bien; no hizo falta alto fijo.
- **Números**: hasta 2 decimales sin ceros finales (`27` y no `27,00`); el diámetro, 1 decimal.
- **Cache** de imágenes (clave `(file_id, modifiedTime)`, TTL 10 min) y del listado de la carpeta padre (5 min) con un cache propio en memoria dentro de `core/`, en vez de `st.cache_data`, para que `core/` no dependa de Streamlit.
- **`FuenteFotos.listar`** devuelve un `Listado(archivos, carpeta_id)`; así `core/ficha.py` guarda en la base el ID de carpeta resuelto sin acoplarse a Drive. Los problemas esperables de fotos se levantan como `FotosError` y se convierten en avisos.
- **Responsive (celular/tablet)**: el formulario usa filas con sus propios campos (observaciones y patologías) en vez de `st.data_editor`, porque una tabla editable es incómoda con el dedo; en pantallas angostas las columnas se apilan. CSS en `ui.estilos()` (botones altos, campos a 16 px para evitar el zoom de iOS) y una regla `@media screen` en la plantilla para la vista previa; el PDF no se ve afectado. Probado en emulación de 375 px (sin scroll horizontal), no en un dispositivo real.
- **Desplegables editables**: Operario y Material son `selectbox` alimentados por la tabla `opciones` (`categoria`, `valor`), que se edita desde la página **Configuración**. Las inspecciones guardan el texto elegido, sin FK: quitar una opción no toca las ya guardadas, y si una inspección vieja tiene un valor que ya no está en la lista, se sigue mostrando. Para sumar otra categoría: agregarla en `CATEGORIAS_OPCIONES` (`core/modelos.py`) y usar `ui.opciones("<categoria>")` en el formulario.
- **`nro_figura` único por inspección**: restricción `unique (id_inspeccion, nro_figura)` en la base (migración 0002) y validación bloqueante en el formulario (antes solo avisaba). Varias patologías sin figura siguen permitidas.
- **Archivos extra** respecto a la estructura pedida: `ui.py` (pegamento con Streamlit), `core/auth.py` (login Supabase), `scripts/generar_fixtures.py`.
- El **PDF y la vista previa** se arman una vez por ficha y se guardan en la sesión; se invalidan al guardar o al volver a pedir la ficha.
- `pytest` va en `requirements.txt` (la imagen sirve también para correr los tests).
- Los `.md` de `docs/` son los de Notion con las credenciales reemplazadas por placeholders.
