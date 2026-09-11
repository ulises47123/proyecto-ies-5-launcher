"""
backend/escritorio.py — Obtiene cursos y novedades del escritorio del campus.
Extrae dinámicamente todas las materias inscriptas y novedades sin truncamiento.
"""
import re
import json

from backend.session import CampusSession
from backend.scraper import decode_html, get_scripts
from config import DESK_URL


def get_escritorio(sess: CampusSession, page_size: int = 120) -> tuple[list, list, str]:
    """
    Descarga escritorio.cgi y devuelve (cursos, novedades, nombre_usuario).
    """
    url_req = f"{DESK_URL}?page_size={page_size}&wModulo=AccesoGrupos&wAccion=cambiar_page_size"
    r = sess.get(url_req)
    html = decode_html(r.content)

    if 'AccesoGrupos' not in html:
        r = sess.get(DESK_URL)
        html = decode_html(r.content)

    from backend.user import get_current_user
    user_info = get_current_user(sess)
    nombre = user_info.get("nombre") or getattr(sess, "nombre", "") or getattr(sess, "usuario", "")

    scripts = get_scripts(html)

    cursos = _parse_cursos(scripts)
    novedades = _parse_novedades(scripts)

    if nombre:
        sess.nombre = nombre

    return cursos, novedades, nombre


def _parse_cursos(scripts: list[str]) -> list[dict]:
    """Extrae la lista completa de cursos del script del escritorio."""
    for sc in scripts:
        if '"nombre"' not in sc or '"id"' not in sc or len(sc) < 1000:
            continue

        # Regex para capturar el arreglo JSON completo de cursos
        candidates = re.findall(r'(\[\s*\{.*?"id"\s*:.*?"nombre"\s*:.*?\}\s*\])', sc, re.DOTALL)
        if not candidates:
            candidates = re.findall(r'(\[\s*\{.*?"cant_items_obl".*?\}\s*\])', sc, re.DOTALL)

        for cand in candidates:
            try:
                data = json.loads(cand)
                if isinstance(data, list) and len(data) > 0:
                    seen, result = set(), []
                    for c in data:
                        if not isinstance(c, dict):
                            continue
                        cid = str(c.get("id", ""))
                        if not cid or cid in seen:
                            continue
                        seen.add(cid)
                        nom = c.get("nombre", "Sin nombre")
                        m_anio = re.search(r'\b(20\d\d)\b', nom)
                        anio = int(m_anio.group(1)) if m_anio else None

                        result.append({
                            "id":            cid,
                            "nombre":        nom,
                            "color":         c.get("color_curso", "#6366f1"),
                            "avance":        c.get("avance", 70),
                            "items_obl":     c.get("cant_items_obl", 0),
                            "ultimo_acceso": c.get("ultimo_acceso", "Reciente"),
                            "favorito":      bool(c.get("favorito")),
                            "anio":          anio,
                        })
                    if result:
                        return result
            except (json.JSONDecodeError, Exception):
                pass
    return []


def _parse_novedades(scripts: list[str]) -> list[dict]:
    """Extrae novedades completas de la plataforma."""
    for sc in scripts:
        if '"clase"' not in sc or '"link"' not in sc or len(sc) < 1000:
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
                        "color":        n.get("color", "#6366f1"),
                        "id_curso":     n.get("id_curso", ""),
                        "link":         n.get("link", ""),
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
