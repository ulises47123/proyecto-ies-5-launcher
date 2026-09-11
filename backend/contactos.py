"""
backend/contactos.py — Obtiene contactos (docentes y compañeros), detalles de perfil y estadísticas.
URL: contactos.cgi?id_curso=ID y perfil.cgi?id_usuario=ID&id_curso=ID
"""
import re
import json
import csv
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from backend.session import CampusSession
from backend.scraper import decode_html, limpiar_html, get_scripts
from config import BASE_URL, cargar_cache_contactos, guardar_cache_contactos


def get_detalle_contacto(sess: CampusSession, id_curso: str, uid: str) -> dict:
    """
    Obtiene los datos detallados de la ficha / pop-up de perfil de un contacto:
    Nombre, Email, Teléfono, Lugar (Localidad/Provincia/País), Foto, Documento, etc.
    """
    url = f"{BASE_URL}perfil.cgi?id_usuario={uid}&id_curso={id_curso}"
    try:
        r = sess.get(url, timeout=10)
        html = decode_html(r.content)
        soup = BeautifulSoup(html, 'html.parser')

        # 1. Nombre
        nombre = ""
        div_nom = soup.find('div', class_='nombre')
        if div_nom:
            nombre = div_nom.get_text().strip()

        # 2. Foto
        foto_url = ""
        img = (
            soup.find('img', class_=re.compile(r'perfil|foto|avatar|user', re.I)) or
            soup.find('img', src=re.compile(r'foto|ver_foto|archivos|imagen|perfil', re.I)) or
            soup.find('img')
        )
        if img:
            foto_src = img.get('src', '')
            if foto_src and not any(k in foto_src.lower() for k in ['spacer', 'pixel', 'icon', 'blank', 'bullet']):
                foto_url = foto_src if foto_src.startswith("http") else f"{BASE_URL}{foto_src.lstrip('/')}"

        # 3. Correo electrónico principal
        email = ""
        datos_base = soup.find('ul', class_='datos_base')
        if datos_base:
            for li in datos_base.find_all('li'):
                txt = li.get_text().strip()
                if '@' in txt:
                    email = txt
                    break

        if not email:
            for a in soup.find_all('a'):
                h = a.get('href', '')
                if 'mailto:' in h:
                    email = a.get_text().strip().replace('mailto:', '')
                    break

        # 4. Campos detallados
        telefono = ""
        localidad = ""
        provincia = ""
        pais = ""
        documento = ""
        nacimiento = ""
        genero = ""
        comentarios = ""

        # Leer datos_base adicionales (nacimiento, documento)
        for ul in soup.find_all('ul', class_='datos_base'):
            for li in ul.find_all('li'):
                t_li = li.get_text().strip()
                if 'nacimiento' in t_li.lower():
                    nacimiento = t_li.replace('Fecha de nacimiento', '').strip()
                elif 'documento' in t_li.lower():
                    documento = t_li.replace('Documento', '').strip()

        # Leer listas de sección
        for li in soup.find_all('li'):
            lbl = li.find('span', class_='label') or li.find('div', class_='label')
            if lbl:
                lbl_k = lbl.get_text().strip().lower()
                val_v = li.get_text().replace(lbl.get_text(), '').strip()
                if any(k in lbl_k for k in ['teléfono', 'telefono', 'móvil', 'celular']) and not telefono:
                    telefono = val_v
                elif 'localidad' in lbl_k and not localidad:
                    localidad = val_v
                elif 'provincia' in lbl_k and not provincia:
                    provincia = val_v
                elif any(k in lbl_k for k in ['país', 'pais']) and not pais:
                    pais = val_v
                elif 'dirección' in lbl_k and not email and '@' in val_v:
                    email = val_v
                elif 'género' in lbl_k or 'genero' in lbl_k:
                    genero = val_v
                elif 'comentarios' in lbl_k:
                    comentarios = val_v

        partes_lugar = [p for p in [localidad, provincia, pais] if p]
        lugar = ", ".join(partes_lugar) if partes_lugar else "No especificado"

        return {
            "id": uid,
            "nombre": nombre,
            "email": email or "No especificado",
            "telefono": telefono or "No especificado",
            "lugar": lugar,
            "foto_url": foto_url,
            "documento": documento,
            "nacimiento": nacimiento,
            "genero": genero,
            "comentarios": comentarios
        }
    except Exception:
        return {
            "id": uid,
            "nombre": "",
            "email": "No especificado",
            "telefono": "No especificado",
            "lugar": "No especificado",
            "foto_url": "",
            "documento": "",
            "nacimiento": "",
            "genero": "",
            "comentarios": ""
        }


