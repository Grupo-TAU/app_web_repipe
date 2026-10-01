# 02_supabase_setup

# 02 — Supabase: creación del proyecto y base de datos de inspecciones

Vértice 2 de 3. Esta guía deja lista la base que consume la app web de fichas (`ficha_web/`, ver `01_prompt_claude_code_ficha_web.md`). Todo lo que sigue se puede ejecutar desde el dashboard de Supabase; el SQL queda además versionado en el repo como `ficha_web/supabase/migrations/0001_init.sql`.

Supabase acá es solo Postgres + Auth. No se usa Storage (las fotos viven en Drive, ver `03_drive_fotos_setup.md`) y no hace falta PostGIS: estos datos no tienen geometría.

---

## 1. Crear el proyecto

1. Entrar a [https://supabase.com/dashboard](https://supabase.com/dashboard) e iniciar sesión (recomendado: cuenta de la empresa, no personal, para que el proyecto no dependa de una persona).
2. Crear o elegir una **Organization** (ej. `Grupo TAU`).
3. **New project**:
    - Name: `repipe-inspecciones`
    - Database password: generar una y guardarla en el gestor de contraseñas. No se pega en el repo ni en chats.
    - Region: **South America (São Paulo)**. Es la más cercana a Uruguay y minimiza latencia.
    - Plan: ver sección 2.
4. Esperar a que termine el aprovisionamiento (1–2 minutos).

## 2. Plan: Free vs Pro (decisión a tomar)

Según la página oficial de precios ([Supabase Pricing](https://supabase.com/pricing)):

|  | Free | Pro (USD 25/mes) |
| --- | --- | --- |
| Base de datos | 500 MB por proyecto | 8 GB por proyecto |
| Inactividad | El proyecto se **pausa tras 1 semana sin actividad** | No se pausa |
| Backups | **No incluye** backups automáticos ni PITR | Backups diarios, 7 días de retención |

El tamaño no es el problema: son tablas de texto, 500 MB alcanzan para decenas de miles de inspecciones. Lo que importa es **la pausa por inactividad** (una semana sin que nadie use la app y hay que reactivarlo a mano) y **la ausencia de backups**.

- Si la app va a ser herramienta de trabajo diaria/semanal y los datos importan: **Pro**.
- Si van a arrancar con prueba piloto: Free, pero (a) programar el script de backup de la sección 8 y (b) aceptar la pausa.

## 3. SQL: esquema

Dashboard → **SQL Editor** → New query → pegar y ejecutar. (Es idempotente en lo posible; si falla a la mitad, revisar el error antes de reintentar.)

```sql
-- =====================================================================
-- 0001_init.sql — inspecciones de repipe / fichas
-- =====================================================================

-- ---------- Tablas ----------------------------------------------------

create table public.inspeccion (
    id              text primary key,             -- N° de inspección (lo ingresa el usuario)
    ubicacion       text not null,
    solicitante     text,
    operario        text,
    fecha           date,
    acceso          text,
    diametro        numeric(7,1),                 -- mm
    material        text,
    largo           numeric(8,2),                 -- m
    limpieza        text,
    conclusiones    text,
    drive_folder_id text,                         -- ID de la carpeta de fotos en Drive (cache; ver doc 03)
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    constraint inspeccion_id_formato
        check (id ~ '^[A-Za-z0-9._-]+$')          -- sin espacios ni barras: se usa para armar nombres de carpeta
);

create table public.observaciones (
    id              bigint generated always as identity primary key,
    id_inspeccion   text not null
        references public.inspeccion (id) on delete cascade on update cascade,
    obs_interna     text not null,
    created_at      timestamptz not null default now()
);

create table public.patologias (
    id              bigint generated always as identity primary key,
    id_inspeccion   text not null
        references public.inspeccion (id) on delete cascade on update cascade,
    metros          numeric(8,2) check (metros is null or metros >= 0),
    patologia       text not null,
    nro_figura      integer check (nro_figura is null or nro_figura > 0),
    created_at      timestamptz not null default now()
);

create index observaciones_id_inspeccion_idx on public.observaciones (id_inspeccion);
create index patologias_id_inspeccion_idx    on public.patologias (id_inspeccion);

comment on column public.inspeccion.id is
    'N° de inspección. Es la clave de negocio: aparece en el nombre de la carpeta de Drive ("<id> - <ubicacion>").';
comment on column public.inspeccion.drive_folder_id is
    'ID de carpeta de Drive. Si es NULL, la app lo resuelve por nombre y lo guarda acá.';
comment on column public.observaciones.obs_interna is
    'Observación interna: NO se imprime en la ficha PDF.';
comment on column public.patologias.nro_figura is
    'Número de figura. Se relaciona con la foto de Drive por el nombre del archivo (ver doc 03).';

-- ---------- updated_at automático ------------------------------------

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end $$;

create trigger inspeccion_set_updated_at
    before update on public.inspeccion
    for each row execute function public.set_updated_at();

-- ---------- Guardado atómico (upsert + hijas) ------------------------
-- La API REST de Supabase no hace transacciones de varias tablas. Esta función
-- guarda inspeccion + observaciones + patologias en UNA transacción: o entra
-- todo o no entra nada. La app la llama con supabase.rpc("guardar_inspeccion", {"p": {...}}).
-- Semántica: las hijas se reemplazan por completo con lo que llega en el payload.

create or replace function public.guardar_inspeccion(p jsonb)
returns text
language plpgsql
security invoker            -- corre con los permisos (y RLS) del usuario que llama
set search_path = public
as $$
declare
    v_id text := nullif(trim(p->>'id'), '');
begin
    if v_id is null then
        raise exception 'El id de inspección es obligatorio';
    end if;

    insert into public.inspeccion (
        id, ubicacion, solicitante, operario, fecha, acceso,
        diametro, material, largo, limpieza, conclusiones, drive_folder_id
    )
    values (
        v_id,
        p->>'ubicacion',
        nullif(p->>'solicitante', ''),
        nullif(p->>'operario', ''),
        nullif(p->>'fecha', '')::date,
        nullif(p->>'acceso', ''),
        nullif(p->>'diametro', '')::numeric,
        nullif(p->>'material', ''),
        nullif(p->>'largo', '')::numeric,
        nullif(p->>'limpieza', ''),
        nullif(p->>'conclusiones', ''),
        nullif(p->>'drive_folder_id', '')
    )
    on conflict (id) do update set
        ubicacion       = excluded.ubicacion,
        solicitante     = excluded.solicitante,
        operario        = excluded.operario,
        fecha           = excluded.fecha,
        acceso          = excluded.acceso,
        diametro        = excluded.diametro,
        material        = excluded.material,
        largo           = excluded.largo,
        limpieza        = excluded.limpieza,
        conclusiones    = excluded.conclusiones,
        -- no pisar con NULL un ID de carpeta ya resuelto
        drive_folder_id = coalesce(excluded.drive_folder_id, public.inspeccion.drive_folder_id);

    delete from public.observaciones where id_inspeccion = v_id;
    insert into public.observaciones (id_inspeccion, obs_interna)
    select v_id, o->>'obs_interna'
    from jsonb_array_elements(coalesce(p->'observaciones', '[]'::jsonb)) as o
    where coalesce(trim(o->>'obs_interna'), '') <> '';

    delete from public.patologias where id_inspeccion = v_id;
    insert into public.patologias (id_inspeccion, metros, patologia, nro_figura)
    select v_id,
           nullif(x->>'metros', '')::numeric,
           x->>'patologia',
           nullif(x->>'nro_figura', '')::integer
    from jsonb_array_elements(coalesce(p->'patologias', '[]'::jsonb)) as x
    where coalesce(trim(x->>'patologia'), '') <> '';

    return v_id;
end $$;

revoke execute on function public.guardar_inspeccion(jsonb) from public, anon;
grant  execute on function public.guardar_inspeccion(jsonb) to authenticated;

-- ---------- Seguridad: RLS -------------------------------------------
-- Regla: solo usuarios AUTENTICADOS (login de la app) leen y escriben.
-- Sin sesión (rol anon) no se ve nada.

alter table public.inspeccion    enable row level security;
alter table public.observaciones enable row level security;
alter table public.patologias    enable row level security;

create policy inspeccion_authenticated_all on public.inspeccion
    for all to authenticated using (true) with check (true);
create policy observaciones_authenticated_all on public.observaciones
    for all to authenticated using (true) with check (true);
create policy patologias_authenticated_all on public.patologias
    for all to authenticated using (true) with check (true);

-- Permisos explícitos (por si el proyecto no los otorga por defecto).
grant select, insert, update, delete on public.inspeccion, public.observaciones, public.patologias to authenticated;
grant usage, select on all sequences in schema public to authenticated;
```

Notas de diseño:

- **`id` es `text`**, no número: la clave viene del sistema de OS y también arma el nombre de la carpeta de Drive. Si están 100 % seguros de que siempre es numérico sin ceros a la izquierda, podría ser `bigint`, pero `text` no cuesta nada y evita sorpresas.
- **`on update cascade`** permite corregir un ID mal cargado sin perder las hijas. Ojo: si se cambia el ID, hay que renombrar la carpeta de Drive (o tener `drive_folder_id` guardado, que evita depender del nombre).
- **`obs_interna` no se imprime** en la ficha (el nombre sugiere uso interno). Si querés que salga, es un cambio de una línea en la plantilla.
- **`nro_figura` no es único** por inspección a propósito (dos patologías podrían mostrarse en la misma figura). Si no querés eso, agregar `unique (id_inspeccion, nro_figura)`.
- **RLS `using (true)`** significa “cualquier usuario logueado puede todo”. Es correcto para un equipo chico y de confianza; para roles (lector vs. editor) ver sección 9.

## 4. Datos de prueba (opcional, recomendado)

```sql
select public.guardar_inspeccion('{
  "id": "1001",
  "ubicacion": "Av. Italia 3200 esq. Comercio",
  "solicitante": "SOMS - Intendencia de Montevideo",
  "operario": "J. Pérez",
  "fecha": "2026-09-15",
  "acceso": "Cámara",
  "diametro": 300,
  "material": "Hormigón",
  "largo": 42.5,
  "limpieza": "Realizada",
  "conclusiones": "Se observa fisura longitudinal y raíces en junta.",
  "observaciones": [
    {"obs_interna": "Vecino avisó que hay olor desde hace 2 semanas."}
  ],
  "patologias": [
    {"metros": 12.3, "patologia": "Fisura longitudinal", "nro_figura": 1},
    {"metros": 27.0, "patologia": "Raíces en junta",     "nro_figura": 2},
    {"metros": 38.4, "patologia": "Deformación",         "nro_figura": 3}
  ]
}'::jsonb);
```

Verificar: **Table Editor** → las tres tablas deben tener filas. Para borrar la prueba: `delete from public.inspeccion where id = '1001';` (las hijas se borran por cascada).

## 5. Autenticación (usuarios de la app)

La app tiene login; Supabase Auth guarda los usuarios.

1. Dashboard → **Authentication → Sign In / Providers** (el nombre exacto del menú puede variar según la versión del dashboard): dejar habilitado **Email**.
2. **Desactivar el registro abierto**: opción “Allow new users to sign up” → **off**. Si no, cualquiera que conozca la URL del proyecto podría crearse un usuario y (por la política `authenticated`) leer y escribir todo.
3. **Authentication → Users → Add user → Create new user**: cargar email + contraseña de cada persona del equipo, marcando “Auto Confirm User”.
4. Cada persona cambia su contraseña luego (o resetearla desde el dashboard si la olvida).

## 6. Credenciales que necesita la app

Dashboard → botón **Connect** o **Project Settings → API**:

| Variable de la app | Qué es | Dónde se ve |
| --- | --- | --- |
| `SUPABASE_URL` | `<SUPABASE_URL>` | Project URL |
| `SUPABASE_KEY` | Clave **publicable:** <SUPABASE_KEY publicable> | API keys |
- La clave publicable es segura de usar en la app **porque RLS está activo**: sin login no da acceso a nada.
- **Nunca** poner la clave `secret` / `service_role` en la app ni en el repo: saltea RLS por completo.
- Todo va en `.env` local o en los secrets del hosting. El repo solo lleva `.env.example` con nombres y sin valores.

## 7. Verificación rápida

Desde una terminal con Python:

```bash
pip install supabase
```

```python
import os
from supabase import create_client

sb = create_client(os.environ["<SUPABASE_URL>"], os.environ["<SUPABASE_KEY publicable>"])

# 1) Sin login NO debe devolver nada (RLS funcionando)
print("anon:", sb.table("inspeccion").select("id").execute().data)   # -> []

# 2) Con login SÍ
sb.auth.sign_in_with_password({"email": "<email-del-usuario>", "password": "<contraseña>"})
print("auth:", sb.table("inspeccion").select("id, ubicacion").execute().data)
```

Si el paso 1 devuelve filas, RLS no quedó activo: revisar los `alter table … enable row level security`.

## 8. Backups

- **Pro:** backups diarios con 7 días de retención (Database → Backups).
- **Free:** no hay. Correr periódicamente un dump desde una PC/servidor con `pg_dump` instalado. La cadena de conexión se copia de **Connect → Session pooler** (el pooler funciona por IPv4; la conexión directa puede requerir IPv6):

bash

```bash
pg_dump "postgresql://postgres.<ref>:<PASSWORD>@<host-del-pooler>:5432/postgres" \        --schema=public -Fc -f "backup_inspecciones_$(date +%F).dump"
```

**Backup automático en el servidor (decidido):** se usa el script `ficha_web/scripts/backup_supabase.sh`, programado con cron, que deja los dumps en `/srv/backups/db/supabase_inspecciones/` (al lado de `/srv/backups/fotos/`).

1. Instalar `pg_dump` en el servidor con la **misma versión mayor que Postgres de Supabase** o superior (verificar con `select version();` en el SQL Editor). En Debian/Ubuntu:

bash

```bash
   sudo apt install -y postgresql-common   sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh   sudo apt install -y postgresql-client-17     # cambiar 17 por la versión que corresponda
```

1. Crear carpetas y copiar el script:

bash

```bash
   sudo mkdir -p /srv/backups/db/supabase_inspecciones /srv/backups/scripts   sudo cp backup_supabase.sh /srv/backups/scripts/ && sudo chmod 750 /srv/backups/scripts/backup_supabase.sh
```

1. Credenciales en `/etc/backup-supabase.env` (`chmod 600`, dueño: el usuario que corre el cron). Host y usuario se copian de **Connect → Session pooler**; la contraseña es la de la base que se definió al crear el proyecto:

bash

```bash
   export PGHOST="<host del Session pooler>"   export PGPORT="5432"   export PGUSER="postgres.<ref-del-proyecto>"   export PGDATABASE="postgres"   export PGPASSWORD='<contraseña de la base>'   RETENCION_DIAS=30   HEALTHCHECK_URL=""        # opcional
```

1. Probar a mano: `/srv/backups/scripts/backup_supabase.sh` (debe terminar con `OK: ...` y dejar un `.dump`).
2. Programar (`crontab -e`, mismo usuario), por ejemplo todos los días a las 02:15:

```
   15 2 * * * /srv/backups/scripts/backup_supabase.sh >> /srv/backups/db/supabase_inspecciones/backup.log 2>&1
```

Limitaciones a tener presentes: el dump cubre solo el esquema `public` (los usuarios de Supabase Auth no van incluidos: se recrean a mano, son pocos); y el backup vive en el mismo servidor que las fotos, así que conviene una segunda copia fuera de él (ver sección 9). **Probar una restauración al menos una vez**: un backup que nunca se restauró no está probado. Para restaurar en un Postgres local de prueba hay que crear antes los roles que las políticas RLS referencian: `psql -c "create role anon; create role authenticated;"`, luego `createdb prueba` y `pg_restore --no-owner --no-privileges -d prueba <archivo>.dump`.

## 9. Cómo escalar desde acá

1. **Migraciones versionadas.** Usar Supabase CLI (`supabase migration new`, `supabase db push`) con la carpeta `ficha_web/supabase/migrations/`. Todo cambio de esquema va como archivo nuevo (`0002_…sql`), nunca editando la base a mano.
2. **Proyecto de staging.** Segundo proyecto (Free alcanza) para probar migraciones y la app antes de tocar producción.
3. **Catálogos en vez de texto libre.** `material`, `limpieza`, `acceso` son texto libre: a los pocos meses hay “Hormigón”, “hormigon” y “HORMIGÓN”. Cuando se estabilicen los valores, pasarlos a tablas de catálogo con FK (o `check … in (…)`), y en el formulario a `selectbox`.
4. **Roles.** Tabla `perfiles(user_id, rol)` y políticas RLS por rol (lector puede `select`; editor puede escribir). Reemplaza el `using (true)`.
5. **Tabla `fotos` (cache de Drive).** Si la resolución de fotos en tiempo real se vuelve lenta, una tabla `fotos(id_inspeccion, drive_file_id, nombre, tipo, nro_figura, modified_at)` llenada por un sync evita listar la carpeta en cada ficha (ver doc 03, sección 9).
6. **Auditoría.** Tabla `inspeccion_historial` con trigger que guarde el estado previo en cada update, si necesitan trazabilidad de quién cambió qué.
7. **Más campos de la ficha vieja.** El `Informe-OS.html` de QGIS tenía Nº Problema, Fecha de ingreso, Descripción, Introducción y datos del croquis. Se agregan como columnas nuevas (migración) sin tocar lo existente.
8. **Integración con PostGIS.** Si más adelante las inspecciones tienen que cruzarse con la red de colectores, la clave natural es `inspeccion.id` (N° de OS) contra la tabla de inspecciones del PostGIS propio; no hace falta mover datos, se puede cruzar por ID en una vista o exportando.