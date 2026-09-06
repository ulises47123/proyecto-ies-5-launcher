"""
backend/programa.py — Obtiene el programa (unidades e ítems) de una materia y su contenido.
Soporta tanto programas.cgi como actividades.cgi (clases).
"""
import re
from datetime import datetime
from bs4 import BeautifulSoup
from backend.session import CampusSession
from backend.scraper import decode_html, limpiar_html
from config import BASE_URL

TIPO_ICONS = {
    "archivo":   "📎",
    "texto":     "📄",
    "actividad": "✏️",
    "link":      "🔗",
    "otro":      "•",
}


def get_programa(sess: CampusSession, id_curso: str) -> list[dict]:
    """
    Devuelve lista de unidades, cada una con su lista de ítems.
    Estructura: [{"id","nombre","items":[{"titulo","tipo","tipo_desc","url","id_item"}]}]
    """
    # Intentar primero con actividades.cgi (que contiene las clases y actividades completas)
    unidades = _obtener_de_url(sess, f"{BASE_URL}actividades.cgi?id_curso={id_curso}", id_curso)
    if not unidades or sum(len(u.get("items", [])) for u in unidades) <= 2:
        # Fallback a programas.cgi
        unidades_prog = _obtener_de_url(sess, f"{BASE_URL}programas.cgi?id_curso={id_curso}", id_curso)
        if unidades_prog and sum(len(u.get("items", [])) for u in unidades_prog) > sum(len(u.get("items", [])) for u in unidades):
            unidades = unidades_prog
    return unidades


def _obtener_de_url(sess: CampusSession, url: str, id_curso: str) -> list[dict]:
    try:
        r = sess.get(url, timeout=15)
        html = decode_html(r.content)
        return _parse_programa(html, id_curso)
    except Exception:
        return []


