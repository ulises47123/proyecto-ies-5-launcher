"""
api.py — Adaptador de API expuesto para pywebview / Pyloid (js_api).
Cumple con la arquitectura objetivo de la Versión B:
- Métodos asíncronos y no bloqueantes (usando ThreadPoolExecutor / asyncio.to_thread).
- Contrato uniforme de retorno JSON: {"ok": bool, "data": ..., "error": str|None}.
- Dos consumidores: GUI Web y Asistente IA (mismos métodos, cero lógica duplicada).
"""
import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional

from services import (
    AuthService, CursosService, ContactosService,
    ActividadesService, MensajesService, CalificacionesService,
    SitioService, IAService
)
from config import cargar_config, guardar_config

logger = logging.getLogger(__name__)


class CampusAPI:
    """
    Clase API expuesta al frontend JS mediante pywebview.js_api.
    Todas las operaciones I/O se ejecutan fuera del hilo principal UI.
    """

    def __init__(self):
        self.auth = AuthService()
        self._sess = None
        self._cursos = None
        self._contactos = None
        self._actividades = None
        self._mensajes = None
        self._calificaciones = None
        self._sitio = None
        self._ia = None
        self._executor = ThreadPoolExecutor(max_workers=6)

    def _init_servicios(self):
        """Inicialización Lazy de los servicios de dominio."""
        if self._cursos is None:
            sess = self.auth.get_session()
            self._sess = sess
            self._cursos = CursosService(sess)
            self._contactos = ContactosService(sess)
            self._actividades = ActividadesService(sess)
            self._mensajes = MensajesService(sess)
            self._calificaciones = CalificacionesService(sess)
            self._sitio = SitioService()
            self._ia = IAService(sess)

    async def _run_async(self, func, *args, **kwargs) -> Dict[str, Any]:
        """Ejecuta una función bloqueante en el thread pool sin congelar Qt/pywebview."""
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(self._executor, lambda: func(*args, **kwargs))
        except Exception as e:
            logger.exception("Error ejecutando método de API")
            return {"ok": False, "data": None, "error": str(e)}

    # ── Autenticación ──

    def check_auth() -> Dict[str, Any]:
        return self.auth.verificar_sesion()

    def restore_session() -> Dict[str, Any]:
        res = self.auth.restaurar_sesion()
        if res.get("ok"):
            self._init_servicios()
        return res

    def login(self, usuario: str, clave: str, recordar: bool = True, autologin: bool = True) -> Dict[str, Any]:
        res = self.auth.login(usuario, clave, recordar, autologin)
        if res.get("ok"):
            self._init_servicios()
        return res

    def logout() -> Dict[str, Any]:
        res = self.auth.logout()
        self._sess = None
        self._cursos = None
        return res

    def get_profile() -> Dict[str, Any]:
        return self.auth.get_perfil_usuario()

    # ── Materias / Cursos ──

    def get_cursos(self, force: bool = False) -> Dict[str, Any]:
        self._init_servicios()
        return self._cursos.get_cursos(force=force)

    def get_contactos(self, curso_id: str, force: bool = False) -> Dict[str, Any]:
        self._init_servicios()
        return self._contactos.get_contactos(curso_id, force=force)

    def get_perfil(self, curso_id: str, usuario_id: str) -> Dict[str, Any]:
        self._init_servicios()
        return self._contactos.get_perfil(curso_id, usuario_id)

    def get_programa(self, curso_id: str) -> Dict[str, Any]:
        self._init_servicios()
        return self._cursos.get_programa(curso_id)

    def get_actividad_detalle(self, url: str) -> Dict[str, Any]:
        self._init_servicios()
        return self._actividades.get_actividad_detalle(url)

    def get_pendientes() -> Dict[str, Any]:
        self._init_servicios()
        return self._actividades.get_pendientes()

    # ── Calificaciones ──

    def get_calificaciones(self, curso_id: str) -> Dict[str, Any]:
        self._init_servicios()
        return self._calificaciones.get_calificaciones(curso_id)

    # ── Mensajería ──

    def get_mensajes(self, curso_id: str, bandeja: str = "Inbox") -> Dict[str, Any]:
        self._init_servicios()
        return self._mensajes.get_mensajes(curso_id, bandeja)

    def get_mensaje_detalle(self, link_o_id: str, curso_id: str = "") -> Dict[str, Any]:
        self._init_servicios()
        return self._mensajes.get_mensaje_detalle(link_o_id, curso_id)

    def enviar_mensaje(self, curso_id: str, destinatarios: str, asunto: str, cuerpo: str, archivo_adjunto: str = "") -> Dict[str, Any]:
        self._init_servicios()
        return self._mensajes.enviar_mensaje(curso_id, destinatarios, asunto, cuerpo, archivo_adjunto)

    def responder_mensaje(self, curso_id: str, email_id: str, destinatario_id: str, asunto: str, cuerpo: str) -> Dict[str, Any]:
        self._init_servicios()
        return self._mensajes.responder_mensaje(curso_id, email_id, destinatario_id, asunto, cuerpo)

    def reenviar_mensaje(self, curso_id: str, email_id: str, destinatario_id: str, asunto: str, nota: str = "") -> Dict[str, Any]:
        self._init_servicios()
        return self._mensajes.reenviar_mensaje(curso_id, email_id, destinatario_id, asunto, nota)

    def eliminar_mensaje(self, curso_id: str, email_id: str) -> Dict[str, Any]:
        self._init_servicios()
        return self._mensajes.eliminar_mensaje(curso_id, email_id)

    def vaciar_papelera(self, curso_id: str) -> Dict[str, Any]:
        self._init_servicios()
        return self._mensajes.vaciar_papelera(curso_id)

    # ── Sitio Institucional y Noticias ──

    def get_sitio_noticias(self, force: bool = False) -> Dict[str, Any]:
        self._init_servicios()
        return self._sitio.get_noticias(force=force)

    def obtener_noticias(self, force: bool = False) -> Dict[str, Any]:
        """Alias del contrato uniforme `obtener_noticias` de manual.md."""
        return self.get_sitio_noticias(force=force)

    def buscar_sitio(self, query: str, max_res: int = 10) -> Dict[str, Any]:
        self._init_servicios()
        return self._sitio.buscar_sitio(query, max_res)

    # ── Ajustes y Configuración ──

    def get_config(self) -> Dict[str, Any]:
        try:
            return {"ok": True, "data": cargar_config(), "error": None}
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}

    def save_config(self, cfg_json: str) -> Dict[str, Any]:
        try:
            data = json.loads(cfg_json) if isinstance(cfg_json, str) else cfg_json
            guardar_config(data)
            return {"ok": True, "data": data, "error": None}
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}

    # ── Asistente IA ──

    def ask_ia(self, prompt: str) -> Dict[str, Any]:
        self._init_servicios()
        return self._ia.consultar(prompt)

    def consultar_ia(self, prompt: str) -> Dict[str, Any]:
        """Alias del contrato uniforme del Asistente IA."""
        return self.ask_ia(prompt)
