"""
backend/scraper.py — Funciones de scraping reutilizables.
Parseo HTML, extracción de JSON embebido, limpieza de texto.
"""
import re
import json


def limpiar_html(html: str) -> str:
    """Convierte HTML a texto plano limpio."""
    txt = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    txt = re.sub(r'<style.*?</style>',  '', txt,  flags=re.DOTALL | re.IGNORECASE)
    txt = re.sub(r'<br\s*/?>', '\n', txt, flags=re.IGNORECASE)
    txt = re.sub(r'<[^>]+>', ' ', txt)
    txt = txt.replace('&nbsp;', ' ').replace('&amp;', '&')
    txt = txt.replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')
    txt = re.sub(r'&#\d+;', '', txt)
    txt = re.sub(r'\s*\n\s*', '\n', txt)
    txt = re.sub(r' {2,}', ' ', txt)
    return txt.strip()


def get_scripts(html: str) -> list[str]:
    """Extrae todos los bloques <script> del HTML."""
    return re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)


def find_json_array(scripts: list[str], markers: list[str]) -> list | None:
    """Busca el primer JSON array grande que contenga todos los markers dados."""
    for sc in scripts:
        if not all(m in sc for m in markers):
            continue
        if len(sc) < 500:
            continue
        # Intentar extraer arrays JSON
        candidates = re.findall(r'(\[\{.*?\}\])', sc, re.DOTALL)
        for c in candidates:
            if len(c) < 100:
                continue
            try:
                data = json.loads(c)
                if isinstance(data, list) and data:
                    return data
            except json.JSONDecodeError:
                pass
    return None


def decode_html(raw: bytes) -> str:
    """Decodifica bytes HTML usando latin-1 (encoding del campus)."""
    return raw.decode('latin-1')


def extract_var(html: str, varname: str) -> str:
    """Extrae el valor de una variable JS: var NOMBRE = 'valor';"""
    m = re.search(rf"var\s+{re.escape(varname)}\s*=\s*['\"]([^'\"]*)['\"]", html)
    return m.group(1).strip() if m else ""


def extract_tabla_html(html: str, clase: str) -> list[list[str]]:
    """Extrae filas de una tabla HTML por clase CSS."""
    rows = re.findall(
        rf'<tr[^>]*class=["\'][^"\']*{re.escape(clase)}[^"\']*["\'][^>]*>(.*?)</tr>',
        html, re.DOTALL | re.IGNORECASE
    )
    result = []
    for row in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL | re.IGNORECASE)
        result.append([limpiar_html(c) for c in cells])
    return result
