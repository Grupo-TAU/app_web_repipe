-- =====================================================================
-- 0003_mas_opciones.sql
--   Nuevas categorías de desplegables editables desde la app:
--   solicitante, acceso, limpieza y patologia (la tabla `opciones` ya existe, ver 0002).
--   Solo se cargan valores iniciales de las que se conocen; el resto se
--   completa desde la página Configuración de la app.
-- Ejecutar en el SQL Editor de Supabase (una sola vez, después de 0002).
-- =====================================================================

insert into public.opciones (categoria, valor) values
    ('solicitante', 'SOMS - Intendencia de Montevideo'),
    ('limpieza', 'Si'),
    ('limpieza', 'No')
on conflict do nothing;

-- Índice para el listado de últimas inspecciones (página Fichas)
create index if not exists inspeccion_updated_at_idx on public.inspeccion (updated_at desc);
