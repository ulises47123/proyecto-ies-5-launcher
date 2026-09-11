"""
config.py — Configuración global, temas, persistencia de ajustes, credenciales y rutas.
Totalmente adaptado para Windows y multiplataforma con codificación UTF-8.
"""
import os
import sys
import json
import requests
try:
    import winreg
except ImportError:
    winreg = None

BASE_URL  = "https://ies5tello-juj.infd.edu.ar/aula/"
LOGIN_URL = BASE_URL + "acceso.cgi"
DESK_URL  = BASE_URL + "escritorio.cgi"

CONFIG_DIR  = os.path.join(os.path.expanduser("~"), ".campus_tello")
CREDS_FILE  = os.path.join(CONFIG_DIR, "creds")
API_FILE    = os.path.join(CONFIG_DIR, "api")
API_KEY_FILE= os.path.join(CONFIG_DIR, "api_key")
GEMINI_KEY_FILE = os.path.join(CONFIG_DIR, "gemini_key")
OPENAI_KEY_FILE = os.path.join(CONFIG_DIR, "openai_key")
THEME_FILE  = os.path.join(CONFIG_DIR, "theme.json")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
CACHE_FILE          = os.path.join(CONFIG_DIR, "cache_materias.json")
CACHE_CONTACTOS_FILE= os.path.join(CONFIG_DIR, "cache_contactos.json")
USER_CACHE_FILE     = os.path.join(CONFIG_DIR, "user_cache.json")
COOKIES_FILE        = os.path.join(CONFIG_DIR, "cookies.json")
FB_CREDS_FILE       = os.path.join(CONFIG_DIR, "fb_creds")
CACHE_SITIO_FILE    = os.path.join(CONFIG_DIR, "cache_sitio_informativo.json")
ESTADO_NOTIFS_FILE  = os.path.join(CONFIG_DIR, "estado_notificaciones.json")
CACHE_SITIO_DIR     = os.path.join(CONFIG_DIR, "cache", "sitio")
APP_DIR             = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR            = os.path.join(APP_DIR, "logs")
DATA_DIR            = os.path.join(APP_DIR, "data")
DATA_ORIGINAL_DIR   = os.path.join(DATA_DIR, "original_files")
DATA_PROCESSED_DIR  = os.path.join(DATA_DIR, "processed")
DATA_KB_DIR         = os.path.join(DATA_DIR, "knowledge_base")
KB_JSON_FILE        = os.path.join(DATA_KB_DIR, "knowledge_base.json")

os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(CACHE_SITIO_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DATA_ORIGINAL_DIR, exist_ok=True)
os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)
os.makedirs(DATA_KB_DIR, exist_ok=True)

