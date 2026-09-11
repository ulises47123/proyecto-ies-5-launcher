"""
services/auth_service.py — Servicio de autenticacion y gestion de sesion de usuario.
Responsabilidad unica (SRP): Orquestar el login, restauracion y cierre de sesion.
Contrato uniforme JSON: {"ok": True, "data": ...} / {"ok": False, "error": "..."}
"""
from typing import Dict, Any, Optional
from backend.session import CampusSession
from config import (
    guardar_creds, borrar_creds, cargar_creds,
    guardar_cookies_sesion, cargar_cookies_sesion, borrar_cookies_sesion,
    guardar_config, cargar_config
)
from backend.user import get_current_user, limpiar_user_cache


class AuthService:
    """Gestiona la autenticacion y el ciclo de vida de la sesion."""

    def __init__(self, session: Optional[CampusSession] = None):
        self.session = session or CampusSession()

    def get_session(self) -> CampusSession:
        return self.session

    def is_authenticated(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "data": {
                "authenticated": getattr(self.session, "logged_in", False),
                "usuario": getattr(self.session, "usuario", ""),
                "nombre": getattr(self.session, "nombre", "")
            }
        }

    def login_con_credenciales(self, usuario: str, clave: str, recordar: bool = False, autologin: bool = False) -> Dict[str, Any]:
        usuario = (usuario or "").strip()
        clave = (clave or "").strip()
        if not usuario or not clave:
            return {"ok": False, "error": "Debes ingresar usuario y contraseña."}

        try:
            ok, msg = self.session.login(usuario, clave)
            if ok:
                if recordar:
                    guardar_creds(usuario, clave)
                else:
                    borrar_creds()

                cfg = cargar_config()
                cfg["autologin"] = autologin
                guardar_config(cfg)

                guardar_cookies_sesion(self.session.http.cookies)

                profile = {}
                try:
                    profile = get_current_user(self.session, force_network=True)
                except Exception:
                    pass

                return {
                    "ok": True,
                    "data": {
                        "mensaje": "Inicio de sesión exitoso.",
                        "usuario": self.session.usuario,
                        "nombre": self.session.nombre,
                        "profile": profile
                    }
                }
            return {"ok": False, "error": msg or "Credenciales incorrectas."}
        except Exception as e:
            return {"ok": False, "error": f"Error de conexión: {str(e)}"}

    def restaurar_sesion_guardada(self) -> Dict[str, Any]:
        try:
            cookies = cargar_cookies_sesion()
            if cookies:
                ok, msg = self.session.restaurar_sesion_cookies(cookies)
                if ok:
                    profile = get_current_user(self.session)
                    return {
                        "ok": True,
                        "data": {
                            "metodo": "cookies",
                            "mensaje": "Sesión restaurada mediante cookies.",
                            "profile": profile
                        }
                    }

            u, p = cargar_creds()
            if u and p:
                ok, msg = self.session.login(u, p)
                if ok:
                    guardar_cookies_sesion(self.session.http.cookies)
                    profile = get_current_user(self.session)
                    return {
                        "ok": True,
                        "data": {
                            "metodo": "credenciales",
                            "mensaje": "Sesión restaurada mediante credenciales guardadas.",
                            "profile": profile
                        }
                    }

            return {"ok": False, "error": "No hay credenciales ni cookies vigentes guardadas."}
        except Exception as e:
            return {"ok": False, "error": f"Error al restaurar sesión: {str(e)}"}

    def get_user_profile(self) -> Dict[str, Any]:
        try:
            profile = get_current_user(self.session)
            return {"ok": True, "data": profile}
        except Exception as e:
            return {"ok": False, "error": f"No se pudo obtener el perfil: {str(e)}"}

    def logout(self) -> Dict[str, Any]:
        try:
            self.session.logged_in = False
            self.session.usuario = ""
            self.session.nombre = ""
            self.session.http.cookies.clear()
            borrar_cookies_sesion()
            limpiar_user_cache()
            return {"ok": True, "data": {"mensaje": "Sesión cerrada correctamente."}}
        except Exception as e:
            return {"ok": False, "error": f"Error al cerrar sesión: {str(e)}"}