def _parse_programa(html: str, id_curso: str) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    unidades = []

    # 1. Buscar bloques estructurados por id="unidad_XXXX"
    for ub in soup.find_all(id=re.compile(r'^unidad_\d+')):
        u_id = ub.get('id', '').replace('unidad_', '')
        nom_el = ub.find(class_=re.compile(r'unidad_nombre|nombre_unidad')) or ub.find(['h2', 'h3', 'h4'])
        u_nom = nom_el.get_text().strip() if nom_el else f"Unidad {u_id}"

        items = []
        seen = set()

        for a in ub.find_all('a'):
            href = a.get('href', '')
            titulo = a.get_text().strip()
            if not href or not titulo or href in seen or 'javascript:' in href:
                continue
            if href.startswith('#') or 'wAccion=verunidades' in href:
                continue

            # Identificar tipo
            tipo = 'otro'
            tipo_desc = ''
            if 'calificaciones.cgi' in href:
                tipo = 'relacionado_calif'
                tipo_desc = 'Calificaciones de la unidad'
            elif 'archivos.cgi' in href:
                tipo = 'relacionado_archivos'
                tipo_desc = 'Archivos de la unidad'
            elif 'actividades.cgi' in href or 'actividad' in href.lower():
                tipo = 'actividad'
                tipo_desc = 'Actividad'
            elif 'prg_archivo.cgi' in href or 'archivo' in href.lower() or 'descargar' in href.lower():
                tipo = 'archivo'
                tipo_desc = 'Archivo'
            elif 'prg_texto.cgi' in href or 'texto' in href.lower():
                tipo = 'texto'
                tipo_desc = 'Contenido'
            elif 'prg_link.cgi' in href or 'link' in href.lower():
                tipo = 'link'
                tipo_desc = 'Enlace'

            # Detectar estado de la actividad (Entregada / Pendiente / Cerrada)
            estado = "Pendiente" if tipo == "actividad" else ""
            estado_color = "orange" if tipo == "actividad" else ""
            fecha_apertura = ""

            padre = a.find_parent(class_=re.compile(r'item'))
            if padre:
                t_span = padre.find(class_='item_tipo')
                if t_span and tipo not in ('relacionado_calif', 'relacionado_archivos'):
                    tipo_desc = t_span.get_text().strip()

                ap_div = padre.find(class_=re.compile(r'apertura|fecha', re.I))
                if ap_div:
                    fecha_apertura = ap_div.get_text().strip()

                # Buscar icono o indicador de estado
                icon_tag = padre.find(class_=re.compile(r'icono|icon_retomar|fa-check|fa-play', re.I))
                icon_title = icon_tag.get('title', '') if icon_tag else ''

                if any(k in icon_title.lower() for k in ['entregado', 'entregada', 'completado', 'completada']) or 'fa-check' in str(padre):
                    estado = "Entregada"
                    estado_color = "green"
                elif tipo == 'actividad':
                    # Determinar si está abierta o cerrada por fecha
                    m_hasta = re.search(r'hasta\s*(\d{2}/\d{2}/\d{4}(?:\s*\d{2}:\d{2})?)', fecha_apertura, re.I)
                    if m_hasta:
                        try:
                            f_str = m_hasta.group(1).strip()
                            fmt = "%d/%m/%Y %H:%M" if " " in f_str else "%d/%m/%Y"
                            dt_lim = datetime.strptime(f_str, fmt)
                            if dt_lim < datetime.now():
                                estado = "Cerrada sin entregar"
                                estado_color = "red"
                            else:
                                estado = "Pendiente"
                                estado_color = "orange"
                        except Exception:
                            estado = "Pendiente"
                            estado_color = "orange"
                    else:
                        estado = "Pendiente"
                        estado_color = "orange"

            seen.add(href)
            full_url = BASE_URL + href if not href.startswith("http") else href
            
            # Limpiar saltos de línea en título
            titulo_limpio = " ".join(titulo.split())

            icon_map = {
                "archivo": "📎",
                "texto": "📄",
                "actividad": "✏️",
                "link": "🔗",
                "relacionado_calif": "🎓",
                "relacionado_archivos": "📂",
                "otro": "•"
            }

            items.append({
                "titulo":         titulo_limpio,
                "tipo":           tipo,
                "tipo_desc":      tipo_desc,
                "url":            full_url,
                "icon":           icon_map.get(tipo, "•"),
                "estado":         estado,
                "estado_color":   estado_color,
                "fecha_apertura": fecha_apertura
            })

        if items or u_nom:
            unidades.append({
                "id":     u_id,
                "nombre": u_nom,
                "items":  items
            })

    # 2. Fallback por regex si BeautifulSoup no encontró bloques
    if not unidades:
        unidades_dict: dict[str, dict] = {}
        for uid, nombre_html in re.findall(
            r'id=["\']nombre_unidad_(\d+)["\'][^>]*>(.*?)</(?:span|div|h\d)>',
            html, re.DOTALL | re.IGNORECASE
        ):
            nombre = limpiar_html(nombre_html).strip()
            if nombre:
                unidades_dict[uid] = {"id": uid, "nombre": nombre, "items": []}

        item_re = re.compile(
            r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE
        )
        for href, tit_html in item_re.findall(html):
            if not any(k in href for k in ['actividades.cgi', 'prg_archivo.cgi', 'prg_texto.cgi', 'prg_link.cgi']):
                continue
            uid_m = re.search(r'id_unidad=(\d+)', href)
            uid = uid_m.group(1) if uid_m else None
            titulo = limpiar_html(tit_html).strip()
            if not titulo:
                continue

            tipo = 'otro'
            if 'actividades.cgi' in href: tipo = 'actividad'
            elif 'prg_archivo.cgi' in href: tipo = 'archivo'
            elif 'prg_texto.cgi' in href: tipo = 'texto'
            elif 'prg_link.cgi' in href: tipo = 'link'

            item = {
                "titulo":    titulo,
                "tipo":      tipo,
                "tipo_desc": tipo.capitalize(),
                "url":       BASE_URL + href.replace("&amp;", "&") if not href.startswith("http") else href,
                "icon":      TIPO_ICONS.get(tipo, "•"),
            }
            if uid and uid in unidades_dict:
                unidades_dict[uid]["items"].append(item)
            elif unidades_dict:
                list(unidades_dict.values())[0]["items"].append(item)

        unidades = list(unidades_dict.values())

    return unidades


