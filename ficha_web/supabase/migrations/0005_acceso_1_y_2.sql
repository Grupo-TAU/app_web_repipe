-- =====================================================================
-- 0005_acceso_1_y_2.sql
--   `acceso` pasa a `acceso_1` (conserva los datos) y se agrega `acceso_2`.
--   Se actualiza guardar_inspeccion, que referencia esas columnas.
-- (Ya ejecutada en el proyecto de Supabase de producción.)
-- =====================================================================
begin;

alter table public.inspeccion rename column acceso to acceso_1;
alter table public.inspeccion add column acceso_2 text;

create or replace function public.guardar_inspeccion(p jsonb)
returns text
language plpgsql
security invoker
set search_path = public
as $$
declare
    v_id text := nullif(trim(p->>'id'), '');
begin
    if v_id is null then
        raise exception 'El id de inspección es obligatorio';
    end if;

    insert into public.inspeccion (
        id, ubicacion, solicitante, operario, fecha, acceso_1, acceso_2,
        diametro, material, largo, limpieza, conclusiones, drive_folder_id
    )
    values (
        v_id,
        p->>'ubicacion',
        nullif(p->>'solicitante', ''),
        nullif(p->>'operario', ''),
        nullif(p->>'fecha', '')::date,
        nullif(p->>'acceso_1', ''),
        nullif(p->>'acceso_2', ''),
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
        acceso_1        = excluded.acceso_1,
        acceso_2        = excluded.acceso_2,
        diametro        = excluded.diametro,
        material        = excluded.material,
        largo           = excluded.largo,
        limpieza        = excluded.limpieza,
        conclusiones    = excluded.conclusiones,
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

commit;
