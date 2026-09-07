"""
backend/mensajes.py — Obtiene mensajes del webmail de una materia y su contenido.
URL: webmail.cgi?id_curso=ID
"""
import re
import json
from bs4 import BeautifulSoup
from backend.session import CampusSession
from backend.scraper import decode_html, limpiar_html, get_scripts
from config import BASE_URL


def get_mensajes(sess: CampusSession, id_curso: str, bandeja: str = "Inbox") -> list[dict]:
    """
    Devuelve lista de mensajes de la materia según la bandeja especificada (Inbox, Outbox o Trash).
    Estructura: [{"id","asunto","remitente","fecha","leido","link","id_curso","bandeja"}]
    """
    url = BASE_URL + f"webmail.cgi?wAccion=VerCarpeta&wIdBandeja={bandeja}&id_curso={id_curso}"
    try:
        r = sess.get(url, timeout=15)
        html = decode_html(r.content)
        return _parse_mensajes(html, id_curso, bandeja=bandeja)
    except Exception:
        return []


def _parse_mensajes(html: str, id_curso: str, bandeja: str = "Inbox") -> list[dict]:
    mensajes = []
    soup = BeautifulSoup(html, 'html.parser')

    # Buscar enlaces a VerEmail
    for a in soup.find_all('a', href=re.compile(r'wAccion=VerEmail')):
        href = a.get('href', '')
        # Extraer wIdEmail
        m_id = re.search(r'wIdEmail=(\d+)', href)
        email_id = m_id.group(1) if m_id else ""
        
        # El enlace suele contener nombre del remitente/destinatario, asunto y fecha
        texto_completo = a.get_text()
        lineas = [l.strip() for l in texto_completo.splitlines() if l.strip()]
        
        remitente = lineas[0] if len(lineas) > 0 else ""
        asunto = lineas[1] if len(lineas) > 1 else ""
        fecha = lineas[-1] if len(lineas) > 2 else ""

        # Limpiar caracteres como '•' o tabulaciones
        asunto = re.sub(r'^[•\-\s]+', '', asunto).strip()
        
        if not asunto and remitente:
            asunto = remitente
            remitente = "Contacto"

        full_link = BASE_URL + href if not href.startswith("http") else href
        
        # Verificar si ya existe para evitar duplicados
        if not any(m.get("id") == email_id for m in mensajes if email_id):
            mensajes.append({
                "id":        email_id,
                "remitente": remitente,
                "asunto":    asunto,
                "fecha":     fecha,
                "leido":     True,
                "link":      full_link,
                "id_curso":  id_curso,
                "bandeja":   bandeja
            })

    return mensajes[:60]


def _coincide_fecha_novedad(fecha_nov: str, fecha_msg: str, exact_only: bool = False) -> bool:
    """Verifica si la fecha de una novedad (formato 'YYYY MM DD HH MM') coincide con la fecha del webmail ('DD/MM/YY - HH:MM hs.')."""
    if not fecha_nov or not fecha_msg:
        return False
    parts = fecha_nov.strip().split()
    if len(parts) >= 5:
        d, m, h, mn = parts[2], parts[1], parts[3], parts[4]
        patron_dia_mes = f"{d}/{m}"
        patron_hora = f"{h}:{mn}"
        if patron_dia_mes in fecha_msg and patron_hora in fecha_msg:
            return True
        if not exact_only and patron_dia_mes in fecha_msg:
            return True
    return False