def get_contactos(sess: CampusSession, id_curso: str, obtener_detalles_completos: bool = True, forzar_recarga: bool = False) -> dict:
    """
    Devuelve {"docentes": [...], "alumnos": [...]}.
    Implementa caché persistente de 2 días según Requerimiento 5.
    """
    cache = cargar_cache_contactos()
    curso_cache = cache.get(str(id_curso), {})
    
    if not forzar_recarga and curso_cache.get("fecha_actualizacion") and curso_cache.get("datos"):
        try:
            dt = datetime.strptime(curso_cache["fecha_actualizacion"], "%Y-%m-%d %H:%M:%S")
            # Si tiene menos de 2 días (48 horas), usar datos en caché
            if datetime.now() - dt < timedelta(days=2):
                return curso_cache["datos"]
        except Exception:
            pass

    # Si pasaron más de 2 días o no existe caché, consultar servidor
    r = sess.get(BASE_URL + f"contactos.cgi?id_curso={id_curso}")
    html = decode_html(r.content)
    datos = _parse_contactos(sess, html, id_curso, obtener_detalles_completos)

    # Guardar en caché con timestamp
    cache[str(id_curso)] = {
        "fecha_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "datos": datos
    }
    guardar_cache_contactos(cache)
    return datos


def _parse_contactos(sess: CampusSession, html: str, id_curso: str, obtener_detalles: bool = True) -> dict:
    docentes = []
    alumnos = []

    # Método 1: Extraer del objeto JS nativo de Educativa
    for tipo, lista_target, rol_nombre in [('P', docentes, 'Docente'), ('A', alumnos, 'Alumno')]:
        m = re.search(rf'Educativa\.Aula\.Contactos\.data\.{tipo}\.items\s*=\s*(\[\{{.*?\}}]);', html, re.DOTALL)
        if m:
            try:
                items = json.loads(m.group(1))
                for item in items:
                    uid = str(item.get("id_usuario", ""))
                    nombre = item.get("apellido_nombre") or item.get("nombre") or ""
                    telefono = item.get("telefono") or item.get("mobile") or ""
                    foto = (
                        item.get("foto") or
                        item.get("foto_url") or
                        item.get("url_foto") or
                        item.get("imagen") or
                        item.get("avatar") or
                        item.get("url_thumb") or ""
                    )
                    if foto and not foto.startswith("http"):
                        foto = f"{BASE_URL}{foto.lstrip('/')}"
                    
                    if nombre:
                        nombre_limpio = limpiar_html(str(nombre)).strip()
                        if nombre_limpio and nombre_limpio.lower() not in ('apellido', 'nombre', 'check all'):
                            lista_target.append({
                                "id": uid,
                                "nombre": nombre_limpio,
                                "rol": rol_nombre,
                                "email": "No especificado",
                                "telefono": str(telefono).strip() if telefono else "No especificado",
                                "lugar": "No especificado",
                                "foto_url": foto
                            })
            except Exception:
                pass

    # Método 2: Fallback por HTML con BeautifulSoup
    if not docentes and not alumnos:
        soup = BeautifulSoup(html, 'html.parser')
        for tr in soup.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) >= 2:
                nombre = tds[1].get_text().strip() if len(tds) > 1 else tds[0].get_text().strip()
                if not nombre or nombre.lower() in ('apellido', 'nombre', 'alumno', 'docente', 'check all'):
                    continue
                mailto = tr.find('a', href=lambda h: h and 'mailto:' in h)
                email = mailto.get_text().strip() if mailto else 'No especificado'
                rol = "Docente" if "docente" in str(tr).lower() else "Alumno"
                inp = tr.find('input', {'type': 'checkbox'})
                uid = inp.get('value', '') if inp else ''

                foto_src = ""
                img_tag = tr.find('img')
                if img_tag and img_tag.get('src'):
                    s_url = img_tag.get('src')
                    if s_url and not any(k in s_url.lower() for k in ['spacer', 'pixel', 'icon', 'blank', 'bullet']):
                        foto_src = s_url if s_url.startswith("http") else f"{BASE_URL}{s_url.lstrip('/')}"

                persona = {
                    "id": uid,
                    "nombre": nombre,
                    "rol": rol,
                    "email": email,
                    "telefono": "No especificado",
                    "lugar": "No especificado",
                    "foto_url": foto_src
                }
                if rol == "Docente":
                    docentes.append(persona)
                else:
                    alumnos.append(persona)

    # Enriquecer con los datos de perfil (Email, Teléfono, Lugar)
    if obtener_detalles:
        for p in (docentes + alumnos):
            if p.get("id"):
                detalles = get_detalle_contacto(sess, id_curso, p["id"])
                if detalles.get("email") and detalles["email"] != "No especificado":
                    p["email"] = detalles["email"]
                if detalles.get("telefono") and detalles["telefono"] != "No especificado":
                    p["telefono"] = detalles["telefono"]
                if detalles.get("lugar") and detalles["lugar"] != "No especificado":
                    p["lugar"] = detalles["lugar"]
                if detalles.get("foto_url") and not p.get("foto_url"):
                    p["foto_url"] = detalles["foto_url"]
                p.update({
                    "documento": detalles.get("documento", ""),
                    "nacimiento": detalles.get("nacimiento", ""),
                    "genero": detalles.get("genero", ""),
                    "comentarios": detalles.get("comentarios", "")
                })

    return {"docentes": docentes, "alumnos": alumnos}


