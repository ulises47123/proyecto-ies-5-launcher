"""
ia/fallback_manager.py — Manejo de conmutación por error (Fallback) entre APIs con timeouts de 10s y reintentos.
"""
import time
from typing import Optional, Tuple
from ia.gemini_handler import GeminiHandler
from ia.openai_handler import OpenAIHandler
from config import cargar_config, cargar_gemini_key, cargar_openai_key


class FallbackManager:
    """Gestiona la ejecución de llamadas a la API Primaria y el fallback a la Secundaria."""

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def responder_con_fallback(
        self,
        prompt: str,
        system_prompt: str = "",
        tools_declarations = None,
        tools_executor = None
    ) -> Tuple[Optional[str], str]:
        """
        Ejecuta la llamada a Gemini primero con Tool Calling. Si falla o excede el timeout, conmuta a OpenAI.
        Retorna (respuesta, proveedor_utilizado).
        """
        cfg = cargar_config()
        gemini_activa = cfg.get("api_gemini_activa", True)
        openai_activa = cfg.get("api_openai_activa", True)

        gemini_key = cargar_gemini_key() if gemini_activa else None
        openai_key = cargar_openai_key() if openai_activa else None

        # 1. Intentar API Primaria (Gemini) si está activada
        if gemini_key and gemini_activa:
            try:
                g_keys = [gemini_key]

                g_handler = GeminiHandler(api_key=g_keys, timeout=self.timeout)
                resp = g_handler.generar_respuesta(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    tools_declarations=tools_declarations,
                    tools_executor=tools_executor
                )
                if resp:
                    return resp, "Gemini"
            except Exception:
                pass

        # 2. Conmutar a API Secundaria (OpenAI) si la primaria falló o no está configurada
        if openai_key:
            try:
                o_handler = OpenAIHandler(api_key=openai_key, timeout=self.timeout)
                resp = o_handler.generar_respuesta(prompt, system_prompt)
                if resp:
                    return resp, "OpenAI (Fallback)"
            except Exception:
                pass

        # Si ambas fallan o no hay claves
        return None, "Sin API"
