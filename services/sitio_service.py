"""
services/sitio_service.py — Servicio del sitio informativo publico institucional.
Responsabilidad unica (SRP): Obtener articulos, noticias y documentos del sitio publico del IES N°5.
Contrato uniforme JSON: {"ok": True, "data": ...} / {"ok": False, "error": "..."}
"""
from typing import Dict, Any
from backend.sitio_informativo import (
    SitioInformativoScraper, buscar_en_sitio_informativo
)
from config import cargar_cache_sitio


class SitioService:
    """Gestiona las noticias publicas y documentos institucionales."""

    def __init__(self):
        self.scraper = SitioInformativoScraper()

    def get_noticias_y_recursos(self, forzar_recarga: bool = False) -> Dict[str, Any]:
        try:
            if not forzar_recarga:
                cache = cargar_cache_sitio()
                if cache and cache.get("recursos"):
                    return {"ok": True, "data": cache}
            res = self.scraper.scrape_completo()
            return {"ok": True, "data": res}
        except Exception as e:
            return {"ok": False, "error": f"Error al obtener noticias del sitio: {str(e)}"}

    def buscar(self, query: str, max_resultados: int = 5) -> Dict[str, Any]:
        try:
            items = buscar_en_sitio_informativo(query, max_resultados=max_resultados)
            return {"ok": True, "data": items}
        except Exception as e:
            return {"ok": False, "error": f"Error en búsqueda: {str(e)}"}