def buscar_mensaje_por_novedad(sess: CampusSession, id_curso: str, fecha_novedad: str, asunto_novedad: str = "") -> dict | None:
    """
    Busca de manera exhaustiva y precisa el mensaje correspondiente a una novedad.
    Revisa en orden las bandejas: Inbox (Recibidos), Trash (Papelera) y Outbox (Enviados).
    Retorna el diccionario del mensaje o None si no hay coincidencia real.
    """
    if not id_curso:
        return None

    # Iterar por todas las bandejas posibles
    for bandeja in ("Inbox", "Trash", "Outbox"):
        try:
            mensajes_list = get_mensajes(sess, id_curso, bandeja=bandeja)
            if not mensajes_list:
                continue

            # 1. Coincidencia exacta con fecha y hora
            if fecha_novedad:
                for m in mensajes_list:
                    if _coincide_fecha_novedad(fecha_novedad, m.get("fecha", ""), exact_only=True):
                        m["bandeja"] = bandeja
                        return m

            # 2. Coincidencia por asunto si está presente
            if asunto_novedad and len(asunto_novedad.strip()) > 2:
                asunto_clean = asunto_novedad.strip().lower()
                for m in mensajes_list:
                    if asunto_clean in m.get("asunto", "").lower():
                        m["bandeja"] = bandeja
                        return m

            # 3. Coincidencia por día y mes
            if fecha_novedad:
                for m in mensajes_list:
                    if _coincide_fecha_novedad(fecha_novedad, m.get("fecha", ""), exact_only=False):
                        m["bandeja"] = bandeja
                        return m
        except Exception:
            continue

    return None


