-- =====================================================================
-- 0004_opciones_largo_300.sql
--   Las opciones de los desplegables (p. ej. descripciones de patologías) pueden
--   tener hasta 300 caracteres (antes 80). No modifica datos.
-- Ejecutar en el SQL Editor de Supabase (después de 0002).
-- =====================================================================

-- Se busca la restricción por su definición, sin depender de su nombre
do $$
declare c text;
begin
    for c in
        select conname from pg_constraint
        where conrelid = 'public.opciones'::regclass
          and contype = 'c'
          and pg_get_constraintdef(oid) ilike '%length%'
    loop
        execute format('alter table public.opciones drop constraint %I', c);
    end loop;
end $$;

alter table public.opciones
    add constraint opciones_valor_largo
    check (length(trim(valor)) between 1 and 300);
