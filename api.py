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

    def check_auth(self) -> Dict[str, Any]:
        """Verifica si hay sesión activa."""
        return self.auth.is_authenticated()

    def restore_session(self) -> Dict[str, Any]:
        """Intenta restaurar la sesión guardada (cookies o credenciales)."""
        res = self.auth.restaurar_sesion_guardada()
        if res.get("ok"):
            self._init_servicios()
        return res

    def login(self, usuario: str, clave: str, recordar: bool = True, autologin: bool = True) -> Dict[str, Any]:
        """Autentica al usuario con sus credenciales."""
        res = self.auth.login_con_credenciales(usuario, clave, recordar, autologin)
        if res.get("ok"):
            self._init_servicios()
        return res

    def logout(self) -> Dict[str, Any]:
        """Cierra la sesión activa."""
        res = self.auth.logout()
        self._sess = None
        self._cursos = None
        return res

    def get_profile(self) -> Dict[str, Any]:
        """Obtiene el perfil del usuario autenticado."""
        return self.auth.get_user_profile()

    # ── Materias / Cursos ──

    def get_cursos(self, force: bool = False) -> Dict[str, Any]:
        """Obtiene la lista de materias y novedades del escritorio."""
        self._init_servicios()
        return self._cursos.get_cursos_y_novedades(forzar_recarga=force)

    def get_programa(self, curso_id: str) -> Dict[str, Any]:
        """Obtiene el programa (unidades e ítems) de una materia."""
        self._init_servicios()
        return self._cursos.get_programa(str(curso_id))

    # ── Contactos ──

    def get_contactos(self, curso_id: str, force: bool = False) -> Dict[str, Any]:
        """Obtiene el directorio de docentes y alumnos de un curso."""
        self._init_servicios()
        return self._contactos.get_contactos_curso(str(curso_id), forzar_recarga=force)

    def get_perfil(self, curso_id: str, usuario_id: str) -> Dict[str, Any]:
        """Obtiene el perfil detallado de un usuario de un curso."""
        self._init_servicios()
        return self._contactos.get_perfil_usuario(str(curso_id), str(usuario_id))

    # ── Actividades ──

    def get_actividad_detalle(self, url: str) -> Dict[str, Any]:
        """Obtiene el detalle de una actividad a partir de su URL."""
        self._init_servicios()
        return self._actividades.get_detalle_actividad(str(url))

    def get_pendientes(self) -> Dict[str, Any]:
        """Obtiene el registro de actividades pendientes guardadas localmente."""
        self._init_servicios()
        return self._actividades.get_registro_pendientes()

    # ── Calificaciones ──

    def get_calificaciones(self, curso_id: str) -> Dict[str, Any]:
        """Obtiene las calificaciones de un curso."""
        self._init_servicios()
        return self._calificaciones.get_calificaciones_curso(str(curso_id))

    # ── Mensajería ──

    def get_mensajes(self, curso_id: str, bandeja: str = "Inbox") -> Dict[str, Any]:
        """Obtiene la lista de mensajes de la bandeja indicada."""
        self._init_servicios()
        return self._mensajes.get_mensajes_bandeja(str(curso_id), bandeja)

    def get_mensaje_detalle(self, link_o_id: str, curso_id: str = "") -> Dict[str, Any]:
        """Obtiene el contenido completo de un mensaje."""
        self._init_servicios()
        return self._mensajes.get_detalle_mensaje(str(link_o_id), id_curso=str(curso_id))

    def enviar_mensaje(self, curso_id: str, destinatarios: str, asunto: str, cuerpo: str, archivo_adjunto: str = "") -> Dict[str, Any]:
        """Envía un nuevo mensaje de webmail."""
        self._init_servicios()
        adj = archivo_adjunto if archivo_adjunto and archivo_adjunto.strip() else None
        return self._mensajes.enviar_mensaje(str(curso_id), destinatarios, asunto, cuerpo, adj)

    def responder_mensaje(self, curso_id: str, email_id: str, destinatario_id: str, asunto: str, cuerpo: str) -> Dict[str, Any]:
        """Responde un mensaje del webmail."""
        self._init_servicios()
        return self._mensajes.responder(str(curso_id), str(email_id), str(destinatario_id), asunto, cuerpo)

    def reenviar_mensaje(self, curso_id: str, email_id: str, destinatario_id: str, asunto: str, nota: str = "") -> Dict[str, Any]:
        """Reenvía un mensaje del webmail."""
        self._init_servicios()
        return self._mensajes.reenviar(str(curso_id), str(email_id), str(destinatario_id), asunto, nota)

    def eliminar_mensaje(self, curso_id: str, email_id: str) -> Dict[str, Any]:
        """Mueve un mensaje a la papelera."""
        self._init_servicios()
        return self._mensajes.eliminar(str(curso_id), str(email_id))

    def vaciar_papelera(self, curso_id: str) -> Dict[str, Any]:
        """Vacía la papelera del webmail del curso."""
        self._init_servicios()
        return self._mensajes.vaciar_papelera(str(curso_id))

    # ── Sitio Institucional y Noticias ──

    def get_sitio_noticias(self, force: bool = False) -> Dict[str, Any]:
        """Obtiene noticias y recursos del sitio institucional."""
        self._init_servicios()
        return self._sitio.get_noticias(force=force)

    def obtener_noticias(self, force: bool = False) -> Dict[str, Any]:
        """Alias del contrato uniforme `obtener_noticias` de manual.md."""
        return self.get_sitio_noticias(force=force)

    def buscar_sitio(self, query: str, max_res: int = 10) -> Dict[str, Any]:
        """Busca en el sitio institucional."""
        self._init_servicios()
        return self._sitio.buscar_sitio(query, max_res)

    # ── Ajustes y Configuración ──

    def get_config(self) -> Dict[str, Any]:
        """Obtiene la configuración actual de la aplicación."""
        try:
            return {"ok": True, "data": cargar_config(), "error": None}
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}

    def save_config(self, cfg_json: str) -> Dict[str, Any]:
        """Guarda la configuración de la aplicación."""
        try:
            data = json.loads(cfg_json) if isinstance(cfg_json, str) else cfg_json
            guardar_config(data)
            return {"ok": True, "data": data, "error": None}
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}

    # ── Asistente IA ──

    def ask_ia(self, prompt: str) -> Dict[str, Any]:
        """Consulta al asistente de IA con el contexto del campus."""
        self._init_servicios()
        return self._ia.consultar(prompt)

    def consultar_ia(self, prompt: str) -> Dict[str, Any]:
        """Alias del contrato uniforme del Asistente IA."""
        return self.ask_ia(prompt)
