"""
ia/agy_sidecar.py — Conector modular desacoplado para el Asistente Avanzado Antigravity CLI (AGY).
Cumple con la filosofía de responsabilidad única:
- Detección del ejecutable agy en el sistema.
- Instalación en segundo plano sin popups de consola.
- Control de autenticación y flujo de login vía navegador.
- Ejecución en modo de bajo consumo de tokens (--effort low).
- Persistencia de configuracion_actual.json.
- Deslogueo / limpieza de credenciales preservando el ejecutable.
"""
import os
import sys
import json
import shutil
import logging
import datetime
import subprocess
import webbrowser
from typing import Optional, Tuple, Callable

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".campus_tello")
AGY_CONFIG_FILE = os.path.join(CONFIG_DIR, "configuracion_actual.json")
INSTALL_CMD = 'powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://antigravity.google/cli/install.ps1 | iex"'
DEFAULT_MODEL = "gemini-3.8-flash-low"
DEFAULT_EFFORT = "low"


def _no_window_flags() -> int:
    """Retorna la bandera de creación de proceso sin ventana de consola en Windows."""
    if sys.platform == "win32":
        return subprocess.CREATE_NO_WINDOW
    return 0


def obtener_ruta_ejecutable() -> Optional[str]:
    """
    Busca la ruta absoluta de agy.exe en el sistema:
    1. En el PATH del sistema.
    2. En el directorio estándar %LOCALAPPDATA%\agy\bin\agy.exe.
    """
    which_path = shutil.which("agy") or shutil.which("agy.exe")
    if which_path and os.path.isfile(which_path):
        return os.path.abspath(which_path)

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        standard_path = os.path.join(local_app_data, "agy", "bin", "agy.exe")
        if os.path.isfile(standard_path):
            return standard_path

    user_profile = os.environ.get("USERPROFILE", "")
    if user_profile:
        fallback_path = os.path.join(user_profile, "AppData", "Local", "agy", "bin", "agy.exe")
        if os.path.isfile(fallback_path):
            return fallback_path

    return None


def esta_instalado() -> bool:
    """Devuelve True si agy.exe está instalado y accesible en la máquina."""
    return obtener_ruta_ejecutable() is not None


_last_auth_check_time = 0.0
_last_auth_check_val = False