def get_detalle_mensaje(sess: CampusSession, link_o_id: str, id_curso: str = "", fecha_novedad: str = "", asunto_novedad: str = "") -> dict:
    """Descarga y limpia con precisión el contenido de un mensaje del webmail."""
    # Si viene un link a la bandeja (ej: webmail.cgi?wAccion=VerCarpeta...) o un asunto de texto, buscar el mensaje
    if "VerCarpeta" in link_o_id or (not link_o_id.startswith("http") and "wAccion" not in link_o_id and not link_o_id.isdigit()):
        if "VerCarpeta" not in link_o_id and not asunto_novedad:
            asunto_novedad = link_o_id

        m_cid = re.search(r'id_curso=(\d+)', link_o_id)
        cid = m_cid.group(1) if m_cid else id_curso

        # Buscar el mensaje real en las bandejas disponibles (Inbox, Trash, Outbox)
        msg_match = buscar_mensaje_por_novedad(sess, cid, fecha_novedad=fecha_novedad, asunto_novedad=asunto_novedad)
        if msg_match and msg_match.get("link"):
            link_o_id = msg_match["link"]
        else:
            return {
                "asunto": asunto_novedad or "Aviso de Mensajería",
                "remitente": "Mensajería del Campus",
                "para": "",
                "fecha": fecha_novedad or "",
                "cuerpo": (
                    "Este aviso de mensajería no coincide con los mensajes disponibles en las bandejas activas del aula.\n\n"
                    "El mensaje original pudo haber sido eliminado permanentemente o pertenecer a otra carpeta."
                ),
                "adjuntos": []
            }

    if link_o_id.startswith("http"):
        url = link_o_id
    elif "wAccion=VerEmail" in link_o_id:
        url = BASE_URL + link_o_id
    else:
        url = BASE_URL + f"webmail.cgi?wAccion=VerEmail&wIdEmail={link_o_id}&wIdBandeja=Inbox&id_curso={id_curso}"

    try:
        r = sess.get(url, timeout=15)
        html = decode_html(r.content)
        soup = BeautifulSoup(html, 'html.parser')

        # Asunto limpio (sin paginador)
        asunto = ""
        sub_span = soup.find('span', class_='subject') or soup.find(class_=re.compile(r'asunto|subject', re.I))
        if sub_span:
            asunto = sub_span.get_text().strip()

        # Remitente y Fecha
        remitente = ""
        fecha = ""
        rem_div = soup.find('div', class_='remitente')
        if rem_div:
            from_span = rem_div.find('span', class_='from')
            if from_span:
                remitente = from_span.get_text().strip()
            date_span = rem_div.find('span', class_='date')
            if date_span:
                fecha = date_span.get_text().strip()

        if not remitente:
            # Fallback
            from_el = soup.find(class_='from')
            if from_el:
                remitente = from_el.get_text().strip()

        # Destinatario (Para:)
        para = ""
        para_div = soup.find('div', class_='para')
        if para_div:
            names_span = para_div.find('span', class_='names')
            if names_span:
                para = names_span.get_text().strip()
            else:
                para = para_div.get_text().replace('Para:', '').strip()

        # Cuerpo del mensaje limpio (específico de Educativa)
        cuerpo = ""
        msg_div = soup.find('div', class_=re.compile(r'mensaje\b|tiny_personalizado', re.I))
        if msg_div:
            cuerpo = limpiar_html(str(msg_div)).strip()
        else:
            ver_mail = soup.find('div', class_='ver_mail')
            if ver_mail:
                # Quitar heading, subject_container, etc
                for tag in ver_mail.find_all(class_=re.compile(r'heading|subject_container|action_item|quota', re.I)):
                    tag.decompose()
                cuerpo = limpiar_html(str(ver_mail)).strip()

        # Limpiar cualquier texto de cabecera que se haya colado
        if cuerpo:
            cuerpo = re.sub(r'^(?:De:[^\n]+\n+|Para:[^\n]+\n+|Asunto:[^\n]+\n+|Fecha:[^\n]+\n+)+', '', cuerpo, flags=re.IGNORECASE).strip()

        if not cuerpo:
            cuerpo = "(Sin contenido en el mensaje)"

        # Adjuntos
        adjuntos = []
        for a in soup.find_all('a', href=re.compile(r'descargar|adjunto|wAccion=bajar', re.I)):
            adj_url = a.get('href', '')
            adj_nom = a.get_text().strip() or "Archivo adjunto"
            full_url = BASE_URL + adj_url if not adj_url.startswith('http') else adj_url
            if not any(it['url'] == full_url for it in adjuntos):
                adjuntos.append({
                    "nombre": adj_nom,
                    "url": full_url
                })

        # Destinatario ID (username/DNI para responder en mensajeria.cgi)
        destinatario_id = ""
        m_to = re.search(r"to\s*:\s*['\"]([^'\"]+)['\"]", html)
        if m_to:
            destinatario_id = m_to.group(1).strip()
        if not destinatario_id:
            m_user = re.search(r"verInfoUsuario\(['\"]([^'\"]+)['\"]", html)
            if m_user:
                destinatario_id = m_user.group(1).strip()

        # ID de email
        email_id = ""
        inp_email = soup.find('input', {'name': 'wIdEmail'})
        if inp_email and inp_email.get('value'):
            email_id = inp_email.get('value').strip()
        if not email_id:
            m_id = re.search(r'wIdEmail=(\d+)', url)
            if m_id:
                email_id = m_id.group(1)

        # Token CSRF
        csrf_token = ""
        inp_csrf = soup.find('input', {'name': 'csrf_token'})
        if inp_csrf and inp_csrf.get('value'):
            csrf_token = inp_csrf.get('value').strip()
        if not csrf_token:
            m_csrf = re.search(r"getCSRFToken\s*=\s*\(\)\s*=>\s*['\"]([^'\"]+)['\"]", html)
            if m_csrf:
                csrf_token = m_csrf.group(1)

        return {
            "id": email_id,
            "id_curso": id_curso,
            "destinatario_id": destinatario_id,
            "csrf_token": csrf_token,
            "asunto": asunto or "Mensaje",
            "remitente": remitente,
            "para": para,
            "fecha": fecha,
            "cuerpo": cuerpo,
            "adjuntos": adjuntos
        }
    except Exception as e:
        return {
            "id": "",
            "id_curso": id_curso,
            "destinatario_id": "",
            "csrf_token": "",
            "asunto": "Error",
            "remitente": "",
            "para": "",
            "fecha": "",
            "cuerpo": f"Error al cargar el mensaje: {e}",
            "adjuntos": []
        }