# ── Temas predefinidos con alto contraste y legibilidad optimizada ──
TEMAS_PREDEFINIDOS = {
    "Azul clásico": {
        "id": "midnight",
        "bg":           "#0e1626",
        "sidebar":      "#141f36",
        "card":         "#1b2a47",
        "accent":       "#2563eb",
        "accent_hover": "#1d4ed8",
        "btn_text":     "#ffffff",
        "success":      "#00cc66",
        "warning":      "#ff8800",
        "text":         "#f8fafc",
        "muted":        "#94a3b8",
        "border":       "#2d3f63",
        "item_bg":      "#101c33",
        "input_bg":     "#141f36",
        "is_dark":      True
    },
    "Neón": {
        "id": "cyberpunk",
        "bg":           "#12111a",
        "sidebar":      "#1a172a",
        "card":         "#251f3d",
        "accent":       "#e11d48",
        "accent_hover": "#be123c",
        "btn_text":     "#ffffff",
        "success":      "#00cc66",
        "warning":      "#ff8800",
        "text":         "#fdf4ff",
        "muted":        "#c4b5fd",
        "border":       "#3b2d61",
        "item_bg":      "#1b152e",
        "input_bg":     "#19152b",
        "is_dark":      True
    },
    "Esmeralda": {
        "id": "forest",
        "bg":           "#0b1c14",
        "sidebar":      "#122b20",
        "card":         "#1a3d2e",
        "accent":       "#059669",
        "accent_hover": "#047857",
        "btn_text":     "#ffffff",
        "success":      "#00cc66",
        "warning":      "#ff8800",
        "text":         "#f0fdf4",
        "muted":        "#86efac",
        "border":       "#245942",
        "item_bg":      "#0e241a",
        "input_bg":     "#122a1f",
        "is_dark":      True
    },
    "Ámbar": {
        "id": "sunset",
        "bg":           "#1a1412",
        "sidebar":      "#261c18",
        "card":         "#382822",
        "accent":       "#ea580c",
        "accent_hover": "#c2410c",
        "btn_text":     "#ffffff",
        "success":      "#00cc66",
        "warning":      "#ff8800",
        "text":         "#fff7ed",
        "muted":        "#fed7aa",
        "border":       "#52362b",
        "item_bg":      "#241712",
        "input_bg":     "#261c18",
        "is_dark":      True
    },
    "Turquesa": {
        "id": "ocean",
        "bg":           "#071a2c",
        "sidebar":      "#0c253e",
        "card":         "#133758",
        "accent":       "#06b6d4",
        "accent_hover": "#0891b2",
        "btn_text":     "#071a2c",
        "success":      "#00cc66",
        "warning":      "#ff8800",
        "text":         "#ecfeff",
        "muted":        "#a5f3fc",
        "border":       "#1e5180",
        "item_bg":      "#0a2239",
        "input_bg":     "#0c253e",
        "is_dark":      True
    },
    "Púrpura": {
        "id": "crimson",
        "bg":           "#200f21",
        "sidebar":      "#2e1530",
        "card":         "#431e46",
        "accent":       "#f43f5e",
        "accent_hover": "#e11d48",
        "btn_text":     "#ffffff",
        "success":      "#00cc66",
        "warning":      "#ff8800",
        "text":         "#fff1f2",
        "muted":        "#fecdd3",
        "border":       "#5c2a60",
        "item_bg":      "#28132a",
        "input_bg":     "#2e1530",
        "is_dark":      True
    },
    "Oliva": {
        "id": "nature_olive",
        "bg":           "#161c14",
        "sidebar":      "#202a1c",
        "card":         "#2d3d27",
        "accent":       "#84cc16",
        "accent_hover": "#65a30d",
        "btn_text":     "#161c14",
        "success":      "#00cc66",
        "warning":      "#ff8800",
        "text":         "#f7fee7",
        "muted":        "#bef264",
        "border":       "#3f5636",
        "item_bg":      "#1a2318",
        "input_bg":     "#202a1c",
        "is_dark":      True
    },
    "Modo claro": {
        "id": "light",
        "bg":           "#f1f5f9",
        "sidebar":      "#e2e8f0",
        "card":         "#ffffff",
        "accent":       "#2563eb",
        "accent_hover": "#1d4ed8",
        "btn_text":     "#ffffff",
        "success":      "#00cc66",
        "warning":      "#ff8800",
        "text":         "#0f172a",
        "muted":        "#475569",
        "border":       "#cbd5e1",
        "item_bg":      "#f8fafc",
        "input_bg":     "#ffffff",
        "is_dark":      False
    }
}

DEFAULT_THEME = TEMAS_PREDEFINIDOS["Azul clásico"]

DEFAULT_CONFIG = {
    "tema": "Azul clásico",
    "intervalo_actualizacion": 10,  # minutos (0 = desactivado, 5, 10, 30, 60)
    "iniciar_con_sistema": False,
    "mostrar_materias_anteriores": False,
    "minimizar_al_cerrar": True,
    "notificaciones_activas": True,
    "tutorial_visto": False,
    "solo_ia_api": False,  # True = Desactiva el bot local y usa exclusivamente modelos de IA API
    "api_gemini_activa": True,
    "api_openai_activa": True,
    "bot_local_activo": True,
    "usar_asistente_agy": False,  # Desmarcado por defecto en primer inicio
    "monitorear_actividades_pendientes": True,
    "intervalo_revision_actividades_dias": 1,  # días entre revisiones (1, 2, 3, 7)
    "recordatorio_frecuente_vencimiento": True,  # insistencia cuando vence pronto
    "intervalo_recordatorio_horas": 2,  # horas entre insistencias (1, 2, 4)
    "formato_hora_12h": True,  # True = 12h (AM/PM), False = 24h
}


