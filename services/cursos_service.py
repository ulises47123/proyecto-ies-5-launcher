"""
services/cursos_service.py — Servicio para la obtencion y consulta de cursos / materias del usuario.
Responsabilidad unica (SRP): Obtener, estructurar y consultar informacion sobre los cursos, programas y novedades.
Contrato uniforme JSON: {"ok": True, "data": ...} / {"ok": False, "error": "..."}
"""
from typing import Dict, Any, Optional
from backend.session import CampusSession
from backend.escritorio import get_escritorio
from backend.programa import get_programa as fetch_programa
from config import cargar_cache, guardar_cache


class CursosService:
    """Gestiona las materias / cursos, programa temático y novedades del usuario."""

    def __init__(self, session: CampusSession):
        self.session = session

    def get_cursos_y_novedades(self, page_size: int = 120, forzar_recarga: bool = False) -> Dict[str, Any]:
        try:
            if not forzar_recarga:
                cache = cargar_cache()
                if cache and cache.get("materias"):
                    return {
                        "ok": True,
                        "data": {
                            "cursos": cache.get("materias", []),
                            "novedades": cache.get("novedades", []),
                            "origen": "cache"
                        },
                        "error": None
                    }

            cursos, novedades, nombre = get_escritorio(self.session, page_size=page_size)
            guardar_cache({"materias": cursos, "novedades": novedades})
            return {
                "ok": True,
                "data": {
                    "cursos": cursos,
                    "novedades": novedades,
                    "usuario_nombre": nombre,
                    "origen": "red"
                },
                "error": None
            }
        except Exception as e:
            return {"ok": False, "data": None, "error": f"Error al obtener escritorio: {str(e)}"}

    def get_cursos(self, force: bool = False) -> Dict[str, Any]:
        """Alias compatible con la API pywebview (js_api)."""
        return self.get_cursos_y_novedades(forzar_recarga=force)

    def get_curso_por_id(self, curso_id: str) -> Dict[str, Any]:
        res = self.get_cursos_y_novedades(forzar_recarga=False)
        if not res.get("ok"):
            return res
        for c in res.get("data", {}).get("cursos", []):
            if str(c.get("id", "")) == str(curso_id):
                return {"ok": True, "data": c, "error": None}
        return {"ok": False, "data": None, "error": f"Curso con ID {curso_id} no encontrado."}

    def get_programa(self, curso_id: str) -> Dict[str, Any]:
        """Obtiene las unidades pedagógicas, clases y recursos de una asignatura."""
        try:
            unidades = fetch_programa(self.session, str(curso_id))
            return {"ok": True, "data": unidades, "error": None}
        except Exception as e:
            return {"ok": False, "data": None, "error": f"Error al obtener programa del curso {curso_id}: {str(e)}"}
