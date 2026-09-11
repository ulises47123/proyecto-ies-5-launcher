---
name: gemini-api-dev
description: >-
  Comprehensive guide and patterns for Google Gemini API development, multimodal prompts,
  tool calling (function calling), structured outputs, system instructions, and fallback handling.
---

# Google Gemini API Development Skill Guide

This skill provides production-grade instructions, code patterns, and best practices for integrating Google Gemini API models into Python and Web applications.

---

## 1. SDK Setup & Client Initialization

```python
import os
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_gemini_model(model_name: str = "gemini-1.5-flash", system_instruction: str = None):
    return genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_instruction
    )
```

---

## 2. Tool Calling (Function Calling)

Function calling allows Gemini to execute local Python functions or request specific API queries:

```python
def search_campus_database(query: str) -> dict:
    """Busca información en las materias y documentos del campus."""
    return {"status": "success", "results": [...]}

tools_list = [search_campus_database]

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    tools=tools_list
)

chat = model.start_chat(enable_automatic_function_calling=True)
response = chat.send_message("¿Cuáles son los temas de la materia Programación I?")
print(response.text)
```

---

## 3. Structured Outputs (JSON Response Schema)

To guarantee JSON responses matching a specific Pydantic or Schema dictionary:

```python
from pydantic import BaseModel, Field

class SummaryResponse(BaseModel):
    title: str = Field(description="Título del documento o noticia")
    key_points: list[str] = Field(description="Puntos clave extraídos")
    sentiment: str = Field(description="Sentimiento general: positivo, neutral, urgente")

model = genai.GenerativeModel("gemini-1.5-flash")
response = model.generate_content(
    "Analiza el siguiente aviso del campus...",
    generation_config=genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=SummaryResponse
    )
)
```

---

## 4. Robust Error Handling & Fallbacks

1. **API Key Verification**: Always verify if key exists before initializing `GenerativeModel`.
2. **Quota & Rate Limits**: Implement exponential backoff for HTTP 429/503 errors.
3. **Graceful Fallbacks**: If Gemini API call fails or key is missing, fallback gracefully to local offline search or prompt user to configure API key in settings.