def exportar_contactos_csv(contactos_data: dict, ruta_archivo: str):
    """Guarda los contactos extraídos en formato CSV."""
    todos = []
    for d in contactos_data.get("docentes", []):
        todos.append({
            "Rol": "Docente",
            "Nombre_Apellido": d.get("nombre", ""),
            "Email": d.get("email", ""),
            "Telefono": d.get("telefono", ""),
            "Lugar": d.get("lugar", "")
        })
    for a in contactos_data.get("alumnos", []):
        todos.append({
            "Rol": "Alumno",
            "Nombre_Apellido": a.get("nombre", ""),
            "Email": a.get("email", ""),
            "Telefono": a.get("telefono", ""),
            "Lugar": a.get("lugar", "")
        })

    with open(ruta_archivo, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["Rol", "Nombre_Apellido", "Email", "Telefono", "Lugar"])
        writer.writeheader()
        writer.writerows(todos)


def get_estadisticas(sess: CampusSession) -> dict:
    """
    Obtiene estadísticas generales del alumno.
    URL: estadisticas.cgi
    """
    r = sess.get(BASE_URL + "estadisticas.cgi")
    html = decode_html(r.content)
    return _parse_estadisticas(html)


def _parse_estadisticas(html: str) -> dict:
    """Extrae datos de actividad, acceso, avance por materia."""
    stats = {
        "accesos_por_curso": [],
        "ultima_conexion":   "",
        "total_actividades": 0,
        "raw_texto":         "",
    }

    txt = limpiar_html(html)
    lines = [l.strip() for l in txt.splitlines() if l.strip() and len(l.strip()) > 3]
    stats["raw_texto"] = "\n".join(lines[5:60])

    scripts = get_scripts(html)
    for sc in scripts:
        if 'actividad' in sc.lower() and len(sc) > 500:
            arrays = re.findall(r'(\[\{.*?actividad.*?\}\])', sc, re.DOTALL | re.IGNORECASE)
            for a in arrays[:3]:
                try:
                    data = json.loads(a)
                    for item in data:
                        if isinstance(item, dict) and "nombre" in item:
                            stats["accesos_por_curso"].append({
                                "nombre": item.get("nombre", ""),
                                "accesos": item.get("cantidad_accesos", item.get("accesos", 0)),
                            })
                    if stats["accesos_por_curso"]:
                        break
                except Exception:
                    pass
            if stats["accesos_por_curso"]:
                break

    return stats
