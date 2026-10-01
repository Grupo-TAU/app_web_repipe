from supabase import create_client

from .config import Config


def iniciar_sesion(cfg: Config, email: str, password: str):
    """Devuelve un cliente Supabase con la sesión del usuario (RLS aplica con su token)."""
    cliente = create_client(cfg.supabase_url, cfg.supabase_key)
    cliente.auth.sign_in_with_password({"email": email, "password": password})
    return cliente
