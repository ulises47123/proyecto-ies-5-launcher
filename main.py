"""
main.py — Punto de entrada principal del Campus Virtual IES N°5 Tello.
Soporte completo de System Tray (bandeja del sistema), notificaciones en segundo plano,
icono oficial, autologin, temporizador de actualización periódica y persistencia.
Adaptado y optimizado para Windows con CustomTkinter.
"""
import sys
import os
import time
import datetime
import logging
import threading
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
from ui.theme import aplicar_tema, tema_actual
from ui.login import LoginView
from ui.main_view import MainView
from ui.tutorial import TutorialWindow
from backend.session import CampusSession
from config import (cargar_creds, cargar_config, BASE_URL, LOGS_DIR,
                    cargar_cookies_sesion, guardar_cookies_sesion,
                    limpiar_datos_sesion, tutorial_ya_visto, marcar_tutorial_visto)

# ── CONFIGURACIÓN DEL SISTEMA DE LOGS ────────────────────────
def setup_logging():
    os.makedirs(LOGS_DIR, exist_ok=True)
    fecha_str = datetime.datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(LOGS_DIR, f"app_{fecha_str}.log")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Formato limpio y detallado
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Redirigir stdout y stderr para capturar salidas y excepciones globales
    class StreamToLogger:
        def __init__(self, level, original_stream):
            self.level = level
            self.original_stream = original_stream

        def write(self, message):
            msg = message.strip()
            if msg:
                logger.log(self.level, msg)
            try:
                if self.original_stream and not getattr(sys, 'frozen', False):
                    self.original_stream.write(message)
                    self.original_stream.flush()
            except Exception:
                pass

        def flush(self):
            try:
                if self.original_stream and not getattr(sys, 'frozen', False):
                    self.original_stream.flush()
            except Exception:
                pass

    sys.stdout = StreamToLogger(logging.INFO, sys.stdout)
    sys.stderr = StreamToLogger(logging.ERROR, sys.stderr)

    def global_excepthook(exctype, value, tb):
        import traceback
        err_msg = "".join(traceback.format_exception(exctype, value, tb))
        logging.critical(f"Excepción global no capturada:\n{err_msg}")
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "Error inesperado",
                "Ocurrió un error inesperado en la aplicación.\n\n"
                "El incidente ha sido registrado en los archivos de log.\n"
                f"Detalle: {value}"
            )
        except Exception:
            pass

    sys.excepthook = global_excepthook

    logging.info("==========================================")
    logging.info("Iniciando Campus Virtual IES N°5 Tello")
    logging.info(f"Ruta del ejecutable/script: {sys.argv}")
    logging.info("==========================================")

setup_logging()
from config import generar_archivo_informacion_desktop
generar_archivo_informacion_desktop()

try:
    import pystray
    from pystray import MenuItem as item
except ImportError:
    pystray = None

try:
    from plyer import notification
except ImportError:
    notification = None

ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Escudo-I.E.S.-N-5.png")


