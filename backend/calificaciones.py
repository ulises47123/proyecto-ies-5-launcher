"""
backend/calificaciones.py — Obtiene calificaciones completas de una materia.
URL: calificaciones.cgi?id_curso=ID y subcategorías wAccion=verexamenes
"""
import re
from bs4 import BeautifulSoup
from backend.session import CampusSession
from backend.scraper import decode_html, limpiar_html
from config import BASE_URL


def get_calificaciones(sess: CampusSession, id_curso: str) -> list[dict]:
    """
    Devuelve lista de calificaciones de la materia consultando la vista general y subcategorías.
    Estructura: [{"nombre","nota","categoria","docente","peso","fecha","observaciones"}]
    """
    url_base = BASE_URL + f"calificaciones.cgi?id_curso={id_curso}"
    try:
        r = sess.get(url_base, timeout=15)
        html = decode_html(r.content)
        soup = BeautifulSoup(html, 'html.parser')

        # Buscar enlaces a categorías de exámenes (wAccion=verexamenes)
        cats = []
        for a in soup.find_all('a', href=re.compile(r'wAccion=verexamenes', re.I)):
            href = a.get('href', '')
            txt = a.get_text().strip()
            # Limpiar nombre de categoría
            cat_nom = txt.splitlines()[-1].strip() if '\n' in txt else txt
            full_link = BASE_URL + href if not href.startswith('http') else href
            if not any(c['url'] == full_link for c in cats):
                cats.append({'url': full_link, 'nombre': cat_nom})

        calificaciones = []

        # Si hay categorías, recorrerlas para extraer los ítems reales de evaluación
        if cats:
            for c in cats:
                try:
                    r_cat = sess.get(c['url'], timeout=12)
                    html_cat = decode_html(r_cat.content)
                    items_cat = _parse_items_calificaciones(html_cat, c['nombre'])
                    calificaciones.extend(items_cat)
                except Exception:
                    pass

        # Si no hubo ítems en subcategorías, intentar parseo de la página principal
        if not calificaciones:
            calificaciones = _parse_items_calificaciones(html, "General")

        return calificaciones
    except Exception:
        return []


def _parse_items_calificaciones(html: str, categoria_default: str = "") -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    result = []

    # 1. Buscar tarjetas con clase .item
    for it in soup.find_all(class_='item'):
        t_el = it.find(['a', 'h3', 'h4', 'span'], class_=re.compile(r'titulo|nombre|head', re.I)) or it.find('a')
        if t_el:
            tit = t_el.get_text().strip().splitlines()[0].strip()
        else:
            lines = [l.strip() for l in it.get_text().splitlines() if l.strip()]
            tit = lines[0] if lines else "Evaluación"

        if not tit or tit.lower() in ('calificaciones', 'inicio', 'clases'):
            continue

        doc_el = it.find(class_=re.compile(r'user|usuario|docente|Contenido-Item-Usuario', re.I))
        docente = doc_el.get_text().strip() if doc_el else ''

        nota_el = it.find(class_=re.compile(r'nota|lista_nota|calific', re.I))
        nota = nota_el.get_text().replace('Nota:', '').strip() if nota_el else '—'
        if not nota:
            nota = '—'

        obs = ''
        for p in it.find_all(['div', 'p', 'span']):
            p_txt = p.get_text().strip()
            if 'observacion' in p_txt.lower():
                obs_val = p_txt.replace('Observaciones:', '').replace('Observación:', '').strip()
                if obs_val:
                    obs = obs_val
            elif 'detalles' in p_txt.lower():
                det_val = p_txt.replace('Detalles:', '').strip()
                if det_val and det_val not in obs:
                    obs = (obs + ' | ' + det_val).strip(' |')

        m_f = re.search(r'(\d{2}/\d{2}/\d{4})', it.get_text())
        fecha = m_f.group(1) if m_f else ''

        result.append({
            "nombre": tit,
            "categoria": categoria_default,
            "docente": docente,
            "nota": nota,
            "fecha": fecha,
            "peso": "",
            "observaciones": obs
        })

    # 2. Fallback si hay tablas <tr>
    if not result:
        for tr in soup.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) >= 2:
                vals = [limpiar_html(str(c)).strip() for c in tds]
                nom = vals[0]
                nota = vals[1] if len(vals) > 1 else '—'
                if nom and nom.lower() not in ('evaluación', 'nota', 'examen', 'nombre', ''):
                    result.append({
                        "nombre": nom,
                        "categoria": categoria_default,
                        "docente": "",
                        "nota": nota or '—',
                        "fecha": vals[-1] if len(vals) > 3 else '',
                        "peso": vals[2] if len(vals) > 2 else '',
                        "observaciones": ""
                    })

    return result
