"""
ia/gemini_handler.py — Cliente para la API de Google Gemini (primaria) con soporte de timeout y Tool Calling.
"""
import requests
import json
from typing import Optional, Dict, Any, List


class GeminiHandler:
    def __init__(self, api_key: str | List[str], timeout: int = 20):
        if isinstance(api_key, list):
            self.api_keys = [k for k in api_key if k]
        elif isinstance(api_key, str) and api_key:
            self.api_keys = [api_key]
        else:
            self.api_keys = []
        self.api_key = self.api_keys[0] if self.api_keys else ""
        self.timeout = timeout

    def generar_respuesta(
        self,
        prompt: str,
        system_prompt: str = "",
        tools_declarations: List[Dict[str, Any]] = None,
        tools_executor = None
    ) -> Optional[str]:
        """Envía solicitud a Gemini usando la API REST oficial con soporte de Tool Calling / Function Calling."""
        if not self.api_keys:
            return None

        modelos = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

        for key in self.api_keys:
            for modelo in modelos:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={key}"
                headers = {"Content-Type": "application/json"}

            payload: Dict[str, Any] = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 800
                }
            }

            if system_prompt:
                payload["system_instruction"] = {
                    "parts": [{"text": system_prompt}]
                }

            if tools_declarations:
                payload["tools"] = [{"function_declarations": tools_declarations}]

            try:
                r = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                if r.status_code != 200:
                    continue

                data = r.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    continue

                model_content = candidates[0].get("content", {})
                parts = model_content.get("parts", [])
                if not parts:
                    continue

                # 1. Verificar si el modelo solicitó una o más llamadas a función (Tool Calling)
                func_calls = [p["functionCall"] for p in parts if "functionCall" in p]

                if func_calls and tools_executor:
                    response_parts = []
                    resultados_ejecucion = []

                    for fc in func_calls:
                        fn_name = fc.get("name")
                        fn_args = fc.get("args", {})
                        fc_id = fc.get("id")

                        fn_res = tools_executor.ejecutar_herramienta(fn_name, fn_args)
                        resultados_ejecucion.append((fn_name, fn_res))

                        fr_dict = {
                            "name": fn_name,
                            "response": {"result": fn_res}
                        }
                        if fc_id:
                            fr_dict["id"] = fc_id
                        response_parts.append({"functionResponse": fr_dict})

                    # Construir historial de conversación para la segunda fase
                    contents_step2 = [
                        payload["contents"][0],
                        model_content,
                        {
                            "role": "user",
                            "parts": response_parts
                        }
                    ]

                    payload_step2 = {
                        "contents": contents_step2,
                        "generationConfig": {
                            "temperature": 0.3,
                            "maxOutputTokens": 800
                        }
                    }
                    if system_prompt:
                        payload_step2["system_instruction"] = payload["system_instruction"]
                    if tools_declarations:
                        payload_step2["tools"] = payload["tools"]

                    try:
                        r2 = requests.post(url, headers=headers, json=payload_step2, timeout=self.timeout)
                        if r2.status_code == 200:
                            data2 = r2.json()
                            cands2 = data2.get("candidates", [])
                            if cands2:
                                parts2 = cands2[0].get("content", {}).get("parts", [])
                                for p2 in parts2:
                                    if "text" in p2 and p2["text"].strip():
                                        return p2["text"].strip()
                    except Exception:
                        pass

                    # Si el step 2 falló o dio error, formatear amablemente los resultados
                    mensajes_fall = []
                    for fn_name, fn_res in resultados_ejecucion:
                        if isinstance(fn_res, dict):
                            if "mensaje" in fn_res and isinstance(fn_res["mensaje"], str):
                                mensajes_fall.append(fn_res["mensaje"])
                            elif fn_res.get("encontrado"):
                                if "personas" in fn_res:
                                    lineas = [f"• {p.get('nombre')} ({p.get('rol')}) - {p.get('materia', '')} | Correo: {p.get('email', 'No especificado')}" for p in fn_res["personas"]]
                                    mensajes_fall.append("Información encontrada:\n" + "\n".join(lineas))
                                elif "mensajes" in fn_res:
                                    lineas = [f"• {m.get('remitente', 'Docente')} ({m.get('materia', 'Materia')}): {m.get('asunto', 'Mensaje')} [{m.get('fecha', '')}]" for m in fn_res["mensajes"]]
                                    mensajes_fall.append("Mensajes recibidos:\n" + "\n".join(lineas))
                                elif "actividades" in fn_res or "pendientes" in fn_res:
                                    acts = fn_res.get("pendientes", [])
                                    if acts:
                                        lineas = [f"• {a.get('materia')}: {a.get('titulo')} (Vence: {a.get('fecha', 'Sin fecha')})" for a in acts]
                                        mensajes_fall.append("Actividades pendientes:\n" + "\n".join(lineas))
                                    else:
                                        mensajes_fall.append("No tienes actividades pendientes de entrega.")
                                elif "docentes" in fn_res:
                                    lineas = [f"• {d.get('docente')} ({d.get('materia')})" for d in fn_res["docentes"]]
                                    mensajes_fall.append("Docentes encontrados:\n" + "\n".join(lineas))
                                elif "materia" in fn_res and "docente" in fn_res:
                                    mensajes_fall.append(f"El docente de {fn_res['materia']} es {fn_res['docente']}.")
                    if mensajes_fall:
                        return "\n\n".join(mensajes_fall)
                    return "No se encontraron resultados para la consulta."

                # 2. Si respondió directamente con texto
                for p in parts:
                    if "text" in p:
                        return p["text"].strip()

            except Exception:
                continue

        return None