def formatear_hora_str(texto_con_hora: str, usar_12h: bool = None) -> str:
    """
    Convierte horas dentro de un texto a formato 12h (AM/PM) o 24h según la configuración.
    Ejemplo: '09/09/2026 23:59' -> '09/09/2026 11:59 pm'
             'Abierta hasta 19:01' -> 'Abierta hasta 07:01 pm'
    """
    if not texto_con_hora:
        return ""
    if usar_12h is None:
        cfg = cargar_config()
        usar_12h = cfg.get("formato_hora_12h", True)

    import re

    def _replace_24_to_12(match):
        hh = int(match.group(1))
        mm = match.group(2)
        ampm = "am" if hh < 12 else "pm"
        hh12 = hh % 12
        if hh12 == 0:
            hh12 = 12
        return f"{hh12:02d}:{mm} {ampm}"

    def _replace_12_to_24(match):
        hh = int(match.group(1))
        mm = match.group(2)
        ampm = match.group(3).lower()
        if ampm == "pm" and hh < 12:
            hh += 12
        elif ampm == "am" and hh == 12:
            hh = 0
        return f"{hh:02d}:{mm}"

    if usar_12h:
        return re.sub(r'\b([01]?\d|2[0-3]):([0-5]\d)(?!\s*(?:am|pm|AM|PM))\b', _replace_24_to_12, str(texto_con_hora))
    else:
        return re.sub(r'\b(0?[1-9]|1[0-2]):([0-5]\d)\s*(am|pm|AM|PM)\b', _replace_12_to_24, str(texto_con_hora))


def cargar_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                cfg.update(saved)
        except Exception:
            pass
    return cfg


def guardar_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def tutorial_ya_visto() -> bool:
    """Devuelve True si el usuario ya vio el tutorial de bienvenida alguna vez."""
    cfg = cargar_config()
    return bool(cfg.get("tutorial_visto", False))


def marcar_tutorial_visto(visto: bool = True):
    """Guarda en la configuración el estado del tutorial visto."""
    cfg = cargar_config()
    cfg["tutorial_visto"] = visto
    guardar_config(cfg)


def set_autoinicio_windows(activar: bool) -> bool:
    """Configura o elimina el autoinicio de la app en el registro de Windows."""
    if not winreg:
        return False
    app_name = "CampusVirtualIES5"
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    if getattr(sys, 'frozen', False):
        exe_path = f'"{sys.executable}" --minimized'
    else:
        python_exe = sys.executable
        # Si se ejecuta con pythonw o python
        main_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
        pythonw_exe = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
        py_runner = pythonw_exe if os.path.exists(pythonw_exe) else python_exe
        exe_path = f'"{py_runner}" "{main_script}" --minimized'

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if activar:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        return False


def cargar_tema():
    if os.path.exists(THEME_FILE):
        try:
            with open(THEME_FILE, "r", encoding="utf-8") as f:
                t = json.load(f)
                merged = dict(DEFAULT_THEME)
                merged.update(t)
                return merged
        except Exception:
            pass
    return dict(DEFAULT_THEME)


def guardar_tema(tema: dict):
    try:
        with open(THEME_FILE, "w", encoding="utf-8") as f:
            json.dump(tema, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ── SISTEMA DE CIFRADO Y SEGURIDAD DE CREDENCIALES (DPAPI / Fallback) ──
def _dpapi_encrypt(data_bytes: bytes) -> bytes:
    """Cifra bytes usando la API nativa de protección de datos de Windows (DPAPI)."""
    if winreg is None:
        return data_bytes
    try:
        import ctypes
        import ctypes.wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [('cbData', ctypes.wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_byte))]

        data_in = DATA_BLOB(len(data_bytes), ctypes.cast(ctypes.create_string_buffer(data_bytes, len(data_bytes)), ctypes.POINTER(ctypes.c_byte)))
        data_out = DATA_BLOB()
        if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(data_in), 'CampusTelloSecurity', None, None, None, 0, ctypes.byref(data_out)):
            raise ctypes.WinError()
        buf = (ctypes.c_byte * data_out.cbData)()
        ctypes.memmove(buf, data_out.pbData, data_out.cbData)
        ctypes.windll.kernel32.LocalFree(data_out.pbData)
        return bytes(buf)
    except Exception:
        return data_bytes


