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

def get_current_user(sess: CampusSession = None, cache_dir: str = CONFIG_DIR, force_network: bool = False) -> dict:
    """
    Obtiene los datos del usuario actual (dni, nombre, foto_url).
    1. Si force_network=False (por defecto), primero intenta leer de user_cache.json para máxima velocidad (<1ms).
    2. Si force_network=True o no hay datos en caché y hay sesión activa conectada, consulta escritorio.cgi.
    3. Guarda los datos obtenidos en user_cache.json dentro de cache_dir.
    4. Devuelve un dict con: {"dni": str, "nombre": str, "foto_url": str}.
    """
    user_data = {
        "dni": "",
        "nombre": "",
        "foto_url": ""
    }
    cache_path = os.path.join(cache_dir, "user_cache.json") if cache_dir else USER_CACHE_FILE

    # 1. Si no se fuerza red, intentar leer de caché primero para respuesta instantánea
    if not force_network:
        cached = cargar_user_cache(cache_path)
        if cached and (cached.get("dni") or cached.get("nombre")):
            return cached
        if sess and getattr(sess, "logged_in", False) and getattr(sess, "nombre", ""):
            return {
                "dni": getattr(sess, "usuario", ""),
                "nombre": getattr(sess, "nombre", ""),
                "foto_url": ""
            }

    # 2. Si se requiere red o no había caché, y hay sesión activa
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

    # 3. Fallback a caché si falló la red
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


def get_perfil_personal(sess: CampusSession) -> dict:
    """
    Obtiene los datos del perfil del usuario desde personal.cgi.
    Retorna un diccionario con:
      - nombre, apellido, email, fecha_nacimiento, telefono, foto_url, raw_form
    """
    from bs4 import BeautifulSoup
    from config import BASE_URL

    url = BASE_URL + "personal.cgi"
    perfil = {
        "nombre": "",
        "apellido": "",
        "email": "",
        "fecha_nacimiento": "",
        "telefono": "",
        "foto_url": "",
        "raw_form": {}
    }
    try:
        r = sess.get(url, timeout=15)
        html = decode_html(r.content)
        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form")
        if not form:
            return perfil

        raw = {}
        for inp in form.find_all("input"):
            n = inp.get("name")
            i_type = (inp.get("type") or "text").lower()
            if not n:
                continue
            if i_type in ("checkbox", "radio"):
                if inp.has_attr("checked"):
                    raw[n] = inp.get("value", "1")
            elif i_type != "submit":
                if n not in raw:
                    raw[n] = inp.get("value", "")
        for sel in form.find_all("select"):
            n = sel.get("name")
            if n:
                opt = sel.find("option", selected=True)
                raw[n] = opt.get("value", "") if opt else ""
        for txt in form.find_all("textarea"):
            n = txt.get("name")
            if n:
                raw[n] = txt.get_text()

        perfil["raw_form"] = raw
        perfil["nombre"] = raw.get("nombre_usuario", "")
        perfil["apellido"] = raw.get("apellido_usuario", "")
        perfil["email"] = raw.get("email", "")
        perfil["fecha_nacimiento"] = raw.get("fecha_nacimiento", "")
        perfil["telefono"] = raw.get("campos_3", "")

        u_info = get_current_user(sess, force_network=False)
        perfil["foto_url"] = u_info.get("foto_url", "")
    except Exception as e:
        logging.warning(f"Error al obtener perfil personal: {e}")

    return perfil


