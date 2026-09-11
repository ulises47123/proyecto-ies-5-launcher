"""
services/actividades_service.py — Servicio para programas de materias, clases y seguimiento de actividades.
Responsabilidad unica (SRP): Consultar unidades, clases, consignas y monitoreo de actividades pendientes.
Contrato uniforme JSON: {"ok": True, "data": ...} / {"ok": False, "error": "..."}
"""
from typing import Dict, Any, List
from backend.session import CampusSession
import backend.programa as prog_mod
import backend.actividades_tracker as tracker_mod


class ActividadesService:
    """Gestiona contenidos de estudio, unidades didacticas y tareas pendientes."""

    def __init__(self, session: CampusSession):
        self.session = session

    def get_programa_materia(self, curso_id: str) -> Dict[str, Any]:
        try:
            programa = prog_mod.get_programa(self.session, str(curso_id))
            return {"ok": True, "data": programa}
        except Exception as e:
            return {"ok": False, "error": f"Error al obtener programa del curso {curso_id}: {str(e)}"}

    def get_detalle_actividad(self, url: str) -> Dict[str, Any]:
        try:
            detalle = prog_mod.get_detalle_actividad(self.session, url)
            return {"ok": True, "data": detalle}
        except Exception as e:
            return {"ok": False, "error": f"Error al obtener detalle de actividad: {str(e)}"}

    def get_contenido_texto(self, url: str) -> Dict[str, Any]:
        try:
            texto_info = prog_mod.get_contenido_texto(self.session, url)
            return {"ok": True, "data": texto_info}
        except Exception as e:
            return {"ok": False, "error": f"Error al obtener contenido de texto: {str(e)}"}

    def get_registro_pendientes(self) -> Dict[str, Any]:
        try:
            reg = tracker_mod.cargar_registro()
            return {"ok": True, "data": reg}
        except Exception as e:
            return {"ok": False, "error": f"Error al cargar registro de pendientes: {str(e)}"}

    def escanear_actividades_pendientes(self, cursos: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            res = tracker_mod.escanear_materias_pendientes(self.session, cursos)
            return {"ok": True, "data": res}
        except Exception as e:
            return {"ok": False, "error": f"Error al escanear actividades pendientes: {str(e)}"}
