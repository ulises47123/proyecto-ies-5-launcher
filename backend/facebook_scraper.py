"""
backend/facebook_scraper.py — Scraper para la página de Facebook institucional con soporte OCR:
URL: https://www.facebook.com/people/Unidad-IES-5-unidos-por-y-para-los-estudiantes/100063943129231/

Maneja credenciales cifradas con DPAPI (~/.campus_tello/fb_creds), descarga de imágenes de publicaciones
a cache/facebook/imagenes/ y extracción de texto mediante OCR (pytesseract si está disponible).
Guarda la información en cache_facebook.json.
"""
import os
import re
import json
import hashlib
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from config import (CACHE_FB_IMG_DIR, CACHE_FB_FILE, cargar_cache_fb,
                    guardar_cache_fb, cargar_fb_creds)

DEFAULT_FB_URLS = [
    "https://www.facebook.com/groups/1709889895904606",
    "https://www.facebook.com/people/Unidad-IES-5-unidos-por-y-para-los-estudiantes/100063943129231/"
]

logger = logging.getLogger(__name__)

# Intentar importar pytesseract y PIL
try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import pytesseract
    _tesseract_disponible = True
except ImportError:
    pytesseract = None
    _tesseract_disponible = False


def aplicar_ocr_a_imagen(ruta_imagen: str) -> str:
    """
    Aplica OCR a un archivo de imagen si pytesseract y el binario tesseract están disponibles.
    Si no está instalado en el sistema, retorna un aviso limpio y seguro.
    """
    if not Image or not os.path.exists(ruta_imagen):
        return ""

    if not pytesseract:
        return "[OCR no disponible: pytesseract no instalado en el entorno]"

    try:
        rutas_posibles_tesseract = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
        ]
        for ruta in rutas_posibles_tesseract:
            if os.path.exists(ruta):
                pytesseract.pytesseract.tesseract_cmd = ruta
                break

        img = Image.open(ruta_imagen)
        texto = pytesseract.image_to_string(img, lang="spa")
        texto_limpio = " ".join(texto.split()).strip()
        return texto_limpio if texto_limpio else "[Imagen procesada sin texto detectable]"
    except Exception as e:
        logger.warning(f"No se pudo ejecutar OCR en {ruta_imagen}: {e}")
        return f"[Aviso OCR: {str(e)[:50]}]"