def responder_mensaje(sess: CampusSession, id_curso: str, id_email: str, destinatario_id: str, asunto: str, cuerpo: str) -> tuple[bool, str]:
    """Envía una respuesta a un mensaje del webmail a través de mensajeria.cgi."""
    try:
        url_get = (BASE_URL + f"mensajeria.cgi?wIdDestino={destinatario_id}&id_curso={id_curso}"
                   f"&wAsunto=Responder_MAIL&wIdEmail={id_email}&wIdEmailEnviadosResponder={id_email}")
        r_get = sess.get(url_get, timeout=15)
        html_get = decode_html(r_get.content)
        soup_get = BeautifulSoup(html_get, "html.parser")
        form = soup_get.find("form")
        if not form:
            return False, "No se encontró el formulario de mensajería en el campus."

        post_data = {}
        for inp in form.find_all("input"):
            name = inp.get("name")
            if name:
                post_data[name] = inp.get("value", "")

        textarea = form.find("textarea", {"name": "wMensaje"})
        cita_previa = textarea.get_text() if textarea else ""

        post_data["wDestinatarios"] = destinatario_id
        post_data["wAsunto"] = asunto
        post_data["wMensaje"] = f"<p>{cuerpo}</p>\n{cita_previa}"
        post_data["wAccion"] = "email"

        url_post = BASE_URL + "mensajeria.cgi"
        r_post = sess.post(url_post, data=post_data, timeout=20)
        html_post = decode_html(r_post.content)

        text_post = BeautifulSoup(html_post, "html.parser").get_text()
        if "enviado" in text_post.lower() or "éxito" in text_post.lower() or "exito" in text_post.lower():
            return True, "Mensaje respondido con éxito."
        else:
            return False, "El campus no confirmó el envío de la respuesta."
    except Exception as e:
        return False, f"Error al responder el mensaje: {e}"


def reenviar_mensaje(sess: CampusSession, id_curso: str, id_email: str, destinatario_id: str, asunto: str, nota_adicional: str = "") -> tuple[bool, str]:
    """Reenvía un mensaje del webmail a un destinatario a través de mensajeria.cgi."""
    try:
        url_get = (BASE_URL + f"mensajeria.cgi?id_curso={id_curso}"
                   f"&wAsunto=Reenviar_MAIL&wIdEmail={id_email}&wIdEmailEnviadosReenvio={id_email}")
        r_get = sess.get(url_get, timeout=15)
        html_get = decode_html(r_get.content)
        soup_get = BeautifulSoup(html_get, "html.parser")
        form = soup_get.find("form")
        if not form:
            return False, "No se encontró el formulario de reenvío en el campus."

        post_data = {}
        for inp in form.find_all("input"):
            name = inp.get("name")
            if name:
                post_data[name] = inp.get("value", "")

        textarea = form.find("textarea", {"name": "wMensaje"})
        cita_previa = textarea.get_text() if textarea else ""

        post_data["wDestinatarios"] = destinatario_id
        post_data["wAsunto"] = asunto
        cuerpo_envio = f"<p>{nota_adicional}</p>\n{cita_previa}" if nota_adicional else cita_previa
        post_data["wMensaje"] = cuerpo_envio
        post_data["wAccion"] = "email"

        url_post = BASE_URL + "mensajeria.cgi"
        r_post = sess.post(url_post, data=post_data, timeout=20)
        html_post = decode_html(r_post.content)

        text_post = BeautifulSoup(html_post, "html.parser").get_text()
        if "enviado" in text_post.lower() or "éxito" in text_post.lower() or "exito" in text_post.lower():
            return True, "Mensaje reenviado con éxito."
        else:
            return False, "El campus no confirmó el reenvío del mensaje."
    except Exception as e:
        return False, f"Error al reenviar el mensaje: {e}"


def eliminar_mensaje(sess: CampusSession, id_curso: str, id_email: str, csrf_token: str = "") -> tuple[bool, str]:
    """Elimina un mensaje del webmail moviéndolo a la papelera."""
    try:
        url = BASE_URL + "webmail.cgi"
        post_data = {
            "wAccion": "EliminarMensaje",
            "id_curso": id_curso,
            "wIdEmail": id_email,
            "wIdBandeja": "Inbox",
            "csrf_token": csrf_token
        }
        r = sess.post(url, data=post_data, timeout=15)
        if r.status_code == 200:
            return True, "Mensaje eliminado correctamente."
        return False, f"Respuesta inesperada del campus ({r.status_code})"
    except Exception as e:
        return False, f"Error al eliminar mensaje: {e}"


