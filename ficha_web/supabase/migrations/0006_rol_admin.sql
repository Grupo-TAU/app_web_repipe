-- Rol admin: la app lee app_metadata.role al iniciar sesión (solo editable con service_role/SQL).
-- Los admins ven la página Seguimiento. Para sumar o quitar uno, repetir con su email
-- (quitar: raw_app_meta_data = raw_app_meta_data - 'role').
update auth.users
   set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || '{"role": "admin"}'::jsonb
 where lower(email) in ('bwerner@dica.com.uy', 'nalonso@dica.com.uy');