def _dpapi_decrypt(data_bytes: bytes) -> bytes:
    """Descifra bytes cifrados con DPAPI."""
    if winreg is None:
        return data_bytes
    try:
        import ctypes
        import ctypes.wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [('cbData', ctypes.wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_byte))]

        data_in = DATA_BLOB(len(data_bytes), ctypes.cast(ctypes.create_string_buffer(data_bytes, len(data_bytes)), ctypes.POINTER(ctypes.c_byte)))
        data_out = DATA_BLOB()
        if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(data_in), None, None, None, None, 0, ctypes.byref(data_out)):
            raise ctypes.WinError()
        buf = (ctypes.c_byte * data_out.cbData)()
        ctypes.memmove(buf, data_out.pbData, data_out.cbData)
        ctypes.windll.kernel32.LocalFree(data_out.pbData)
        return bytes(buf)
    except Exception:
        return data_bytes


def guardar_creds(usuario: str, clave: str):
    """Guarda las credenciales cifradas con DPAPI y permisos de archivo seguros."""
    try:
        payload = f"{usuario.strip()}\n{clave.strip()}".encode('utf-8')
        enc = _dpapi_encrypt(payload)
        with open(CREDS_FILE, "wb") as f:
            f.write(enc)
        try:
            os.chmod(CREDS_FILE, 0o600)
        except Exception:
            pass
    except Exception:
        pass


def cargar_creds() -> tuple[str, str]:
    """Carga y descifra las credenciales de ~/.campus_tello/creds o fallback local."""
    # 1. Intentar desde ~/.campus_tello/creds (cifrado DPAPI)
    if os.path.exists(CREDS_FILE):
        try:
            with open(CREDS_FILE, "rb") as f:
                raw = f.read()
            # Intentar descifrar con DPAPI
            dec = _dpapi_decrypt(raw)
            text = dec.decode('utf-8', errors='ignore')
            lines = text.splitlines()
            if len(lines) >= 2 and lines[0].strip() and lines[1].strip():
                return lines[0].strip(), lines[1].strip()
        except Exception:
            pass

    return "", ""


def borrar_creds():
    """Elimina el archivo de credenciales cifradas."""
    if os.path.exists(CREDS_FILE):
        try:
            os.remove(CREDS_FILE)
        except Exception:
            pass


# ── PERSISTENCIA DE SESIÓN Y COOKIES ──
def guardar_cookies_sesion(session_cookies):
    """Serializa y guarda las cookies de requests.Session en COOKIES_FILE cifradas."""
    try:
        cookies_dict = requests.utils.dict_from_cookiejar(session_cookies) if hasattr(session_cookies, 'get_dict') or hasattr(session_cookies, 'items') else {}
        if not cookies_dict and hasattr(session_cookies, '__iter__'):
            cookies_dict = {c.name: c.value for c in session_cookies}
        
        raw_json = json.dumps(cookies_dict).encode('utf-8')
        enc = _dpapi_encrypt(raw_json)
        with open(COOKIES_FILE, "wb") as f:
            f.write(enc)
        try:
            os.chmod(COOKIES_FILE, 0o600)
        except Exception:
            pass
    except Exception:
        pass


def cargar_cookies_sesion() -> dict:
    """Carga y descifra las cookies guardadas de la sesión."""
    if not os.path.exists(COOKIES_FILE):
        return {}
    try:
        with open(COOKIES_FILE, "rb") as f:
            raw = f.read()
        dec = _dpapi_decrypt(raw)
        return json.loads(dec.decode('utf-8'))
    except Exception:
        return {}


