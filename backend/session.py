"""
backend/session.py — Manejo de sesión HTTP con el campus.
Login, cookies, requests autenticados.
"""
import requests
import hashlib
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import LOGIN_URL, BASE_URL


class CampusSession:
    """Maneja la sesión autenticada con el campus."""

    def __init__(self):
        self.http = requests.Session()
        self.http.headers['User-Agent'] = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        # Reintentos automáticos (Requerimiento 1)
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.http.mount('https://', adapter)
        self.http.mount('http://', adapter)

        self.logged_in = False
        self.usuario   = ""
        self.nombre    = ""

    def login(self, usuario: str, clave: str) -> tuple[bool, str]:
        """Intenta login. Devuelve (ok, mensaje_error)."""
        try:
            md5 = hashlib.md5(clave.strip().encode('utf-8')).hexdigest()
            r = self.http.post(LOGIN_URL, data={
                "wIdSeccion": "82",
                "id_curso":   "",
                "wAccion":    "login",
                "wIdUsuario": usuario.strip(),
                "wClaveUsuarioPlana": "",
                "wClaveUsuario":     md5,
            }, timeout=20, allow_redirects=True)
            if "escritorio.cgi" in r.text or "escritorio" in r.url:
                self.logged_in = True
                self.usuario   = usuario.strip()
                return True, "OK"
            return False, "Usuario o contraseña incorrectos."
        except requests.exceptions.ConnectionError:
            return False, "No tienes conexión a internet. Conéctate y vuelve a intentarlo."
        except requests.exceptions.Timeout:
            return False, "Tu conexión a internet es inestable. Por favor, verifica tu red."
        except Exception as e:
            return False, str(e)

    def restaurar_sesion_cookies(self, cookies_dict: dict) -> tuple[bool, str]:
        """
        Intenta restaurar la sesión usando cookies serializadas previamente.
        Verifica si la sesión sigue activa haciendo una petición liviana a escritorio.cgi.
        """
        if not cookies_dict:
            return False, "No hay cookies guardadas."
        try:
            self.http.cookies.clear()
            self.http.cookies.update(cookies_dict)
            
            # Petición de prueba para comprobar vigencia de la cookie de sesión
            r = self.http.get(self.url("escritorio.cgi"), timeout=12, allow_redirects=True)
            if "acceso.cgi" in r.url or "wAccion=login" in r.text or "acceso" in r.url:
                self.http.cookies.clear()
                self.logged_in = False
                return False, "La sesión ha expirado."
            
            if "escritorio" in r.url or "escritorio.cgi" in r.text or "AccesoGrupos" in r.text:
                self.logged_in = True
                return True, "OK"

            return False, "No se pudo validar la sesión."
        except Exception as e:
            return False, str(e)

    def get(self, url: str, **kwargs) -> requests.Response:
        """GET autenticado con reintentos y captura amigable."""
        kwargs.setdefault('timeout', 25)
        try:
            return self.http.get(url, **kwargs)
        except requests.exceptions.Timeout:
            raise RuntimeError("Tu conexión a internet es inestable. Por favor, verifica tu red.")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("No tienes conexión a internet. Conéctate y vuelve a intentarlo.")

    def post(self, url: str, **kwargs) -> requests.Response:
        """POST autenticado con reintentos y captura amigable."""
        kwargs.setdefault('timeout', 25)
        try:
            return self.http.post(url, **kwargs)
        except requests.exceptions.Timeout:
            raise RuntimeError("Tu conexión a internet es inestable. Por favor, verifica tu red.")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("No tienes conexión a internet. Conéctate y vuelve a intentarlo.")

    def url(self, path: str) -> str:
        """Construye URL completa del campus."""
        return BASE_URL + path