def esta_autenticado(force: bool = False) -> bool:
    """
    Verifica si agy puede responder sin solicitar login.
    Ejecuta una consulta ligera de prueba ('ping') en modo low con caché de 60 segundos.
    """
    global _last_auth_check_time, _last_auth_check_val
    import time
    now = time.time()
    if not force and (now - _last_auth_check_time) < 60:
        return _last_auth_check_val

    exe = obtener_ruta_ejecutable()
    if not exe:
        _last_auth_check_val = False
        _last_auth_check_time = now
        return False

    try:
        res = subprocess.run(
            [exe, "--print", "ping", "--effort", "low"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            creationflags=_no_window_flags()
        )
        val = (res.returncode == 0 and "pong" in (res.stdout or "").lower())
        _last_auth_check_val = val
        _last_auth_check_time = now
        return val
    except Exception as e:
        logger.warning(f"Error al verificar autenticación de agy: {e}")
        return False


def instalar_en_segundo_plano(
    on_progreso: Optional[Callable[[str], None]] = None,
    on_completado: Optional[Callable[[bool, str], None]] = None
):
    """
    Ejecuta la instalación de AGY en segundo plano sin abrir ventanas CMD.
    Llama a on_progreso y on_completado al finalizar.
    """
    import threading

    def _worker():
        if on_progreso:
            on_progreso("Descargando componentes del Asistente Avanzado (AGY)...")
        try:
            proc = subprocess.run(
                INSTALL_CMD,
                shell=True,
                capture_output=True,
                text=True,
                creationflags=_no_window_flags(),
                timeout=180
            )
            if esta_instalado():
                if on_completado:
                    on_completado(True, "Instalación completada exitosamente.")
            else:
                err = proc.stderr.strip() if proc.stderr else "No se detectó el archivo ejecutable tras la instalación."
                if on_completado:
                    on_completado(False, err)
        except subprocess.TimeoutExpired:
            if on_completado:
                on_completado(False, "La descarga excedió el tiempo límite (timeout).")
        except Exception as ex:
            if on_completado:
                on_completado(False, str(ex))

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t


def abrir_navegador_login():
    """Abre el navegador por defecto para iniciar el flujo de autenticación de Google Antigravity."""
    login_url = "https://antigravity.google/login"
    try:
        webbrowser.open(login_url)
    except Exception as e:
        logger.error(f"Error al abrir navegador para login AGY: {e}")


def guardar_configuracion_actual(
    modelo: str = DEFAULT_MODEL,
    effort: str = DEFAULT_EFFORT,
    codigo_autorizacion: str = ""
) -> dict:
    """
    Crea o actualiza el archivo de configuración actual con el modelo, el modo low token
    y el código de autorización de Google, marcando los términos y onboarding como completados.
    """
    os.makedirs(CONFIG_DIR, exist_ok=True)
    cfg = {
        "asistente": "Google Antigravity CLI (AGY)",
        "modelo": modelo,
        "effort": effort,
        "consumo_tokens": "low",
        "descripcion": "Modo de bajo consumo de tokens configurado para conversaciones ágiles con el asistente.",
        "terminos_aceptados": True,
        "color_tema": "default",
        "onboarding_completado": True,
        "codigo_autorizacion": codigo_autorizacion.strip(),
        "autenticado": True,
        "fecha_configuracion": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(AGY_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Error guardando configuracion_actual.json: {e}")
    return cfg


def cargar_configuracion_actual() -> Optional[dict]:
    """Carga configuracion_actual.json si existe."""
    if os.path.exists(AGY_CONFIG_FILE):
        try:
            with open(AGY_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def borrar_sesion_agy():
    """
    Cierra la sesión de AGY y borra el archivo de configuración local del campus.
    NO modifica el sistema operativo, ni el ejecutable agy.exe ni las credenciales del host.
    """
    if os.path.exists(AGY_CONFIG_FILE):
        try:
            os.remove(AGY_CONFIG_FILE)
        except Exception:
            pass


def ejecutar_consulta(
    pregunta: str,
    contexto_sistema: str = "",
    modelo: str = DEFAULT_MODEL,
    effort: str = DEFAULT_EFFORT,
    timeout: int = 45
) -> Tuple[bool, str]:
    """
    Ejecuta una consulta al Asistente Avanzado AGY mediante subprocess silencioso.
    Retorna (éxito: bool, respuesta: str).
    """
    exe = obtener_ruta_ejecutable()
    if not exe:
        return False, "El Asistente Avanzado (AGY) no se encuentra instalado en este equipo."

    prompt_completo = ""
    if contexto_sistema:
        prompt_completo = f"INSTRUCCIONES Y CONTEXTO:\n{contexto_sistema}\n\nCONSULTA DEL ALUMNO:\n{pregunta}"
    else:
        prompt_completo = pregunta

    cmd = [
        exe,
        "--print", prompt_completo,
        "--effort", effort,
        "--model", modelo
    ]

    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=_no_window_flags()
        )

        if res.returncode == 0:
            salida = (res.stdout or "").strip()
            if salida:
                return True, salida
            return True, "No se recibió respuesta del Asistente Avanzado."
        else:
            err = (res.stderr or "").strip()
            return False, f"Error en AGY (código {res.returncode}): {err}"
    except subprocess.TimeoutExpired:
        return False, f"La consulta al Asistente Avanzado excedió el tiempo límite de {timeout} segundos."
    except Exception as ex:
        return False, f"Error al invocar el Asistente Avanzado: {ex}"
