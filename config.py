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
THEME_FILE  = os.path.join(CONFIG_DIR, "theme.json")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
CACHE_FILE          = os.path.join(CONFIG_DIR, "cache_materias.json")
CACHE_CONTACTOS_FILE= os.path.join(CONFIG_DIR, "cache_contactos.json")
USER_CACHE_FILE     = os.path.join(CONFIG_DIR, "user_cache.json")
COOKIES_FILE        = os.path.join(CONFIG_DIR, "cookies.json")
FB_CREDS_FILE       = os.path.join(CONFIG_DIR, "fb_creds")
CACHE_SITIO_FILE    = os.path.join(CONFIG_DIR, "cache_sitio_informativo.json")
CACHE_FB_FILE       = os.path.join(CONFIG_DIR, "cache_facebook.json")
ESTADO_NOTIFS_FILE  = os.path.join(CONFIG_DIR, "estado_notificaciones.json")
CACHE_SITIO_DIR     = os.path.join(CONFIG_DIR, "cache", "sitio")
CACHE_FB_IMG_DIR    = os.path.join(CONFIG_DIR, "cache", "facebook", "imagenes")
APP_DIR             = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR            = os.path.join(APP_DIR, "logs")

os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(CACHE_SITIO_DIR, exist_ok=True)
os.makedirs(CACHE_FB_IMG_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

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
}


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

    # 2. Fallback: credenciales.txt en el directorio de la app
    local_creds = os.path.join(os.path.dirname(__file__), "credenciales.txt")
    if os.path.exists(local_creds):
        try:
            with open(local_creds, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
                lines = text.splitlines()
                u, p = "", ""
                for l in lines:
                    if "usuario:" in l.lower():
                        u = l.split(":", 1)[1].strip()
                    elif any(k in l.lower() for k in ["contrasena:", "contraseña:", "contrcania:", "clave:"]):
                        p = l.split(":", 1)[1].strip()
                if u and p:
                    return u, p
                if len(lines) >= 2:
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


# ── POLÍTICAS DE LIMPIEZA DE DATOS Y CACHÉ ──
def limpiar_datos_sesion():
    """
    Política de Logout manual:
    Elimina cookies guardadas, user_cache.json y credenciales en disco.
    """
    borrar_cookies_sesion()
    borrar_creds()
    from backend.user import limpiar_user_cache
    limpiar_user_cache()


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
    """Cifra con DPAPI y guarda en ~/.campus_tello/api_key."""
    try:
        payload = clave.strip().encode('utf-8')
        enc = _dpapi_encrypt(payload)
        with open(API_KEY_FILE, "wb") as f:
            f.write(enc)
        try:
            os.chmod(API_KEY_FILE, 0o600)
        except Exception:
            pass
    except Exception:
        pass


def cargar_api_key() -> str | None:
    """Descifra y devuelve la clave API guardada con DPAPI o None si no existe."""
    if not os.path.exists(API_KEY_FILE):
        return None
    try:
        with open(API_KEY_FILE, "rb") as f:
            raw = f.read()
        dec = _dpapi_decrypt(raw)
        val = dec.decode('utf-8', errors='ignore').strip()
        return val if val else None
    except Exception:
        return None


def borrar_api_key():
    """Elimina el archivo de clave API cifrada."""
    if os.path.exists(API_KEY_FILE):
        try:
            os.remove(API_KEY_FILE)
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


# ── PERSISTENCIA CREDENCIALES FACEBOOK (DPAPI) ──
def guardar_fb_creds(usuario: str, clave: str):
    """Guarda credenciales de Facebook cifradas con DPAPI."""
    try:
        payload = f"{usuario.strip()}\n{clave.strip()}".encode('utf-8')
        enc = _dpapi_encrypt(payload)
        with open(FB_CREDS_FILE, "wb") as f:
            f.write(enc)
        try:
            os.chmod(FB_CREDS_FILE, 0o600)
        except Exception:
            pass
    except Exception:
        pass


def cargar_fb_creds() -> tuple[str, str]:
    """Carga y descifra las credenciales de Facebook."""
    if not os.path.exists(FB_CREDS_FILE):
        return "", ""
    try:
        with open(FB_CREDS_FILE, "rb") as f:
            raw = f.read()
        dec = _dpapi_decrypt(raw)
        lines = dec.decode('utf-8', errors='ignore').splitlines()
        return (lines[0].strip(), lines[1].strip()) if len(lines) >= 2 else ("", "")
    except Exception:
        return "", ""


def borrar_fb_creds():
    """Elimina las credenciales de Facebook guardadas."""
    if os.path.exists(FB_CREDS_FILE):
        try:
            os.remove(FB_CREDS_FILE)
        except Exception:
            pass


# ── CACHÉ SITIO INFORMATIVO Y FACEBOOK ──
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
        return {}


def guardar_cache_fb(data: dict):
    try:
        with open(CACHE_FB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass


def cargar_cache_fb() -> dict:
    if not os.path.exists(CACHE_FB_FILE):
        return {}
    try:
        with open(CACHE_FB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def generar_archivo_informacion_desktop():
    """Genera el archivo 'informacion.txt' en el escritorio del usuario según Requerimiento 3."""
    try:
        escritorio = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(escritorio):
            escritorio = os.path.expanduser("~")
        
        target_path = os.path.join(escritorio, "informacion.txt")
        
        contenido = (
            "INFORMACIÓN DEL CAMPUS VIRTUAL\n"
            "================================\n\n"
            "1. DESCRIPCIÓN GENERAL\n"
            "El programa permite acceder al campus virtual del I.E.S. Nº5 'José E. Tello' desde una interfaz de escritorio moderna y rápida.\n"
            "Entre sus funciones principales destacan:\n"
            "- Visualización y seguimiento de materias, clases y unidades académicas.\n"
            "- Acceso a actividades, consignas, rúbricas y estados de entrega (🟢 Entregada / 🟠 Pendiente / 🔴 Cerrada).\n"
            "- Mensajería interna (Webmail) con lectura completa de correos y archivos adjuntos.\n"
            "- Notificaciones nativas de escritorio del sistema operativo ante novedades reales (2 minutos de duración).\n"
            "- Asistente virtual inteligente (bot local con IA) con respuestas contextuales.\n\n"
            "2. TECNOLOGÍAS UTILIZADAS\n"
            "- Lenguaje: Python 3.11+\n"
            "- Interfaz gráfica de usuario: CustomTkinter (con soporte para 8 temas personalizables de alto contraste)\n"
            "- Conectividad HTTP: requests con adaptador de reintentos automáticos (HTTPAdapter con 3 reintentos y backoff)\n"
            "- Procesamiento HTML: BeautifulSoup4 para extracción estructurada de contenidos del aula\n"
            "- Almacenamiento en caché: Archivos JSON estructurados (cache_materias.json, cache_contactos.json, estado_notificaciones.json)\n"
            "- Sistema de notificaciones: Plyer / Notificaciones nativas del SO con duración temporizada\n"
            "- Imágenes y visualización: Pillow (PIL) y renderizado adaptativo\n\n"
            "3. ASISTENTE VIRTUAL (BOT LOCAL)\n"
            "Actualmente, el asistente local inteligente es capaz de:\n"
            "- Responder datos personales del estudiante ('¿Cómo me llamo?', '¿Cuál es mi DNI?', '¿Quién soy?').\n"
            "- Listar materias del ciclo lectivo actual junto con sus docentes a cargo y porcentaje de progreso.\n"
            "- Consultar actividades pendientes y tareas entregadas por materia.\n"
            "- Mostrar un resumen limpio de las novedades y avisos recientes del campus.\n"
            "Todas las consultas se resuelven en milisegundos a través de los datos cacheados localmente.\n\n"
            "4. POSIBLES MEJORAS CON IA EXTERNA\n"
            "Si se activa una clave de API externa (Google Gemini o OpenAI GPT), el asistente puede expandir sus capacidades:\n"
            "- Generar resúmenes automáticos y síntesis de lecturas obligatorias o unidades extensas.\n"
            "- Explicar conceptos técnicos y algoritmos en lenguaje natural adaptado al nivel del estudiante.\n"
            "- Resolver consultas complejas sobre consignas de trabajos prácticos.\n"
            "- Sugerir bibliografía complementaria y guías de estudio personalizadas.\n"
        )
        
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(contenido)
    except Exception:
        pass



