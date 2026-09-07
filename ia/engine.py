"""
ia/engine.py — Motor de IA unificado con IntelligentAgent y compatibilidad con UI.
"""
from typing import Dict, Any, List
from ia.agent import IntelligentAgent
from config import (
    cargar_api_key, cargar_gemini_key, cargar_openai_key,
    guardar_gemini_key, guardar_openai_key, borrar_gemini_key, borrar_openai_key
)


class IAEngine:
    def __init__(self, campus_session=None):
        self.campus = campus_session
        self.agent = IntelligentAgent(campus_session)
        self.cursos = []
        self.novedades = []

    def actualizar_datos(self, cursos: list, novedades: list, cache_data: dict = None):
        self.cursos = cursos
        self.novedades = novedades
        if cache_data and hasattr(self.agent, "context_mgr"):
            self.agent.context_mgr.set_extra_context("cache_data", cache_data)

    def responder(self, pregunta: str) -> str:
        return self.agent.procesar_consulta(pregunta)

    def tiene_api_activa(self) -> bool:
        return self.agent.tiene_api_activa()

    def tiene_api(self) -> bool:
        return self.agent.tiene_api_activa()

    def get_saludo_inicial(self) -> str:
        return self.agent.get_saludo_inicial()

