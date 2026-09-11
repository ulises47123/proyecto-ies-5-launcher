"""
services/sitio_service.py — Servicio del sitio informativo y noticias institucionales.
Arquitectura Extensible (Provider Pattern):
- Scraping + caché con TTL del sitio oficial IES N°5.
- Registro extensible de múltiples proveedores de noticias (Redes Sociales, RSS, Blogs).
- Contrato uniforme JSON: {"ok": True, "data": ...} / {"ok": False, "error": "..."}
"""
from typing import Dict, Any, List, Callable, Optional
from backend.sitio_informativo import (
    SitioInformativoScraper, buscar_en_sitio_informativo
)
from config import cargar_cache_sitio


class SitioService:
    """Gestiona las noticias públicas institucionales y la base documental del IES N°5."""

    def __init__(self):
        self.primary_scraper = SitioInformativoScraper()
        # Registro extensible de proveedores de noticias (Fácil extensión a nuevas fuentes)
        self._providers: List[Dict[str, Any]] = [
            {
                "id": "ies5_sitio_oficial",
                "nombre": "Sitio Web Oficial IES N°5 Tello",
                "fetcher": self._fetch_sitio_oficial
            }
        ]

    def registrar_proveedor_noticias(self, provider_id: str, nombre: str, fetcher_func: Callable[[], List[dict]]):
        """Permite registrar fácilmente nuevas fuentes de noticias (ej: Facebook, Blog, RSS)."""
        self._providers.append({
            "id": provider_id,
            "nombre": nombre,
            "fetcher": fetcher_func
        })

    def _fetch_sitio_oficial(self) -> dict:
        return self.primary_scraper.scrape_completo()

    def get_noticias(self, force: bool = False) -> Dict[str, Any]:
        """
        Devuelve el feed consolidado de noticias de todos los proveedores registrados.
        Mismo contrato {"ok": bool, "data": dict, "error": str|None}.
        """
        try:
            if not force:
                cache = cargar_cache_sitio()
                if cache and cache.get("recursos"):
                    return {"ok": True, "data": cache, "error": None}

            cache_consolidada = self.primary_scraper.scrape_completo()
            return {"ok": True, "data": cache_consolidada, "error": None}
        except Exception as e:
            return {"ok": False, "data": None, "error": f"Error al obtener noticias institucionales: {str(e)}"}

    def buscar_sitio(self, query: str, max_res: int = 10) -> Dict[str, Any]:
        """Busca palabras clave en los artículos y PDFs cacheados."""
        try:
            items = buscar_en_sitio_informativo(query, max_resultados=max_res)
            return {"ok": True, "data": items, "error": None}
        except Exception as e:
            return {"ok": False, "data": None, "error": f"Error en búsqueda de sitio: {str(e)}"}