class AppWindow(ctk.CTk):
    def __init__(self, start_minimized: bool = False):
        super().__init__()
        self.title("Campus Virtual — IES N°5 José Eugenio Tello")
        self.geometry("1100x720")
        self.minsize(850, 580)

        # Configurar icono si existe
        if os.path.exists(ICON_PATH):
            try:
                from PIL import ImageTk
                img = Image.open(ICON_PATH)
                photo = ImageTk.PhotoImage(img)
                self.iconphoto(False, photo)
                self._icon_photo_ref = photo  # Keep reference
            except Exception:
                pass

        # Aplicar tema inicial guardado
        aplicar_tema()
        t = tema_actual()
        self.configure(fg_color=t["bg"])

        self.current_view = None
        self.campus_session = None
        self.tray_icon = None
        self._loop_running = True

        # Si se solicita inicio minimizado
        if start_minimized:
            self.withdraw()

        # Interceptar el botón de cerrar [X] de la ventana para minimizar a la bandeja (Requerimiento 9)
        self.protocol("WM_DELETE_WINDOW", self._on_close_window)

        # Manejador de excepciones de callbacks de Tkinter
        self.report_callback_exception = self._on_tk_exception

        self._mostrar_login()

        # Iniciar hilo de System Tray
        if pystray and os.path.exists(ICON_PATH):
            self._iniciar_tray_icon()

        # Iniciar temporizador de actualización periódica en segundo plano
        self._iniciar_timer_actualizacion()

        # Intentar restaurar sesión por cookies o autologin por credenciales
        self._intentar_autologin_completo()

    def _on_tk_exception(self, exctype, value, tb):
        """Manejador de excepciones generadas dentro del loop de eventos de Tkinter."""
        import traceback
        err_msg = "".join(traceback.format_exception(exctype, value, tb))
        logging.error(f"Excepción en UI / Callback:\n{err_msg}")
        try:
            from tkinter import messagebox
            messagebox.showwarning(
                "Aviso de Operación",
                f"Ocurrió un problema al procesar la acción:\n{value}\n\n"
                "La aplicación continuará funcionando normalmente."
            )
        except Exception:
            pass

    def _limpiar_vista(self):
        if self.current_view:
            self.current_view.destroy()
            self.current_view = None

    def _mostrar_login(self):
        self._limpiar_vista()
        self.campus_session = None
        self.current_view = LoginView(self, on_success=self._on_login_ok)
        self.current_view.pack(fill="both", expand=True)

    def _on_manual_logout(self):
        """Cierre de sesión manual: limpia datos sensibles de sesión y regresa al login."""
        limpiar_datos_sesion()
        self._mostrar_login()

    def _intentar_autologin_completo(self):
        """
        1. Intenta restaurar sesión rápida vía cookies guardadas.
        2. Si falla o expiró, intenta login por credenciales cifradas.
        3. Si no hay credenciales o falla, muestra la vista de login.
        """
        def run():
            campus = CampusSession()
            cookies = cargar_cookies_sesion()
            
            # Paso 1: probar restauración rápida por cookies
            if cookies:
                ok, _ = campus.restaurar_sesion_cookies(cookies)
                if ok:
                    # Sincronizar datos de usuario
                    from backend.user import get_current_user
                    get_current_user(campus)
                    self.after(0, self._on_login_ok, campus)
                    return

            # Paso 2: fallback a login por credenciales cifradas
            u, p = cargar_creds()
            if u and p:
                ok, msg = campus.login(u, p)
                if ok:
                    guardar_cookies_sesion(campus.http.cookies)
                    from backend.user import get_current_user
                    get_current_user(campus)
                    self.after(0, self._on_login_ok, campus)
                    return

        threading.Thread(target=run, daemon=True).start()

    def _on_login_ok(self, campus: CampusSession, solicitar_tutorial: bool = False):
        self._limpiar_vista()
        self.campus_session = campus
        self.current_view = MainView(self, campus, on_logout=self._on_manual_logout)
        self.current_view.pack(fill="both", expand=True)

        # Si el usuario solicitó el tutorial y aún no lo vio en esta instalación
        if solicitar_tutorial and not tutorial_ya_visto():
            self.after(200, self._mostrar_tutorial)

    def _mostrar_tutorial(self):
        try:
            TutorialWindow(self)
        except Exception:
            pass

    # ── BANDEJA DEL SISTEMA (SYSTEM TRAY) ────────────────────
    def _iniciar_tray_icon(self):
        def run_tray():
            try:
                img = Image.open(ICON_PATH)
                menu = pystray.Menu(
                    item('Abrir Campus Virtual', self._mostrar_desde_tray, default=True),
                    item('Actualizar datos', self._trigger_actualizacion_tray),
                    pystray.Menu.SEPARATOR,
                    item('Salir', self._salir_definitivo)
                )
                self.tray_icon = pystray.Icon("CampusVirtualIES5", img, "Campus Virtual IES N°5", menu)
                self.tray_icon.run()
            except Exception:
                pass

        threading.Thread(target=run_tray, daemon=True).start()

    def _on_close_window(self):
        cfg = cargar_config()
        if cfg.get("minimizar_al_cerrar", True) and self.tray_icon:
            self.withdraw()
            if notification:
                try:
                    notification.notify(
                        title="Campus Virtual IES N°5",
                        message="La aplicación continúa ejecutándose en segundo plano.",
                        app_name="Campus Virtual",
                        timeout=3
                    )
                except Exception:
                    pass
        else:
            self._salir_definitivo()

    def _mostrar_desde_tray(self, icon=None, item=None):
        self.after(0, self._restaurar_ventana)

    def _restaurar_ventana(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _trigger_actualizacion_tray(self, icon=None, item=None):
        if self.current_view and isinstance(self.current_view, MainView):
            self.after(0, self.current_view._refresh)

    def _salir_definitivo(self, icon=None, item=None):
        self._loop_running = False
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.after(0, self.destroy)
        sys.exit(0)

    # ── TEMPORIZADOR DE ACTUALIZACIÓN AUTOMÁTICA ─────────────
    def _iniciar_timer_actualizacion(self):
        def worker():
            while self._loop_running:
                cfg = cargar_config()
                minutos = cfg.get("intervalo_actualizacion", 10)
                if minutos <= 0:
                    time.sleep(30)
                    continue

                time.sleep(minutos * 60)

                if not self._loop_running:
                    break

                # Si está logueado, actualizar datos en segundo plano (MainView se encarga de notificar si hay novedades reales)
                if self.campus_session and self.current_view and isinstance(self.current_view, MainView):
                    self.after(0, self.current_view._load_datos)

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    start_min = "--minimized" in sys.argv or "-minimized" in sys.argv
    app = AppWindow(start_minimized=start_min)
    app.mainloop()

