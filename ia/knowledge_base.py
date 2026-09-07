"""
ia/knowledge_base.py — Gestión y consulta de la base de conocimiento local (knowledge_base.json).
"""
import os
import json
from typing import Dict, Any, List
from config import KB_JSON_FILE


class KnowledgeBaseManager:
    """Maneja la lectura y búsqueda semántica/léxica en la base de conocimiento."""

    def __init__(self, kb_file: str = KB_JSON_FILE):
        self.kb_file = kb_file

    def cargar_datos(self) -> Dict[str, Any]:
        if not os.path.exists(self.kb_file):
            return {"documentos": []}
        try:
            with open(self.kb_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"documentos": []}

    def listar_documentos(self) -> List[Dict[str, Any]]:
        """Devuelve la lista de documentos con sus metadatos e índices."""
        data = self.cargar_datos()
        res = []
        for doc in data.get("documentos", []):
            res.append({
                "titulo": doc.get("titulo", ""),
                "fuente": doc.get("fuente", ""),
                "tipo": doc.get("tipo", "general"),
                "materia": doc.get("materia", ""),
                "indice": doc.get("indice", [])
            })
        return res

    def buscar_en_indice(self, consulta: str) -> List[Dict[str, Any]]:
        """Busca en el índice y títulos de los documentos cargados."""
        consulta_lower = consulta.lower()
        palabras = [p for p in consulta_lower.split() if len(p) > 2]
        data = self.cargar_datos()
        coincidencias = []

        for doc in data.get("documentos", []):
            score = 0
            titulo = doc.get("titulo", "").lower()
            materia = doc.get("materia", "").lower()
            indice = [str(item).lower() for item in doc.get("indice", [])]
            contenido = doc.get("contenido", "").lower()

            for p in palabras:
                if p in titulo:
                    score += 5
                if p in materia:
                    score += 4
                for item in indice:
                    if p in item:
                        score += 3
                if p in contenido[:1000]:
                    score += 1

            if score > 0:
                coincidencias.append({
                    "score": score,
                    "titulo": doc.get("titulo"),
                    "fuente": doc.get("fuente"),
                    "materia": doc.get("materia"),
                    "tipo": doc.get("tipo"),
                    "indice": doc.get("indice", []),
                    "extracto": doc.get("contenido", "")[:300] + "..."
                })

        coincidencias.sort(key=lambda x: x["score"], reverse=True)
        return coincidencias

    def obtener_contenido_completo(self, titulo_o_fuente: str) -> Dict[str, Any]:
        """Obtiene el documento completo por coincidencia exacta o parcial de título o fuente."""
        query = titulo_o_fuente.strip().lower()
        data = self.cargar_datos()
        
        for doc in data.get("documentos", []):
            if query == doc.get("titulo", "").lower() or query == doc.get("fuente", "").lower():
                return doc
        
        for doc in data.get("documentos", []):
            if query in doc.get("titulo", "").lower() or query in doc.get("fuente", "").lower():
                return doc
                
        return {}

    def guardar_documento(self, doc_data: Dict[str, Any]) -> bool:
        """Guarda o actualiza un documento en la base de conocimiento."""
        data = self.cargar_datos()
        documentos = data.get("documentos", [])
        
        # Actualizar si ya existe por fuente o titulo
        actualizado = False
        for i, doc in enumerate(documentos):
            if doc.get("fuente") == doc_data.get("fuente") or (doc.get("titulo") and doc.get("titulo") == doc_data.get("titulo")):
                documentos[i] = doc_data
                actualizado = True
                break
        if not actualizado:
            documentos.append(doc_data)
            
        data["documentos"] = documentos
        try:
            os.makedirs(os.path.dirname(self.kb_file), exist_ok=True)
            with open(self.kb_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
