"""
services/calificaciones_service.py — Servicio de calificaciones y notas academicas.
Responsabilidad unica (SRP): Consulta de calificaciones y notas por curso.
Contrato uniforme JSON: {"ok": True, "data": ...} / {"ok": False, "error": "..."}
"""
from typing import Dict, Any
from backend.session import CampusSession
from backend.calificaciones import get_calificaciones


class CalificacionesService:
    """Gestiona las notas y evaluaciones de materias."""

    def __init__(self, session: CampusSession):
        self.session = session

    def get_calificaciones_curso(self, curso_id: str) -> Dict[str, Any]:
        try:
            califs = get_calificaciones(self.session, str(curso_id))
            return {"ok": True, "data": califs}
        except Exception as e:
            return {"ok": False, "error": f"Error al obtener calificaciones del curso {curso_id}: {str(e)}"}
