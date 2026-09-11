"""
services/ia_service.py — Servicio de Inteligencia Artificial y asistente pedagogico.
Responsabilidad unica (SRP): Orquestar el agente inteligente, Tool Calling y respuestas de IA.
Contrato uniforme JSON: {"ok": True, "data": ...} / {"ok": False, "error": "..."}
"""
from typing import Dict, Any, Optional
from backend.session import CampusSession
from ia.agent import IntelligentAgent


class IAService:
    """Gestiona las consultas inteligentes del usuario y asistencia pedagogica."""

    def __init__(self, session: Optional[CampusSession] = None):
        self.agent = IntelligentAgent(campus_session=session)

    def tiene_api_activa(self) -> Dict[str, Any]:
        try:
            activa = bool(self.agent.tiene_api_activa())
            return {"ok": True, "data": {"activa": activa}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_saludo_inicial(self) -> Dict[str, Any]:
        try:
            saludo = self.agent.get_saludo_inicial()
            return {"ok": True, "data": {"saludo": saludo}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def consultar(self, pregunta: str) -> Dict[str, Any]:
        pregunta = (pregunta or "").strip()
        if not pregunta:
            return {"ok": False, "error": "La pregunta no puede estar vacía."}
        try:
            respuesta = self.agent.procesar_consulta(pregunta)
            return {"ok": True, "data": {"respuesta": respuesta}}
        except Exception as e:
            return {"ok": False, "error": f"Error al procesar consulta con IA: {str(e)}"}