class FacebookScraper:
    """Scraper institucional para grupos y páginas de Facebook con OCR."""

    def __init__(self, page_url: str = None, cache_dir: str = CACHE_FB_IMG_DIR):
        self.page_url = page_url or DEFAULT_FB_URLS[0]
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.http = requests.Session()
        self.http.headers.update({
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            "Accept-Language": "es-ES,es;q=0.9",
        })

    def autenticar(self, usuario: str = None, clave: str = None) -> bool:
        """
        Intenta autenticarse en Facebook usando las credenciales provistas o guardadas.
        Detecta y documenta requerimientos de checkpoint/2FA.
        """
        if not usuario or not clave:
            usuario, clave = cargar_fb_creds()

        if not usuario or not clave:
            logger.info("No hay credenciales de Facebook configuradas; procediendo en modo extracción pública/móvil.")
            return False

        try:
            init_resp = self.http.get("https://mbasic.facebook.com/login", timeout=15)
            soup = BeautifulSoup(init_resp.content, "html.parser")
            form = soup.find("form")
            if not form:
                return False

            payload = {inp.get("name"): inp.get("value", "") for inp in form.find_all("input") if inp.get("name")}
            payload["email"] = usuario
            payload["pass"] = clave

            action_url = form.get("action", "https://mbasic.facebook.com/login/device-based/regular/login/")
            if not action_url.startswith("http"):
                action_url = "https://mbasic.facebook.com" + action_url

            resp = self.http.post(action_url, data=payload, timeout=20, allow_redirects=True)
            if "c_user" in self.http.cookies.get_dict():
                logger.info("Autenticación en Facebook exitosa (c_user establecido).")
                return True
            else:
                logger.info("Login en Facebook evaluado (Facebook requiere verificación de seguridad o cookies de navegador).")
                return False
        except Exception as e:
            logger.warning(f"Error al intentar login en Facebook: {e}")
            return False

    def scrape_publicaciones(self, max_posts: int = 15, url_override: str = None) -> dict:
        """
        Extrae publicaciones del grupo o página institucional, descarga imágenes asociadas y ejecuta OCR.
        Guarda en cache_facebook.json de forma incremental.
        """
        target_url = url_override or self.page_url
        mobile_url = target_url.replace("www.facebook.com", "m.facebook.com")

        cache = cargar_cache_fb()
        if not cache:
            cache = {
                "ultima_actualizacion": "",
                "posts": []
            }

        posts_existentes = {p.get("id"): p for p in cache.get("posts", []) if p.get("id")}

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-es",
            }
            resp = self.http.get(mobile_url, headers=headers, timeout=20)
            soup = BeautifulSoup(resp.content, "html.parser")

            titulo_grupo = soup.title.string.strip() if soup.title else "Grupo IES N°5"
            meta_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
            desc_texto = meta_desc.get("content", "").strip() if meta_desc else ""

            meta_img = soup.find("meta", property="og:image")
            img_url = meta_img.get("content") if meta_img else None

            # Descargar imagen de cabecera / publicación si está disponible
            imagenes_descargadas = []
            ocr_resultado = ""
            if img_url and ("fbcdn" in img_url or "scontent" in img_url):
                img_hash = hashlib.md5(img_url.encode('utf-8')).hexdigest()[:12]
                img_filename = f"fb_group_{img_hash}.jpg"
                img_path = os.path.join(self.cache_dir, img_filename)

                if not os.path.exists(img_path):
                    try:
                        r_img = self.http.get(img_url, timeout=15)
                        if r_img.status_code == 200:
                            with open(img_path, "wb") as f_img:
                                f_img.write(r_img.content)
                    except Exception as e:
                        logger.warning(f"Error descargando imagen de Facebook {img_url}: {e}")

                if os.path.exists(img_path):
                    imagenes_descargadas.append(img_path)
                    ocr_resultado = aplicar_ocr_a_imagen(img_path)

            # Crear publicación estructurada del grupo
            post_id = f"fb_group_1709889895904606"
            texto_completo = f"Publicación y estado del {titulo_grupo}:\n{desc_texto}"
            
            post_obj = {
                "id": post_id,
                "fecha": datetime.now().strftime("%d/%m/%Y"),
                "autor": titulo_grupo,
                "url": target_url,
                "texto": texto_completo,
                "imagenes": imagenes_descargadas,
                "ocr_texto": ocr_resultado if ocr_resultado else "Información oficial del grupo institucional IES J.E. TELLO"
            }
            posts_existentes[post_id] = post_obj

            cache["ultima_actualizacion"] = datetime.now().isoformat()
            cache["posts"] = list(posts_existentes.values())
            guardar_cache_fb(cache)
            logger.info(f"Facebook scraper finalizado: {len(posts_existentes)} publicaciones en caché.")
            return cache

        except Exception as e:
            logger.error(f"Error en FacebookScraper: {e}")
            return cache


def buscar_en_facebook(query: str, max_resultados: int = 5) -> list[dict]:
    """Busca en el texto de las publicaciones y texto extraído por OCR de Facebook."""
    cache = cargar_cache_fb()
    posts = cache.get("posts", [])
    if not posts:
        return []

    tokens = [t.lower() for t in query.split() if len(t) > 2]
    if not tokens:
        tokens = [query.lower()]

    resultados = []
    for p in posts:
        score = 0
        texto = (p.get("texto") or "").lower()
        ocr = (p.get("ocr_texto") or "").lower()

        for tok in tokens:
            if tok in texto:
                score += 5
            if tok in ocr:
                score += 10

        if score > 0:
            resultados.append({
                "score": score,
                "id": p.get("id"),
                "fecha": p.get("fecha"),
                "texto": p.get("texto"),
                "ocr_texto": p.get("ocr_texto"),
                "imagenes": p.get("imagenes", [])
            })

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:max_resultados]
