"""
ia/user_context.py — Manejo del contexto personalizado del usuario (sesión activa o caché).
"""
from typing import Dict, Any, List
from config import cargar_cache, USER_CACHE_FILE, cargar_cache_contactos
from backend.user import get_current_user
import os
import json


class UserContextManager:
    """Gestiona el perfil del estudiante, materias cursadas, progreso y preferencias."""

    def __init__(self, campus_session=None):
        self.campus = campus_session
        self._custom_context = {}

    def get_user_data(self) -> Dict[str, Any]:
        """Obtiene el perfil completo del usuario actual desde la sesión activa o caché."""
        # 1. Sesión activa
        if self.campus and getattr(self.campus, "logged_in", False):
            info = get_current_user(self.campus)
            if info.get("nombre") or info.get("dni"):
                return {
                    "nombre": info.get("nombre") or getattr(self.campus, "nombre", "Estudiante"),
                    "dni": info.get("dni") or getattr(self.campus, "usuario", ""),
                    "carrera": "Tecnicatura Superior en Soporte de Infraestructura de TI",
                    "institucion": "IES N°5 'José Eugenio Tello'"
                }

        # 2. Archivo de caché de usuario
        if os.path.exists(USER_CACHE_FILE):
            try:
                with open(USER_CACHE_FILE, "r", encoding="utf-8") as f:
                    u_data = json.load(f)
                    if u_data.get("nombre") or u_data.get("dni"):
                        return {
                            "nombre": u_data.get("nombre", "Estudiante"),
                            "dni": u_data.get("dni", ""),
                            "carrera": "Tecnicatura Superior en Soporte de Infraestructura de TI",
                            "institucion": "IES N°5 'José Eugenio Tello'"
                        }
            except Exception:
                pass

        # 3. Caché general
        cache = cargar_cache()
        nom = cache.get("usuario") or "Estudiante"
        return {
            "nombre": nom,
            "dni": "",
            "carrera": cache.get("carrera", "Tecnicatura Superior en Soporte de Infraestructura de TI"),
            "institucion": "IES N°5 'José Eugenio Tello'"
        }

    def get_user_name(self) -> str:
        """Obtiene el nombre de pila del estudiante."""
        udata = self.get_user_data()
        nombre = udata.get("nombre", "")
        if nombre:
            partes = nombre.replace(",", " ").split()
            for p in partes:
                if len(p) > 2 and not p.isdigit() and p.upper() not in ["LIC", "ING", "PROF"]:
                    return p.capitalize()
            return nombre.strip().title()
        return "Estudiante"

    def get_context(self) -> Dict[str, Any]:
        """Obtiene el diccionario completo de contexto para alimentar el prompt o herramientas."""
        cache = cargar_cache()
        cursos = cache.get("cursos", [])
        u_data = self.get_user_data()
        contactos_cache = cargar_cache_contactos()
        
        materias_activas = []
        for c in cursos:
            cid = str(c.get("id", ""))
            docentes = []
            
            # Buscar docentes en caché de contactos
            if cid in contactos_cache:
                doc_list = contactos_cache[cid].get("datos", {}).get("docentes", [])
                docentes = [d.get("nombre") for d in doc_list if d.get("nombre")]
            
            if not docentes and c.get("docente"):
                docentes = [c.get("docente")]
                
            materias_activas.append({
                "id": cid,
                "nombre": c.get("nombre"),
                "avance": c.get("avance", 0),
                "anio": c.get("anio"),
                "docentes": docentes or ["Docente a confirmar"]
            })

        return {
            "nombre_completo": u_data.get("nombre", "Estudiante"),
            "nombre_pila": self.get_user_name(),
            "dni": u_data.get("dni", ""),
            "carrera": u_data.get("carrera", "Tecnicatura Superior en Soporte de Infraestructura de TI"),
            "institucion": u_data.get("institucion", "IES N°5 'José Eugenio Tello'"),
            "total_materias": len(materias_activas),
            "materias": materias_activas,
            "calificaciones_registradas": list(cache.get("calificaciones", {}).keys()),
            "extra": self._custom_context
        }

    def set_extra_context(self, key: str, value: Any):
        self._custom_context[key] = value
