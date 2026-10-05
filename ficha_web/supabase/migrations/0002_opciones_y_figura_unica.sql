-- =====================================================================
-- 0002_opciones_y_figura_unica.sql
--   1) Tabla `opciones`: valores de los desplegables (operario, material),
--      editable desde la app (página Configuración).
--   2) nro_figura único por inspección.
-- Ejecutar en el SQL Editor de Supabase (una sola vez).
-- =====================================================================

-- ---------- 1) Opciones de desplegables ------------------------------
-- Las inspecciones guardan el TEXTO elegido (sin FK): quitar una opción
-- no modifica inspecciones ya cargadas.

create table public.opciones (
    id          bigint generated always as identity primary key,
    categoria   text not null,                       -- 'operario', 'material', ...
    valor       text not null check (length(trim(valor)) between 1 and 80),
    created_at  timestamptz not null default now()
);

-- sin repetidos dentro de una categoría (sin distinguir mayúsculas)
create unique index opciones_categoria_valor_idx
    on public.opciones (categoria, lower(valor));

alter table public.opciones enable row level security;

create policy opciones_authenticated_all on public.opciones
    for all to authenticated using (true) with check (true);

grant select, insert, update, delete on public.opciones to authenticated;
grant usage, select on all sequences in schema public to authenticated;

insert into public.opciones (categoria, valor) values
    ('operario', 'FE'),
    ('operario', 'TP'),
    ('material', 'Hormigón'),
    ('material', 'PVC'),
    ('material', 'GRESS'),
    ('material', 'Hierro Fundido'),
    ('material', 'Gress - Hormigón'),
    ('material', 'Hormigón - PVC'),
    ('material', 'Gress - PVC'),
    ('material', 'Varios');

-- ---------- 2) nro_figura único por inspección -----------------------
-- Si ya hay figuras repetidas, el ALTER falla. Para encontrarlas:
--   select id_inspeccion, nro_figura, count(*)
--   from public.patologias where nro_figura is not null
--   group by 1, 2 having count(*) > 1;
-- (varias patologías SIN figura siguen permitidas: NULL no cuenta como repetido)

alter table public.patologias
    add constraint patologias_figura_unica unique (id_inspeccion, nro_figura);
