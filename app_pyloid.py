"""
app_pyloid.py — Punto de entrada paralelo para la GUI Web Híbrida estilo Discord.
Responsabilidad única (SRP): Orquestar la ventana Pyloid, registrar el adaptador IPC (CampusAPI)
y delegar las acciones a la capa services/ sin acoplamiento a HTML ni a detalles de scraping.
"""
import os
import sys
import json
import logging
from typing import Dict, Any

from pyloid import Pyloid
from pyloid.ipc import PyloidIPC, Bridge

# Importar la capa de servicios desacoplada (Fase 2)
from services import (
    AuthService, CursosService, ContactosService,
    ActividadesService, MensajesService, CalificacionesService,
    SitioService, IAService
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class CampusAPI(PyloidIPC):
    """
    Adaptador IPC para Pyloid.
    Responsabilidad única: Exponer funciones a JavaScript mediante JSON
    y delegar la ejecución a los servicios de dominio correspondientes.
    """

    def __init__(self):
        super().__init__()
        # Inicialización rápida: solo AuthService, sin network I/O al arrancar
        self.auth = AuthService()
        self._sess = None
        self._cursos = None
        self._contactos = None
        self._actividades = None
        self._mensajes = None
        self._calificaciones = None
        self._sitio = None
        self._ia = None

    def _init_servicios(self):
        """Inicializa los servicios de dominio de forma lazy (primera llamada)."""
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

    @property
    def cursos(self):
        self._init_servicios(); return self._cursos
    @property
    def contactos(self):
        self._init_servicios(); return self._contactos
    @property
    def actividades(self):
        self._init_servicios(); return self._actividades
    @property
    def mensajes(self):
        self._init_servicios(); return self._mensajes
    @property
    def calificaciones(self):
        self._init_servicios(); return self._calificaciones
    @property
    def sitio(self):
        self._init_servicios(); return self._sitio
    @property
    def ia(self):
        self._init_servicios(); return self._ia

    # ── Autenticación y Sesión ──
    @Bridge(result=str)
    def check_auth(self) -> str:
        return json.dumps(self.auth.is_authenticated())

    @Bridge(result=str)
    def restore_session(self) -> str:
        return json.dumps(self.auth.restaurar_sesion_guardada())

    @Bridge(str, str, bool, bool, result=str)
    def login(self, usuario: str, clave: str, recordar: bool, autologin: bool) -> str:
        res = self.auth.login_con_credenciales(usuario, clave, recordar, autologin)
        return json.dumps(res)

    @Bridge(result=str)
    def logout(self) -> str:
        return json.dumps(self.auth.logout())

    @Bridge(result=str)
    def get_profile(self) -> str:
        return json.dumps(self.auth.get_user_profile())

    # ── Cursos y Escritorio ──
    @Bridge(bool, result=str)
    def get_cursos(self, forzar: bool = False) -> str:
        return json.dumps(self.cursos.get_cursos_y_novedades(forzar_recarga=forzar))

    # ── Contactos y Miembros ──
    @Bridge(str, bool, result=str)
    def get_contactos(self, curso_id: str, forzar: bool = False) -> str:
        return json.dumps(self.contactos.get_contactos_curso(curso_id, forzar_recarga=forzar))

    @Bridge(str, str, result=str)
    def get_perfil(self, curso_id: str, usuario_id: str) -> str:
        return json.dumps(self.contactos.get_perfil_usuario(curso_id, usuario_id))

    # ── Actividades y Clases ──
    @Bridge(str, result=str)
    def get_programa(self, curso_id: str) -> str:
        return json.dumps(self.actividades.get_programa_materia(curso_id))

    @Bridge(str, result=str)
    def get_actividad_detalle(self, url: str) -> str:
        return json.dumps(self.actividades.get_detalle_actividad(url))

    @Bridge(result=str)
    def get_pendientes(self) -> str:
        return json.dumps(self.actividades.get_registro_pendientes())

    # ── Calificaciones ──
    @Bridge(str, result=str)
    def get_calificaciones(self, curso_id: str) -> str:
        return json.dumps(self.calificaciones.get_calificaciones_curso(curso_id))

    # ── Mensajería / Webmail ──
    @Bridge(str, str, result=str)
    def get_mensajes(self, curso_id: str, bandeja: str = "Inbox") -> str:
        return json.dumps(self.mensajes.get_mensajes_bandeja(curso_id, bandeja=bandeja))

    # ── Sitio Institucional ──
    @Bridge(bool, result=str)
    def get_sitio_noticias(self, forzar: bool = False) -> str:
        return json.dumps(self.sitio.get_noticias_y_recursos(forzar_recarga=forzar))

    # ── Inteligencia Artificial ──
    @Bridge(str, result=str)
    def ask_ia(self, pregunta: str) -> str:
        return json.dumps(self.ia.consultar(pregunta))


    # ── Mensajería Avanzada (Detalle, Enviar, Responder, Reenviar, Eliminar, Vaciar) ──
    @Bridge(str, str, result=str)
    def get_mensaje_detalle(self, link_o_id: str, id_curso: str = "") -> str:
        return json.dumps(self.mensajes.get_detalle_mensaje(link_o_id, id_curso=id_curso))

    @Bridge(str, str, str, str, str, result=str)
    def enviar_mensaje(self, id_curso: str, destinatarios: str, asunto: str, cuerpo: str, archivo_adjunto: str = "") -> str:
        adj = archivo_adjunto if archivo_adjunto.strip() else None
        return json.dumps(self.mensajes.enviar_mensaje(id_curso, destinatarios, asunto, cuerpo, adj))

    @Bridge(str, str, str, str, str, result=str)
    def responder_mensaje(self, id_curso: str, id_email: str, destinatario_id: str, asunto: str, cuerpo: str) -> str:
        return json.dumps(self.mensajes.responder(id_curso, id_email, destinatario_id, asunto, cuerpo))

    @Bridge(str, str, str, str, str, result=str)
    def reenviar_mensaje(self, id_curso: str, id_email: str, destinatario_id: str, asunto: str, nota: str = "") -> str:
        return json.dumps(self.mensajes.reenviar(id_curso, id_email, destinatario_id, asunto, nota))

    @Bridge(str, str, result=str)
    def eliminar_mensaje(self, id_curso: str, id_email: str) -> str:
        return json.dumps(self.mensajes.eliminar(id_curso, id_email))

    @Bridge(str, result=str)
    def vaciar_papelera(self, id_curso: str) -> str:
        return json.dumps(self.mensajes.vaciar_papelera(id_curso))

    # ── Búsqueda en Sitio Institucional ──
    @Bridge(str, int, result=str)
    def buscar_sitio(self, query: str, max_res: int = 10) -> str:
        return json.dumps(self.sitio.buscar(query, max_resultados=max_res))


def main():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    html_file = os.path.join(app_dir, "web_gui", "index.html")

    if not os.path.exists(html_file):
        print(f"Error: No se encontró el archivo HTML en {html_file}")
        sys.exit(1)

    app = Pyloid(app_name="CampusTello-Launcher")

    # Crear ventana principal con adaptador IPC registrado
    window = app.create_window(
        title="launcher oficial ies N° 5",
        width=1280,
        height=850,
        dev_tools=False,
        IPCs=[CampusAPI()]
    )

    # Cargar interfaz web oficial estilo Stitch Midnight
    window.load_file(html_file)
    window.show()
    window.focus()

    app.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback
        err_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_error.log")
        with open(err_path, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
            f.write(f"\nError: {exc}\n")
        print(f"[FATAL] Error al iniciar. Ver: {err_path}")
        input("Presione Enter para salir...")
        sys.exit(1)
