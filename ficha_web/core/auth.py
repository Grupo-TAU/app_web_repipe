from supabase import create_client

from .config import Config

ROL_ADMIN = "admin"


def iniciar_sesion(cfg: Config, email: str, password: str):
    """Devuelve (cliente Supabase con la sesión del usuario, rol). RLS aplica con su token.

    El rol sale de `app_metadata.role` (solo editable con la service_role, no por el usuario).
    """
    cliente = create_client(cfg.supabase_url, cfg.supabase_key)
    respuesta = cliente.auth.sign_in_with_password({"email": email, "password": password})
    return cliente, (respuesta.user.app_metadata or {}).get("role", "")
