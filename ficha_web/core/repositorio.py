import json
from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import date
from pathlib import Path

from .config import RAIZ
from .modelos import Inspeccion, Observacion, Patologia, ResumenInspeccion, id_valido


OPCIONES_SEMILLA = {  # mismo contenido que supabase/migrations/0002 y 0003 (para el modo mock)
    "solicitante": ["SOMS - Intendencia de Montevideo"],
    "operario": ["FE", "TP"],
    "acceso": [],
    "limpieza": ["Si", "No"],
    "patologia": [],
    "material": ["Hormigón", "PVC", "GRESS", "Hierro Fundido", "Gress - Hormigón",
                 "Hormigón - PVC", "Gress - PVC", "Varios"],
}


class OpcionDuplicada(Exception):
    pass


def _figuras_repetidas(insp: Inspeccion) -> list[int]:
    figuras = [p.nro_figura for p in insp.patologias if p.nro_figura is not None]
    return sorted({f for f in figuras if figuras.count(f) > 1})


class Repositorio(ABC):
    @abstractmethod
    def obtener(self, id_inspeccion: str) -> Inspeccion | None: ...

    @abstractmethod
    def guardar(self, insp: Inspeccion) -> str: ...

    @abstractmethod
    def guardar_carpeta_drive(self, id_inspeccion: str, folder_id: str) -> None: ...

    @abstractmethod
    def listar_recientes(self, cantidad: int = 20) -> list[ResumenInspeccion]: ...

    @abstractmethod
    def listar_opciones(self, categoria: str) -> list[str]: ...

    @abstractmethod
    def agregar_opcion(self, categoria: str, valor: str) -> None: ...

    @abstractmethod
    def quitar_opcion(self, categoria: str, valor: str) -> None: ...


def a_payload(insp: Inspeccion) -> dict:
    """Payload de la RPC guardar_inspeccion."""
    return {
        "id": insp.id,
        "ubicacion": insp.ubicacion,
        "solicitante": insp.solicitante,
        "operario": insp.operario,
        "fecha": insp.fecha.isoformat() if insp.fecha else None,
        "acceso_1": insp.acceso_1,
        "acceso_2": insp.acceso_2,
        "diametro": insp.diametro,
        "material": insp.material,
        "largo": insp.largo,
        "limpieza": insp.limpieza,
        "conclusiones": insp.conclusiones,
        "drive_folder_id": insp.drive_folder_id,
        "observaciones": [{"obs_interna": o.obs_interna} for o in insp.observaciones],
        "patologias": [
            {"metros": p.metros, "patologia": p.patologia, "nro_figura": p.nro_figura}
            for p in insp.patologias
        ],
    }


def _resumen(d: dict) -> ResumenInspeccion:
    return ResumenInspeccion(
        id=d["id"], ubicacion=d["ubicacion"], operario=d.get("operario"),
        fecha=date.fromisoformat(d["fecha"]) if d.get("fecha") else None,
    )


def desde_payload(d: dict) -> Inspeccion:
    return Inspeccion(
        id=d["id"],
        ubicacion=d["ubicacion"],
        solicitante=d.get("solicitante"),
        operario=d.get("operario"),
        fecha=date.fromisoformat(d["fecha"]) if d.get("fecha") else None,
        acceso_1=d.get("acceso_1"),
        acceso_2=d.get("acceso_2"),
        diametro=d.get("diametro"),
        material=d.get("material"),
        largo=d.get("largo"),
        limpieza=d.get("limpieza"),
        conclusiones=d.get("conclusiones"),
        drive_folder_id=d.get("drive_folder_id"),
        observaciones=[Observacion(o["obs_interna"]) for o in d.get("observaciones", [])],
        patologias=[
            Patologia(p["patologia"], p.get("metros"), p.get("nro_figura"))
            for p in d.get("patologias", [])
        ],
    )