def _get_trash_csrf(sess: CampusSession, id_curso: str) -> str:
    """Extrae el token CSRF actual de la papelera."""
    try:
        url = BASE_URL + f"webmail.cgi?wAccion=VerCarpeta&wIdBandeja=Trash&id_curso={id_curso}"
        r = sess.get(url, timeout=12)
        html = decode_html(r.content)
        soup = BeautifulSoup(html, "html.parser")
        inp = soup.find("input", {"name": "csrf_token"})
        return inp.get("value", "") if inp else ""
    except Exception:
        return ""


def restaurar_mensajes_papelera(sess: CampusSession, id_curso: str, email_ids: list[str], csrf_token: str = "") -> tuple[bool, str]:
    """Restaura mensajes seleccionados de la papelera a la bandeja de entrada."""
    if not email_ids:
        return False, "No se seleccionó ningún mensaje para restaurar."
    try:
        token = csrf_token or _get_trash_csrf(sess, id_curso)
        url = BASE_URL + "webmail.cgi"
        post_data = {
            "wAccion": "RestaurarEmails",
            "id_curso": id_curso,
            "wIdBandeja": "Trash",
            "wCampoOrden": "fecha_email",
            "wSentidoOrden": "desc",
            "wPaginaActual": "1",
            "csrf_token": token,
            "wCantidadEmails": str(len(email_ids))
        }
        for i, mid in enumerate(email_ids, 1):
            post_data[f"wIdEmail{i}"] = str(mid)

        r = sess.post(url, data=post_data, timeout=20)
        if r.status_code == 200:
            return True, f"Se restauraron {len(email_ids)} mensaje(s) correctamente."
        return False, f"El campus devolvió código {r.status_code}"
    except Exception as e:
        return False, f"Error al restaurar mensajes: {e}"


def eliminar_permanente_papelera(sess: CampusSession, id_curso: str, email_ids: list[str], csrf_token: str = "") -> tuple[bool, str]:
    """Elimina permanentemente de la papelera los mensajes seleccionados."""
    if not email_ids:
        return False, "No se seleccionó ningún mensaje para eliminar."
    try:
        token = csrf_token or _get_trash_csrf(sess, id_curso)
        url = BASE_URL + "webmail.cgi"
        post_data = {
            "wAccion": "EliminarPermanentemente",
            "id_curso": id_curso,
            "wIdBandeja": "Trash",
            "wCampoOrden": "fecha_email",
            "wSentidoOrden": "desc",
            "wPaginaActual": "1",
            "csrf_token": token,
            "wCantidadEmails": str(len(email_ids))
        }
        for i, mid in enumerate(email_ids, 1):
            post_data[f"wIdEmail{i}"] = str(mid)

        r = sess.post(url, data=post_data, timeout=20)
        if r.status_code == 200:
            return True, f"Se eliminaron permanentemente {len(email_ids)} mensaje(s)."
        return False, f"El campus devolvió código {r.status_code}"
    except Exception as e:
        return False, f"Error al eliminar mensajes: {e}"


def vaciar_papelera(sess: CampusSession, id_curso: str, csrf_token: str = "") -> tuple[bool, str]:
    """Vacía por completo la papelera del webmail del curso."""
    try:
        token = csrf_token or _get_trash_csrf(sess, id_curso)
        url = BASE_URL + "webmail.cgi"
        post_data = {
            "wAccion": "Vaciar",
            "id_curso": id_curso,
            "wIdBandeja": "Trash",
            "csrf_token": token
        }
        r = sess.post(url, data=post_data, timeout=20)
        if r.status_code == 200:
            return True, "La papelera ha sido vaciada con éxito."
        return False, f"El campus devolvió código {r.status_code}"
    except Exception as e:
        return False, f"Error al vaciar la papelera: {e}"