def get_detalle_actividad(sess: CampusSession, url: str) -> dict:
    """Extrae consigna, fechas, estado, entrega/realización y adjuntos de una actividad."""
    try:
        r = sess.get(url, timeout=15)
        html = decode_html(r.content)
        soup = BeautifulSoup(html, 'html.parser')

        # 1. Título principal (específico del ítem/actividad)
        titulo = ""
        # Buscar títulos específicos de la actividad evitando títulos institucionales globales
        tit_element = (
            soup.find(class_=re.compile(r'titulo_item|actividad_titulo|item_titulo|nombre_actividad', re.I)) or
            soup.find('h2', class_=re.compile(r'titulo|nombre', re.I)) or
            soup.find('div', class_=re.compile(r'titulo', re.I))
        )
        if tit_element:
            t_cand = tit_element.get_text().strip()
            if not any(k in t_cand.lower() for k in ['instituto', 'campus virtual', 'bienvenido']):
                titulo = t_cand

        if not titulo:
            for h in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                t_txt = h.get_text().strip()
                if t_txt and not any(k in t_txt.lower() for k in ['actividades integradoras', 'clases', 'instituto', 'campus virtual', 'educativa']):
                    titulo = t_txt
                    break

        if not titulo:
            h_alt = soup.find(class_=re.compile(r'titulo|nombre', re.I))
            titulo = h_alt.get_text().strip() if h_alt else "Actividad"

        # 2. Fechas de apertura y cierre
        fechas = []
        for fe in soup.find_all(class_=re.compile(r'fecha', re.I)):
            f_txt = fe.get_text().strip()
            if f_txt and f_txt not in fechas:
                fechas.append(f_txt)
        fecha_texto = " | ".join(fechas) if fechas else "Sin fecha límite especificada"

        # 3. Estado de la actividad (Entregada / Aprobada / Pendiente / Cerrada)
        estado = "Pendiente"
        estado_color = "orange"
        estados_found = [e.get_text().strip() for e in soup.find_all(class_=re.compile(r'estado', re.I))]
        if estados_found:
            estado_raw = " - ".join(estados_found)
            if any(k in estado_raw.lower() for k in ['entregada', 'aprobada', 'aprobado', 'muy bueno', 'bueno', 'regular', 'excelente']):
                estado = f"Entregada ({estado_raw})"
                estado_color = "green"
            elif any(k in estado_raw.lower() for k in ['cerrada', 'no entregada', 'vencida']):
                estado = f"Cerrada ({estado_raw})"
                estado_color = "red"
            else:
                estado = estado_raw

        # 4. Enunciado / Consigna (evitar contenedores globales que traigan encabezados del instituto)
        conthtml = (
            soup.find('div', class_=re.compile(r'conthtml|texto_actividad|consigna|enunciado|contenido_620', re.I)) or
            soup.find(id='conthtml') or
            soup.find('div', class_=re.compile(r'contenido', re.I))
        )
        cuerpo = limpiar_html(str(conthtml)) if conthtml else "(No se pudo extraer el contenido de la actividad)"

        # 5. Enlaces / Hipervínculos dentro del enunciado
        links_externos = []
        if conthtml:
            for a in conthtml.find_all('a'):
                h_url = a.get('href', '')
                h_txt = a.get_text().strip() or h_url
                if h_url and not h_url.startswith('#') and 'javascript:' not in h_url:
                    full_link = BASE_URL + h_url if not h_url.startswith('http') else h_url
                    links_externos.append({"texto": h_txt, "url": full_link})

        # 6. Sección de Realización / Entrega (si el alumno ya entregó)
        entrega_data = None
        sec_entrega = soup.find(class_=re.compile(r'entrega', re.I))
        if sec_entrega:
            e_txt = limpiar_html(str(sec_entrega))
            e_adjuntos = []
            for a in sec_entrega.find_all('a'):
                a_h = a.get('href', '')
                a_nom = a.get_text().strip() or "Archivo de entrega"
                if a_h and not a_h.startswith('#') and 'javascript:' not in a_h:
                    full_a = BASE_URL + a_h if not a_h.startswith('http') else a_h
                    e_adjuntos.append({"nombre": a_nom, "url": full_a})
            
            entrega_data = {
                "texto": e_txt,
                "adjuntos": e_adjuntos
            }
            # Confirmar estado verde si hay sección de entrega
            estado = "Entregada"
            estado_color = "green"

        # 7. Formulario de Entrega / Realización (si la actividad está pendiente y permite entregar)
        permite_entrega = False
        form_entrega = None
        form_tag = soup.find('form', action=re.compile(r'actividades\.cgi|realizacion\.cgi', re.I))
        if form_tag or soup.find(class_=re.compile(r'realizar|adjuntar|entregar', re.I)):
            permite_entrega = True
            form_action = form_tag.get('action', 'actividades.cgi') if form_tag else 'actividades.cgi'
            form_entrega = {
                "action": BASE_URL + form_action if not form_action.startswith('http') else form_action,
                "url_origen": url
            }

        # 8. Imágenes incrustadas en el texto/consigna
        imagenes = []
        if conthtml:
            for img in conthtml.find_all('img'):
                src = img.get('src', '')
                if src and not src.startswith('data:'):
                    full_src = BASE_URL + src if not src.startswith('http') else src
                    imagenes.append(full_src)

        # 9. Archivos adjuntos de la consigna
        adjuntos = []
        for sec in soup.find_all(class_=re.compile(r'archivos_adjuntos|adjunto', re.I)):
            for a in sec.find_all('a', href=re.compile(r'descargar|archivo|prg_archivo|location\.cgi', re.I)):
                href = a.get('href', '')
                nom_adj = a.get_text().strip() or "Descargar archivo adjunto"
                full_href = BASE_URL + href if not href.startswith("http") else href
                adjuntos.append({
                    "nombre": nom_adj,
                    "url": full_href
                })
                # Si el adjunto es una imagen
                if any(nom_adj.lower().endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                    imagenes.append(full_href)

        return {
            "titulo": titulo,
            "fechas": fecha_texto,
            "estado": estado,
            "estado_color": estado_color,
            "cuerpo": cuerpo,
            "links": links_externos,
            "adjuntos": adjuntos,
            "imagenes": imagenes,
            "entrega": entrega_data,
            "permite_entrega": permite_entrega and estado_color == "orange",
            "form_entrega": form_entrega,
            "url": url,
            "raw_html": html
        }
    except Exception as e:
        return {
            "titulo": "Error",
            "fechas": "",
            "estado": "Desconocido",
            "estado_color": "orange",
            "cuerpo": f"Error al cargar la actividad: {e}",
            "links": [],
            "adjuntos": [],
            "entrega": None,
            "permite_entrega": False
        }


def realizar_entrega_actividad(sess: CampusSession, url_actividad: str, comentario: str, ruta_archivo: str = "") -> tuple[bool, str]:
    """
    Envía la entrega de una actividad con comentario opcional y archivo adjunto.
    """
    try:
        # Extraer parámetros de la URL
        import urllib.parse
        parsed = urllib.parse.urlparse(url_actividad)
        params = urllib.parse.parse_qs(parsed.query)
        id_curso = params.get("id_curso", [""])[0]
        id_actividad = params.get("id_actividad", [""])[0] or params.get("id_item", [""])[0]

        post_url = f"{BASE_URL}actividades.cgi"
        data = {
            "id_curso": id_curso,
            "id_actividad": id_actividad,
            "wAccion": "guardar_entrega",
            "texto": comentario.strip(),
            "comentario": comentario.strip()
        }

        files = None
        if ruta_archivo and os.path.exists(ruta_archivo):
            f_name = os.path.basename(ruta_archivo)
            files = {
                'archivo': (f_name, open(ruta_archivo, 'rb'))
            }

        r = sess.post(post_url, data=data, files=files, timeout=30)
        if r.status_code in (200, 302):
            return True, "¡Actividad entregada correctamente!"
        return False, f"El servidor respondió con código {r.status_code}"
    except Exception as e:
        return False, f"No se pudo realizar la entrega: {e}"


def get_contenido_texto(sess: CampusSession, url: str) -> dict:
    """Descarga y extrae el texto de un ítem de tipo 'texto', enlaces y adjuntos."""
    try:
        r    = sess.get(url, timeout=15)
        html = decode_html(r.content)
        soup = BeautifulSoup(html, 'html.parser')

        conthtml = soup.find(id='conthtml') or soup.find(class_=re.compile(r'texto|contenido|mensaje', re.I))
        txt = ""
        links_ext = []
        if conthtml:
            txt = limpiar_html(str(conthtml))
            for a in conthtml.find_all('a'):
                h_url = a.get('href', '')
                if h_url and not h_url.startswith('#'):
                    full_link = BASE_URL + h_url if not h_url.startswith('http') else h_url
                    links_ext.append({"texto": a.get_text().strip() or full_link, "url": full_link})

        if not txt or len(txt) < 10:
            txt = limpiar_html(html)

        return {
            "texto": txt or "(Sin contenido disponible)",
            "links": links_ext
        }
    except Exception as e:
        return {
            "texto": f"(Error al cargar: {e})",
            "links": []
        }


