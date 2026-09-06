"""
backend/escritorio.py — Obtiene cursos y novedades del escritorio del campus.
"""
import re
import json
from datetime import datetime
from backend.session import CampusSession
from backend.scraper import decode_html, get_scripts, extract_var
from config import DESK_URL


def get_escritorio(sess: CampusSession, page_size: int = 120) -> tuple[list, list, str]:
    """
    Descarga escritorio.cgi con el page_size seleccionado (por defecto 120)
    y devuelve (cursos, novedades, nombre_usuario).
    """
    url_req = f"{DESK_URL}?page_size={page_size}&wModulo=AccesoGrupos&wAccion=cambiar_page_size"
    r    = sess.get(url_req)
    html = decode_html(r.content)

    # Si no trajo el script completo con la url con params, intentar get simple
    if 'AccesoGrupos' not in html:
        r = sess.get(DESK_URL)
        html = decode_html(r.content)

    # Extraer nombre dinámicamente
    from backend.user import get_current_user
    user_info = get_current_user(sess)
    nombre = user_info.get("nombre") or sess.usuario

    scripts = get_scripts(html)

    cursos    = _parse_cursos(scripts)
    novedades = _parse_novedades(scripts)

    # Actualizar nombre en la sesión
    if nombre:
        sess.nombre = nombre

    return cursos, novedades, nombre


def _parse_cursos(scripts: list[str]) -> list[dict]:
    """Extrae la lista de cursos del script grande del escritorio."""
    for sc in scripts:
        if '"nombre"' not in sc or '"id"' not in sc or len(sc) < 5000:
            continue
        m = re.search(r'(\[\{"cant_items_obl.*?\}\])', sc, re.DOTALL)
        if not m:
            m = re.search(r'(\[\{.*?"nombre".*?\}\])', sc, re.DOTALL)
        if not m:
            continue
        try:
            data = json.loads(m.group(1))
            seen, result = set(), []
            for c in data:
                cid = str(c.get("id", ""))
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                nom = c.get("nombre", "Sin nombre")
                # Extraer año académico dinámicamente si figura en el nombre o datos
                anio = None
                m_anio = re.search(r'\b(20\d\d)\b', nom)
                if m_anio:
                    anio = int(m_anio.group(1))

                result.append({
                    "id":            cid,
                    "nombre":        nom,
                    "color":         c.get("color_curso", "#0f3460"),
                    "avance":        c.get("avance"),          # int o None
                    "items_obl":     c.get("cant_items_obl", 0),
                    "ultimo_acceso": c.get("ultimo_acceso", ""),
                    "favorito":      bool(c.get("favorito")),
                    "anio":          anio,
                })
            return result
        except (json.JSONDecodeError, Exception):
            pass
    return []


def _parse_novedades(scripts: list[str]) -> list[dict]:
    """Extrae novedades con toda su información del campo 'data'."""
    for sc in scripts:
        if '"clase"' not in sc or '"link"' not in sc or len(sc) < 5000:
            continue
        novs_raw = re.findall(r'\[\{[^[]*?"clase"[^[]*?\}\]', sc, re.DOTALL)
        result = []
        for nr in novs_raw:
            try:
                lista = json.loads(nr.replace("\\u0026", "&"))
                for n in lista:
                    if not isinstance(n, dict) or "clase" not in n:
                        continue
                    data = n.get("data") or {}
                    result.append({
                        "clase":        n.get("clase", ""),
                        "cant":         n.get("cant", 1),
                        "no_leidos":    n.get("no_leidos", 0),
                        "fecha":        n.get("fecha", ""),
                        "color":        n.get("color", "#0f3460"),
                        "id_curso":     n.get("id_curso", ""),
                        "link":         n.get("link", ""),
                        # Datos ricos
                        "nombre_curso":  data.get("nombre_curso", ""),
                        "nombre_unidad": data.get("nombre_unidad", ""),
                        "nombre_item":  (data.get("nombre_prg_texto") or
                                         data.get("nombre_actividad") or
                                         data.get("nombre_calificacion") or ""),
                    })
            except (json.JSONDecodeError, Exception):
                pass
        if result:
            return result
    return []


def fmt_fecha(fecha_str: str) -> str:
    """Convierte '2026 08 18 20 51' a descripción relativa."""
    try:
        dt   = datetime.strptime(fecha_str.strip(), "%Y %m %d %H %M")
        diff = datetime.now() - dt
        if diff.days == 0:
            h = diff.seconds // 3600
            return f"hace {diff.seconds//60} min" if h == 0 else f"hace {h}h"
        if diff.days == 1:  return "ayer"
        if diff.days < 7:   return f"hace {diff.days} días"
        if diff.days < 30:  return f"hace {diff.days//7} semana(s)"
        if diff.days < 365: return f"hace {diff.days//30} mes(es)"
        return f"hace {diff.days//365} año(s)"
    except Exception:
        return fecha_str


def es_reciente(fecha_str: str, dias: int = 7) -> bool:
    """True si la fecha es más nueva que `dias` días."""
    try:
        dt   = datetime.strptime(fecha_str.strip(), "%Y %m %d %H %M")
        return (datetime.now() - dt).days <= dias
    except Exception:
        return True