def enviar_nuevo_mensaje(sess: CampusSession, id_curso: str, destinatarios: list[str] | str, asunto: str, cuerpo: str, archivo_adjunto: str | None = None) -> tuple[bool, str]:
    """
    Envía un nuevo mensaje del webmail a través de mensajeria.cgi.
    destinatarios: lista de IDs de contactos o string delimitado por comas ("38164348,46845785").
    archivo_adjunto: ruta local a un archivo adjunto (máx 30 MB).
    """
    import os
    import mimetypes

    if isinstance(destinatarios, list):
        dest_list = [str(d).strip() for d in destinatarios if str(d).strip()]
        dest_str = ",".join(dest_list)
    else:
        dest_str = str(destinatarios).strip()
        dest_list = [d.strip() for d in dest_str.split(",") if d.strip()]

    if not dest_str:
        return False, "Debes seleccionar al menos un destinatario."

    if archivo_adjunto:
        if not os.path.exists(archivo_adjunto):
            return False, f"El archivo adjunto no existe: {archivo_adjunto}"
        size_bytes = os.path.getsize(archivo_adjunto)
        if size_bytes > 30 * 1024 * 1024:
            return False, "El archivo seleccionado supera el límite máximo de 30 MB permitido por el campus."

    try:
        url_get = BASE_URL + f"mensajeria.cgi?id_curso={id_curso}&wAsunto=Redactar_MAIL"
        r_get = sess.get(url_get, timeout=15)
        html_get = decode_html(r_get.content)
        soup_get = BeautifulSoup(html_get, "html.parser")
        form = soup_get.find("form")
        if not form:
            return False, "No se encontró el formulario de mensajería en el campus."

        post_data = {}
        for inp in form.find_all("input"):
            name = inp.get("name")
            if name:
                post_data[name] = inp.get("value", "")

        post_data["wDestinatarios"] = dest_str
        post_data["wAsunto"] = asunto
        post_data["wMensaje"] = f"<p>{cuerpo}</p>"
        post_data["wAccion"] = "email"

        url_post = BASE_URL + "mensajeria.cgi"

        if archivo_adjunto:
            instancia = post_data.get("wInstancia", "")
            if not instancia:
                m_inst = re.search(r'id_instancia\s*:\s*["\']([^"\']+)["\']', html_get)
                if m_inst:
                    instancia = m_inst.group(1).strip()
                    post_data["wInstancia"] = instancia

            upload_url = BASE_URL + "HTML5Upload.cgi"
            mime_type, _ = mimetypes.guess_type(archivo_adjunto)
            mime_type = mime_type or "application/octet-stream"
            filename = os.path.basename(archivo_adjunto)

            with open(archivo_adjunto, "rb") as f_adj:
                files_up = {"Filedata": (filename, f_adj, mime_type)}
                data_up = {
                    "instancia": instancia,
                    "accion": "upload",
                    "html": "html",
                    "file_size_limit": "31457280"
                }
                r_up = sess.post(upload_url, data=data_up, files=files_up, timeout=90)

            post_data["wAdjunto_cant"] = "1"
            r_post = sess.post(url_post, data=post_data, timeout=30)
        else:
            post_data["wAdjunto_cant"] = "0"
            r_post = sess.post(url_post, data=post_data, timeout=20)

        html_post = decode_html(r_post.content)
        text_post = BeautifulSoup(html_post, "html.parser").get_text()

        if "enviado" in text_post.lower() or "éxito" in text_post.lower() or "exito" in text_post.lower():
            cant = len(dest_list)
            txt_dest = "al destinatario" if cant == 1 else f"a los {cant} destinatarios"
            msg_ok = f"El mensaje dirigido {txt_dest} ha sido enviado con éxito. Gracias por utilizar el servicio de mensajería interna del Instituto de Educación Superior N°5 'José E. Tello'."
            return True, msg_ok
        else:
            return False, "El campus no confirmó el envío del mensaje."
    except Exception as e:
        return False, f"Error al enviar el mensaje: {e}"




