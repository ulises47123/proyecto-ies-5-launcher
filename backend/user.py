"""
backend/user.py — Centraliza la extracción, normalización y caché de datos del usuario autenticado.
Totalmente dinámico: extrae DNI/usuario, nombre completo y foto desde la sesión o caché sin ningún valor estático.
"""
import os
import re
import json
import logging
from backend.session import CampusSession
from backend.scraper import decode_html, extract_var
from config import CONFIG_DIR, USER_CACHE_FILE

def get_current_user(sess: CampusSession = None, cache_dir: str = CONFIG_DIR) -> dict:
    """
    Obtiene los datos del usuario actual (dni, nombre, foto_url).
    1. Si hay sesión activa conectada, intenta extraer los datos desde escritorio.cgi o estadisticas.cgi.
    2. Guarda los datos obtenidos en user_cache.json dentro de cache_dir.
    3. Si la sesión no está disponible o falla la red, lee los datos de user_cache.json.
    4. Devuelve un dict con: {"dni": str, "nombre": str, "foto_url": str}.
    """
    user_data = {
        "dni": "",
        "nombre": "",
        "foto_url": ""
    }
    cache_path = os.path.join(cache_dir, "user_cache.json") if cache_dir else USER_CACHE_FILE

    # 1. Si hay sesión activa, scrapear datos en tiempo real
    if sess and getattr(sess, "logged_in", False):
        dni = getattr(sess, "usuario", "").strip()
        nombre = getattr(sess, "nombre", "").strip()
        foto_url = ""

        try:
            r = sess.get(sess.url("escritorio.cgi"), timeout=10)
            html = decode_html(r.content)

            # Extraer DNI / id_usuario si no lo teníamos
            if not dni:
                m_uid = re.search(r"var\s+id_usuario\s*=\s*['\"]([^'\"]+)['\"]", html)
                if not m_uid:
                    m_uid = re.search(r'username:\s*["\']([^"\']+)["\']', html)
                if m_uid:
                    dni = m_uid.group(1).strip()

            # Extraer nombre completo
            if not nombre or nombre == dni:
                # Método a: window.navigationInstance o similar
                m_nom_inst = re.search(r'user_nombre_completo:\s*["\']([^"\']+)["\']', html)
                if m_nom_inst:
                    nombre = m_nom_inst.group(1).strip()

            if not nombre or nombre == dni:
                # Método b: variable nombre_completo
                nom_var = extract_var(html, "nombre_completo")
                if nom_var:
                    nombre = nom_var.strip()

            if not nombre or nombre == dni:
                # Método c: topbar-user-name en HTML
                m_topbar = re.search(r'class=["\'][^"\']*topbar-user-name[^"\']*["\'][^>]*>(.*?)</span>', html, re.DOTALL | re.IGNORECASE)
                if m_topbar:
                    nombre = re.sub(r'<[^>]+>', '', m_topbar.group(1)).strip()

            # Extraer foto de perfil
            m_foto = re.search(r'url_thumb:\s*["\']([^"\']+)["\']', html)
            if not m_foto:
                m_foto = re.search(r'class=["\'][^"\']*topbar-user-avatar[^"\']*["\'][^>]*src=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if m_foto:
                foto_url = m_foto.group(1).strip()

            # Fallback secundario a estadisticas.cgi si aún falta el nombre
            if not nombre or nombre == dni:
                try:
                    r_est = sess.get(sess.url("estadisticas.cgi"), timeout=5)
                    h_est = decode_html(r_est.content)
                    m_est_nom = re.search(r'<h[12][^>]*>\s*([^,<\n\r]+),\s*as[íi]\s*vamos', h_est, re.IGNORECASE)
                    if m_est_nom:
                        nombre = m_est_nom.group(1).strip()
                except Exception:
                    pass

        except Exception as e:
            logging.warning(f"Error al extraer datos de usuario dinámicos: {e}")

        if dni:
            user_data["dni"] = dni
        if nombre:
            user_data["nombre"] = nombre
            sess.nombre = nombre
        if foto_url:
            user_data["foto_url"] = foto_url

        # Guardar en user_cache.json si obtuvimos al menos dni o nombre
        if user_data["dni"] or user_data["nombre"]:
            guardar_user_cache(user_data, cache_path)
            return user_data

    # 2. Si no hay sesión o falló la extracción, consultar user_cache.json
    cached = cargar_user_cache(cache_path)
    if cached:
        return cached

    return user_data


def guardar_user_cache(data: dict, file_path: str = USER_CACHE_FILE):
    """Guarda los datos del usuario en la caché JSON."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning(f"No se pudo guardar user_cache.json: {e}")


def cargar_user_cache(file_path: str = USER_CACHE_FILE) -> dict:
    """Carga los datos del usuario desde la caché JSON."""
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def limpiar_user_cache(file_path: str = USER_CACHE_FILE):
    """Elimina la caché de usuario si se solicita un logout completo."""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
