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


def get_mensajes(sess: CampusSession, id_curso: str) -> list[dict]:
    """
    Devuelve lista de mensajes de la materia.
    Estructura: [{"id","asunto","remitente","fecha","leido","link"}]
    """
    url = BASE_URL + f"webmail.cgi?wAccion=VerCarpeta&wIdBandeja=Inbox&id_curso={id_curso}"
    try:
        r = sess.get(url, timeout=15)
        html = decode_html(r.content)
        return _parse_mensajes(html, id_curso)
    except Exception:
        return []


def _parse_mensajes(html: str, id_curso: str) -> list[dict]:
    mensajes = []
    soup = BeautifulSoup(html, 'html.parser')

    # Buscar enlaces a VerEmail
    for a in soup.find_all('a', href=re.compile(r'wAccion=VerEmail')):
        href = a.get('href', '')
        # Extraer wIdEmail
        m_id = re.search(r'wIdEmail=(\d+)', href)
        email_id = m_id.group(1) if m_id else ""
        
        # El enlace suele contener nombre del remitente, asunto y fecha
        texto_completo = a.get_text()
        lineas = [l.strip() for l in texto_completo.splitlines() if l.strip()]
        
        remitente = lineas[0] if len(lineas) > 0 else ""
        asunto = lineas[1] if len(lineas) > 1 else ""
        fecha = lineas[-1] if len(lineas) > 2 else ""

        # Limpiar caracteres como '•' o tabulaciones
        asunto = re.sub(r'^[•\-\s]+', '', asunto).strip()
        
        if not asunto and remitente:
            asunto = remitente
            remitente = "Docente"

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
                "id_curso":  id_curso
            })

    return mensajes[:50]


def get_detalle_mensaje(sess: CampusSession, link_o_id: str, id_curso: str = "") -> dict:
    """Descarga y limpia con precisión el contenido de un mensaje del webmail."""
    # Si viene un link a la bandeja (ej: webmail.cgi?wAccion=VerCarpeta...), obtener el primer mensaje
    if "VerCarpeta" in link_o_id:
        m_cid = re.search(r'id_curso=(\d+)', link_o_id)
        cid = m_cid.group(1) if m_cid else id_curso
        mensajes_list = get_mensajes(sess, cid)
        if mensajes_list:
            link_o_id = mensajes_list[0].get("link", "")
        else:
            return {
                "asunto": "Bandeja de Mensajes",
                "remitente": "",
                "para": "",
                "fecha": "",
                "cuerpo": "No hay mensajes en la bandeja de entrada.",
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

        return {
            "asunto": asunto or "Mensaje",
            "remitente": remitente,
            "para": para,
            "fecha": fecha,
            "cuerpo": cuerpo,
            "adjuntos": adjuntos
        }
    except Exception as e:
        return {
            "asunto": "Error",
            "remitente": "",
            "para": "",
            "fecha": "",
            "cuerpo": f"Error al cargar el mensaje: {e}",
            "adjuntos": []
        }