def borrar_cookies_sesion():
    """Elimina el archivo de cookies persistidas."""
    if os.path.exists(COOKIES_FILE):
        try:
            os.remove(COOKIES_FILE)
        except Exception:
            pass


def tiene_sesion_guardada() -> bool:
    """Devuelve True si existen credenciales o cookies guardadas para autologueo."""
    u, p = cargar_creds()
    if u and p:
        return True
    cookies = cargar_cookies_sesion()
    return bool(cookies)


# ── POLÍTICAS DE LIMPIEZA DE DATOS Y CACHÉ ──
def limpiar_datos_sesion():
    """
    Política de Logout manual:
    Elimina cookies guardadas, user_cache.json, credenciales en disco y sesión de AGY.
    Conserva siempre el ejecutable agy.exe en disco.
    """
    borrar_cookies_sesion()
    borrar_creds()
    from backend.user import limpiar_user_cache
    limpiar_user_cache()
    try:
        from ia.agy_sidecar import borrar_sesion_agy
        borrar_sesion_agy()
    except Exception:
        pass
    try:
        cfg = cargar_config()
        cfg["usar_asistente_agy"] = False
        guardar_config(cfg)
    except Exception:
        pass


def limpiar_todas_caches():
    """Elimina absolutamente todas las cachés locales (materias, contactos, usuario, notificaciones)."""
    limpiar_datos_sesion()
    for fpath in [CACHE_FILE, CACHE_CONTACTOS_FILE, ESTADO_NOTIFS_FILE]:
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass


def guardar_api(provider, key):
    try:
        with open(API_FILE, "w", encoding="utf-8") as f:
            f.write(f"{provider}\n{key}\n")
        try:
            os.chmod(API_FILE, 0o600)
        except Exception:
            pass
    except Exception:
        pass