def guardar_perfil_personal(sess: CampusSession, datos_nuevos: dict, nueva_foto_path: str = None, eliminar_foto: bool = False, clave_actual: str = "", nueva_clave: str = "") -> tuple[bool, str]:
    """
    Guarda los cambios del perfil en personal.cgi.
    datos_nuevos: dict con 'nombre', 'apellido', 'email', 'fecha_nacimiento', 'telefono'.
    nueva_foto_path: ruta de archivo de imagen local para subir.
    eliminar_foto: si True, envía fotografia=3 (quitar foto).
    clave_actual: contraseña actual (requerida si nueva_clave no está vacía).
    nueva_clave: nueva contraseña (mínimo 8 caracteres, al menos 1 mayúscula).
    """
    from bs4 import BeautifulSoup
    from config import BASE_URL, CONFIG_DIR
    import mimetypes
    import shutil

    if nueva_clave:
        if len(nueva_clave) < 8:
            return False, "La nueva clave debe contener al menos 8 caracteres."
        if not any(c.isupper() for c in nueva_clave):
            return False, "La nueva clave debe contener al menos 1 letra mayúscula."
        if not clave_actual:
            return False, "Debes ingresar tu clave actual para autorizar el cambio de contraseña."

    try:
        # Siempre obtener formulario fresco de personal.cgi para tener csrf_token y campos vigentes
        fresh = get_perfil_personal(sess)
        post_data = dict(fresh.get("raw_form", {}))
        # Botón submit requerido por el CGI de la plataforma
        post_data["wOk"] = "GUARDAR"

        if "nombre" in datos_nuevos and datos_nuevos["nombre"]:
            post_data["nombre_usuario"] = datos_nuevos["nombre"]
        if "apellido" in datos_nuevos and datos_nuevos["apellido"]:
            post_data["apellido_usuario"] = datos_nuevos["apellido"]
        if "email" in datos_nuevos and datos_nuevos["email"]:
            post_data["email"] = datos_nuevos["email"]
            post_data["campos_1"] = datos_nuevos["email"]
        if "fecha_nacimiento" in datos_nuevos and datos_nuevos["fecha_nacimiento"]:
            post_data["fecha_nacimiento"] = datos_nuevos["fecha_nacimiento"]
        if "telefono" in datos_nuevos:
            post_data["campos_3"] = datos_nuevos["telefono"]

        if nueva_clave:
            post_data["clave"] = nueva_clave
            post_data["clave2"] = nueva_clave
            post_data["clave_actual"] = clave_actual
        else:
            post_data["clave"] = ""
            post_data["clave2"] = ""
            post_data["clave_actual"] = ""

        # Manejo de fotografía
        # fotografia: "1" = mantener actual, "2" = subir nueva foto, "3" = quitar foto
        post_data.pop("fotografia-file", None)
        if eliminar_foto:
            post_data["fotografia"] = "3"
        elif nueva_foto_path and os.path.exists(nueva_foto_path):
            post_data["fotografia"] = "2"
        else:
            post_data["fotografia"] = "1"

        url = BASE_URL + "personal.cgi"

        if nueva_foto_path and os.path.exists(nueva_foto_path) and not eliminar_foto:
            mime_type, _ = mimetypes.guess_type(nueva_foto_path)
            mime_type = mime_type or "image/jpeg"
            filename = os.path.basename(nueva_foto_path)
            with open(nueva_foto_path, "rb") as f_img:
                files = {"fotografia-file": (filename, f_img.read(), mime_type)}
                r = sess.post(url, data=post_data, files=files, timeout=30)
        else:
            r = sess.post(url, data=post_data, timeout=25)

        html = decode_html(r.content)
        soup = BeautifulSoup(html, "html.parser")

        alertas = soup.find_all("div", class_=re.compile(r"alerta|error", re.I))
        for a in alertas:
            txt = a.get_text().strip()
            if "error" in txt.lower() or "incorrect" in txt.lower():
                return False, txt

        nombre_completo = f"{post_data.get('nombre_usuario', '')} {post_data.get('apellido_usuario', '')}".strip()
        if nombre_completo:
            sess.nombre = nombre_completo

        # Limpiar caché local de miniaturas de avatar si la foto cambió
        if nueva_foto_path or eliminar_foto:
            try:
                avatars_dir = os.path.join(CONFIG_DIR, "avatars")
                if os.path.exists(avatars_dir):
                    shutil.rmtree(avatars_dir, ignore_errors=True)
                    os.makedirs(avatars_dir, exist_ok=True)
            except Exception:
                pass

        # Actualizar user cache para reflejar cambios en foto consultando la red
        if nueva_foto_path or eliminar_foto:
            try:
                fresh_user = get_current_user(sess, force_network=True)
                if eliminar_foto:
                    fresh_user["foto_url"] = ""
                guardar_user_cache(fresh_user)
            except Exception:
                pass
        else:
            u_info = get_current_user(sess, force_network=False)
            u_info["nombre"] = nombre_completo
            guardar_user_cache(u_info)

        return True, "Datos de perfil guardados correctamente."
    except Exception as e:
        return False, f"Error al guardar perfil: {e}"

