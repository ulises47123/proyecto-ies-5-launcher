"""
backend/cache_utils.py — Utilidades genéricas para persistencia, carga y actualización
segura de cachés en formato JSON con codificación UTF-8.
"""
import os
import json
import logging

logger = logging.getLogger(__name__)


def guardar_cache_json(filepath: str, data: dict | list) -> bool:
    """Guarda un diccionario o lista en formato JSON de forma segura."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"Error al guardar cache en {filepath}: {e}")
        return False


def cargar_cache_json(filepath: str, default_factory=None) -> dict | list:
    """Carga un archivo JSON de caché. Si no existe o falla, devuelve el valor por defecto."""
    if default_factory is None:
        default_val = {}
    elif callable(default_factory):
        default_val = default_factory()
    else:
        default_val = default_factory

    if not os.path.exists(filepath):
        return default_val
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error al leer cache de {filepath}: {e}")
        return default_val


# ── CHAT DEL AULA VIRTUAL (FIREBASE FIRESTORE REST INTEGRADO) ──
def get_mensajes_chat(sess, id_curso: str) -> dict:
    """
    Obtiene los mensajes reales del chat del aula virtual desde Firebase Firestore REST.
    Retorna un dict con:
      - 'disponible': bool (True si la materia tiene sección de chat habilitada)
      - 'mensajes': list de dicts con {id, remitente, fecha, texto, es_propio, profile_pic}
    """
    import re
    import json
    import requests
    from datetime import datetime
    from config import BASE_URL

    url = f"{BASE_URL}chat.cgi?id_curso={id_curso}"
    try:
        r = sess.get(url, timeout=12)
        if r.status_code != 200 or "EducativaChat" not in r.text:
            return {"disponible": False, "mensajes": [], "msg": "Chat no disponible para esta materia"}

        html = r.text
        token_m = re.findall(r'token:\s*\'([^\']+)\'', html)
        campus_m = re.findall(r'campusCollection:\s*\'([^\']+)\'', html)
        room_m = re.findall(r'roomId:\s*\'([^\']+)\'', html)
        cfg_m = re.findall(r'firebaseConfig:\s*\'(\{.*?\})\'', html)

        if not (token_m and campus_m and room_m and cfg_m):
            return {"disponible": False, "mensajes": [], "msg": "Chat no disponible para esta materia"}

        token = token_m[0]
        campus_col = campus_m[0]
        room_id = room_m[0]
        cfg = json.loads(cfg_m[0])
        api_key = cfg.get("apiKey", "")

        # Autenticación segura con Firebase Custom Token
        auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}"
        r_auth = requests.post(auth_url, json={"token": token, "returnSecureToken": True}, timeout=10)
        id_token = r_auth.json().get("idToken")
        if not id_token:
            return {"disponible": False, "mensajes": [], "msg": "No se pudo autenticar en el chat"}

        # Consulta a colección Firestore
        fs_url = f"https://firestore.googleapis.com/v1/projects/chat-educativa/databases/(default)/documents/{campus_col}/{room_id}/messages"
        headers = {"Authorization": f"Bearer {id_token}"}
        r_msgs = requests.get(fs_url, headers=headers, timeout=10)
        if r_msgs.status_code != 200:
            return {"disponible": True, "mensajes": []}

        docs = r_msgs.json().get("documents", [])
        mensajes = []
        user_id_actual = str(getattr(sess, "usuario", "usuario_anonimo"))

        for d in docs:
            fields = d.get("fields", {})
            remitente = fields.get("name", {}).get("stringValue") or fields.get("userId", {}).get("stringValue") or "Usuario"
            texto = fields.get("text", {}).get("stringValue") or ""
            uid_msg = fields.get("userId", {}).get("stringValue") or ""
            raw_ts = fields.get("timestamp", {}).get("timestampValue") or d.get("createTime") or ""
            
            # Formatear fecha legible
            fecha_str = ""
            dt_sort = 0
            if raw_ts:
                try:
                    dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                    dt_sort = dt.timestamp()
                    # Convertir a hora local aproximada / formato legible
                    fecha_str = dt.strftime("%d/%m %H:%M")
                except Exception:
                    fecha_str = raw_ts[:16]

            if texto:
                mensajes.append({
                    "id": d.get("name", ""),
                    "remitente": remitente,
                    "autor": remitente,
                    "fecha": fecha_str,
                    "texto": texto,
                    "es_propio": (uid_msg == user_id_actual or user_id_actual in uid_msg),
                    "_ts": dt_sort
                })

        # Ordenar cronológicamente (antiguos primero, recientes abajo)
        mensajes.sort(key=lambda m: m.get("_ts", 0))

        return {"disponible": True, "mensajes": mensajes}
    except Exception as e:
        logger.warning(f"Error al obtener chat de materia {id_curso}: {e}")
        return {"disponible": False, "mensajes": [], "msg": f"Error: {e}"}


# Alias de compatibilidad
obtener_mensajes_chat = get_mensajes_chat


def enviar_mensaje_chat(sess, id_curso: str, mensaje: str) -> tuple[bool, str]:
    """
    Envía un mensaje al chat general de la materia conectando a Firebase Firestore REST.
    """
    import re
    import json
    import requests
    import datetime
    from config import BASE_URL

    if not mensaje or not mensaje.strip():
        return False, "El mensaje no puede estar vacío."

    url = f"{BASE_URL}chat.cgi?id_curso={id_curso}"
    try:
        r = sess.get(url, timeout=12)
        if r.status_code != 200 or "EducativaChat" not in r.text:
            return False, "El chat no está habilitado para esta materia."

        html = r.text
        token_m = re.findall(r'token:\s*\'([^\']+)\'', html)
        campus_m = re.findall(r'campusCollection:\s*\'([^\']+)\'', html)
        room_m = re.findall(r'roomId:\s*\'([^\']+)\'', html)
        cfg_m = re.findall(r'firebaseConfig:\s*\'(\{.*?\})\'', html)
        nom_m = re.findall(r'displayName:\s*\"([^\"]+)\"', html)

        if not (token_m and campus_m and room_m and cfg_m):
            return False, "No se encontraron los datos de conexión del chat."

        token = token_m[0]
        campus_col = campus_m[0]
        room_id = room_m[0]
        cfg = json.loads(cfg_m[0])
        api_key = cfg.get("apiKey", "")
        display_name = nom_m[0] if nom_m else (getattr(sess, "nombre", "") or getattr(sess, "usuario", "Estudiante"))
        user_id = str(getattr(sess, "usuario", "usuario_anonimo"))

        # Auth
        auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}"
        r_auth = requests.post(auth_url, json={"token": token, "returnSecureToken": True}, timeout=10)
        id_token = r_auth.json().get("idToken")
        if not id_token:
            return False, "No se pudo autenticar en Firebase para enviar el mensaje."

        # POST mensaje a Firestore
        fs_post = f"https://firestore.googleapis.com/v1/projects/chat-educativa/databases/(default)/documents/{campus_col}/{room_id}/messages"
        headers = {"Authorization": f"Bearer {id_token}"}
        payload = {
            "fields": {
                "UID": {"stringValue": f"{campus_col}_{user_id}"},
                "userId": {"stringValue": user_id},
                "name": {"stringValue": display_name},
                "text": {"stringValue": mensaje.strip()},
                "timestamp": {"timestampValue": datetime.datetime.now(datetime.timezone.utc).isoformat()}
            }
        }
        r_send = requests.post(fs_post, headers=headers, json=payload, timeout=12)
        if r_send.status_code in (200, 201):
            return True, "Mensaje enviado con éxito."
        return False, f"Error de Firebase (código {r_send.status_code})."
    except Exception as e:
        return False, f"Error al enviar mensaje: {e}"
