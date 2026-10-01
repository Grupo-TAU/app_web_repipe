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