class MockRepositorio(Repositorio):
    """En memoria, precargado con la inspección 1001 del seed del doc 02."""

    def __init__(self, seed: Path = RAIZ / "fixtures" / "inspeccion_1001.json"):
        self._datos: dict[str, dict] = {}
        self._opciones = {c: list(v) for c, v in OPCIONES_SEMILLA.items()}
        self._orden: list[str] = []   # ids, del más viejo al más recién guardado
        if seed.exists():
            semilla = json.loads(seed.read_text(encoding="utf-8"))
            self._datos[semilla["id"]] = semilla
            self._orden.append(semilla["id"])

    def obtener(self, id_inspeccion):
        d = self._datos.get(id_inspeccion)
        return desde_payload(deepcopy(d)) if d else None

    def guardar(self, insp):
        if not id_valido(insp.id):
            raise ValueError("El ID solo admite letras, números, punto, guion y guion bajo")
        if rep := _figuras_repetidas(insp):
            raise ValueError("Figuras repetidas en la misma inspección: " + ", ".join(map(str, rep)))
        previo = self._datos.get(insp.id, {})
        nuevo = a_payload(insp)
        nuevo["drive_folder_id"] = nuevo["drive_folder_id"] or previo.get("drive_folder_id")
        self._datos[insp.id] = nuevo
        if insp.id in self._orden:
            self._orden.remove(insp.id)
        self._orden.append(insp.id)
        return insp.id

    def listar_recientes(self, cantidad=20):
        return [_resumen(self._datos[i]) for i in reversed(self._orden)][:cantidad]

    def guardar_carpeta_drive(self, id_inspeccion, folder_id):
        if id_inspeccion in self._datos:
            self._datos[id_inspeccion]["drive_folder_id"] = folder_id


    def listar_opciones(self, categoria):
        return list(self._opciones.get(categoria, []))

    def agregar_opcion(self, categoria, valor):
        lista = self._opciones.setdefault(categoria, [])
        if valor.casefold() in (v.casefold() for v in lista):
            raise OpcionDuplicada(valor)
        lista.append(valor)

    def quitar_opcion(self, categoria, valor):
        if valor in self._opciones.get(categoria, []):
            self._opciones[categoria].remove(valor)


class SupabaseRepositorio(Repositorio):
    """Usa un cliente ya autenticado con el usuario (para que RLS aplique)."""

    def __init__(self, cliente):
        self._sb = cliente

    def obtener(self, id_inspeccion):
        filas = self._sb.table("inspeccion").select("*").eq("id", id_inspeccion).limit(1).execute().data
        if not filas:
            return None
        base = filas[0]
        base["observaciones"] = (
            self._sb.table("observaciones").select("obs_interna")
            .eq("id_inspeccion", id_inspeccion).order("id").execute().data
        )
        base["patologias"] = (
            self._sb.table("patologias").select("metros,patologia,nro_figura")
            .eq("id_inspeccion", id_inspeccion).order("id").execute().data
        )
        return desde_payload(base)

    def listar_recientes(self, cantidad=20):
        filas = (
            self._sb.table("inspeccion").select("id,ubicacion,fecha,operario,updated_at")
            .order("updated_at", desc=True).limit(cantidad).execute().data
        )
        return [_resumen(f) for f in filas]

    def guardar(self, insp):
        # Una sola transacción en la base: upsert + reemplazo de hijas
        return self._sb.rpc("guardar_inspeccion", {"p": a_payload(insp)}).execute().data

    def guardar_carpeta_drive(self, id_inspeccion, folder_id):
        self._sb.table("inspeccion").update({"drive_folder_id": folder_id}).eq("id", id_inspeccion).execute()

    def listar_opciones(self, categoria):
        filas = self._sb.table("opciones").select("valor").eq("categoria", categoria).order("id").execute().data
        return [f["valor"] for f in filas]

    def agregar_opcion(self, categoria, valor):
        try:
            self._sb.table("opciones").insert({"categoria": categoria, "valor": valor}).execute()
        except Exception as e:
            if "23505" in str(e) or "duplicate" in str(e).lower():
                raise OpcionDuplicada(valor) from e
            raise

    def quitar_opcion(self, categoria, valor):
        self._sb.table("opciones").delete().eq("categoria", categoria).eq("valor", valor).execute()
