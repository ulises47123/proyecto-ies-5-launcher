"""
services/contactos_service.py — Servicio de contactos, miembros de cursos y perfiles.
Responsabilidad unica (SRP): Obtener datos de docentes, compañeros, perfiles y exportacion CSV.
Contrato uniforme JSON: {"ok": True, "data": ...} / {"ok": False, "error": "..."}
"""
from typing import Dict, Any, Optional
from backend.session import CampusSession
from backend.contactos import get_contactos, get_detalle_contacto, exportar_contactos_csv


class ContactosService:
    """Gestiona los contactos de los cursos y la informacion de perfiles."""

    def __init__(self, session: CampusSession):
        self.session = session

    def get_contactos_curso(self, curso_id: str, forzar_recarga: bool = False) -> Dict[str, Any]:
        try:
            contactos = get_contactos(
                self.session, str(curso_id),
                obtener_detalles_completos=True,
                forzar_recarga=forzar_recarga
            )
            return {"ok": True, "data": contactos}
        except Exception as e:
            return {"ok": False, "error": f"Error al obtener contactos del curso {curso_id}: {str(e)}"}

    def get_perfil_usuario(self, curso_id: str, usuario_id: str) -> Dict[str, Any]:
        try:
            perfil = get_detalle_contacto(self.session, str(curso_id), str(usuario_id))
            return {"ok": True, "data": perfil}
        except Exception as e:
            return {"ok": False, "error": f"Error al obtener perfil del usuario {usuario_id}: {str(e)}"}

    def exportar_csv(self, contactos_data: dict, ruta_archivo: str) -> Dict[str, Any]:
        try:
            exportar_contactos_csv(contactos_data, ruta_archivo)
            return {"ok": True, "data": {"ruta": ruta_archivo}}
        except Exception as e:
            return {"ok": False, "error": f"Error al exportar contactos CSV: {str(e)}"}
