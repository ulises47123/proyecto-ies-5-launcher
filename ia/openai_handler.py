"""
ia/openai_handler.py — Cliente para la API de OpenAI (secundaria / fallback) con timeout y gestión de fallos.
"""
from typing import Optional, Dict, Any, List
import requests
import json


class OpenAIHandler:
    def __init__(self, api_key: str, timeout: int = 10, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.timeout = timeout
        self.model = model

    def generar_respuesta(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Envía solicitud a OpenAI con timeout estricto."""
        if not self.api_key:
            return None

        # Intentar con openai SDK primero
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key, timeout=self.timeout)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=800,
                temperature=0.3
            )
            if resp and resp.choices and resp.choices[0].message.content:
                return resp.choices[0].message.content.strip()
        except Exception:
            pass

        # Fallback a llamadas REST
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 800,
                "temperature": 0.3
            }
            r = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
        except Exception:
            return None
        return None