def cargar_api():
    if not os.path.exists(API_FILE):
        return "", ""
    try:
        with open(API_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        return (lines[0], lines[1]) if len(lines) >= 2 else ("", "")
    except Exception:
        return "", ""


def guardar_api_key(clave: str):
    """Cifra con DPAPI y guarda en ~/.campus_tello/api_key (Gemini principal)."""
    guardar_gemini_key(clave)


def cargar_api_key() -> str | None:
    """Descifra y devuelve la clave API guardada (Gemini principal) o None."""
    return cargar_gemini_key()


def borrar_api_key():
    """Elimina el archivo de clave API Gemini."""
    borrar_gemini_key()


def guardar_gemini_key(clave: str):
    try:
        payload = clave.strip().encode('utf-8')
        enc = _dpapi_encrypt(payload)
        with open(GEMINI_KEY_FILE, "wb") as f:
            f.write(enc)
        try:
            os.chmod(GEMINI_KEY_FILE, 0o600)
        except Exception:
            pass
    except Exception:
        pass


def cargar_gemini_key() -> str | None:
    if not os.path.exists(GEMINI_KEY_FILE):
        # Fallback al archivo antiguo api_key si existe
        if os.path.exists(API_KEY_FILE):
            try:
                with open(API_KEY_FILE, "rb") as f:
                    raw = f.read()
                dec = _dpapi_decrypt(raw)
                val = dec.decode('utf-8', errors='ignore').strip()
                if val:
                    return val
            except Exception:
                pass
        env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_KEY")
        if env_key:
            return env_key.strip()
        return None
    try:
        with open(GEMINI_KEY_FILE, "rb") as f:
            raw = f.read()
        dec = _dpapi_decrypt(raw)
        val = dec.decode('utf-8', errors='ignore').strip()
        return val if val else None
    except Exception:
        return None


def borrar_gemini_key():
    for path in [GEMINI_KEY_FILE, API_KEY_FILE]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


def guardar_openai_key(clave: str):
    try:
        payload = clave.strip().encode('utf-8')
        enc = _dpapi_encrypt(payload)
        with open(OPENAI_KEY_FILE, "wb") as f:
            f.write(enc)
        try:
            os.chmod(OPENAI_KEY_FILE, 0o600)
        except Exception:
            pass
    except Exception:
        pass


def cargar_openai_key() -> str | None:
    if not os.path.exists(OPENAI_KEY_FILE):
        return None
    try:
        with open(OPENAI_KEY_FILE, "rb") as f:
            raw = f.read()
        dec = _dpapi_decrypt(raw)
        val = dec.decode('utf-8', errors='ignore').strip()
        return val if val else None
    except Exception:
        return None


def borrar_openai_key():
    if os.path.exists(OPENAI_KEY_FILE):
        try:
            os.remove(OPENAI_KEY_FILE)
        except Exception:
            pass


from backend.cache_utils import guardar_cache_json, cargar_cache_json


def guardar_cache(data: dict):
    guardar_cache_json(CACHE_FILE, data)


def cargar_cache() -> dict:
    return cargar_cache_json(CACHE_FILE, dict)


def guardar_cache_contactos(data: dict):
    guardar_cache_json(CACHE_CONTACTOS_FILE, data)


def cargar_cache_contactos() -> dict:
    return cargar_cache_json(CACHE_CONTACTOS_FILE, dict)


def guardar_estado_notifs(data: dict):
    try:
        with open(ESTADO_NOTIFS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass


def cargar_estado_notifs() -> dict:
    if not os.path.exists(ESTADO_NOTIFS_FILE):
        return {"vistos": []}
    try:
        with open(ESTADO_NOTIFS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"vistos": []}


# ── CACHÉ SITIO INFORMATIVO ──
def guardar_cache_sitio(data: dict):
    try:
        with open(CACHE_SITIO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass


def cargar_cache_sitio() -> dict:
    if not os.path.exists(CACHE_SITIO_FILE):
        return {}
    try:
        with open(CACHE_SITIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        pass
    return {}


def generar_archivo_informacion_desktop(usuario: str = "", auto_login: bool = True):
    """
    Gestiona la persistencia según auto-logueo:
    - Auto-logueo = True: datos persisten internamente, no se crea archivo en escritorio.
    - Auto-logueo = False: se crea/actualiza archivo .txt en el escritorio con el nombre del estudiante.
    """
    try:
        escritorio = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(escritorio):
            escritorio = os.path.expanduser("~")

        nombre_archivo = f"{usuario.strip() or 'informacion'}.txt"
        target_path = os.path.join(escritorio, nombre_archivo)

        if auto_login:
            # Si auto-logueo está activo, no se debe generar/modificar archivo en el escritorio
            return

        cache = cargar_cache()
        nombre_completo = cache.get("usuario") or usuario or "Estudiante"
        carrera = cache.get("carrera", "IES N°5 'José E. Tello'")
        cursos = cache.get("cursos", [])

        mat_lines = []
        for c in cursos:
            nom = c.get("nombre", "")
            av = c.get("avance", 0)
            doc = c.get("docente", "A confirmar")
            mat_lines.append(f"- {nom} (Avance: {av}%) | Docente: {doc}")

        contenido = (
            f"INFORMACIÓN DEL ESTUDIANTE - CAMPUS VIRTUAL\n"
            f"============================================\n\n"
            f"Estudiante: {nombre_completo}\n"
            f"Institución / Carrera: {carrera}\n"
            f"Fecha de Exportación: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            f"MATERIAS REGISTRADAS:\n"
            + ("\n".join(mat_lines) if mat_lines else "- No se registran materias sincronizadas aún.") + "\n\n"
            f"ASISTENTE VIRTUAL Y SERVICIOS:\n"
            f"- Base de conocimiento local activa en el sistema.\n"
            f"- Integración con consultas académicas e institucionales.\n"
        )

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(contenido)
    except Exception:
        pass


def borrar_archivo_informacion_desktop(usuario: str = ""):
    """Borra el archivo .txt del escritorio cuando el usuario cierra sesión."""
    try:
        escritorio = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(escritorio):
            escritorio = os.path.expanduser("~")

        for fname in [f"{usuario.strip()}.txt", "informacion.txt"]:
            if usuario or fname == "informacion.txt":
                fpath = os.path.join(escritorio, fname)
                if os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
    except Exception:
        pass




