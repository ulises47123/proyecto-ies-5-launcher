"""
backend/sitio_informativo.py — Scraper para la plataforma informativa pública del IES N°5:
URL: https://ies5tello-juj.infd.edu.ar/sitio/

No requiere autenticación. Extrae artículos, noticias, hipervínculos y documentos PDF adjuntos.
Descarga y almacena localmente los PDFs y textos extraídos en cache/sitio/ y gestiona
una caché incremental en cache_sitio_informativo.json.
"""
import os
import re
import zlib
import json
import hashlib
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from config import CACHE_SITIO_DIR, CACHE_SITIO_FILE, cargar_cache_sitio, guardar_cache_sitio

BASE_SITIO_URL = "https://ies5tello-juj.infd.edu.ar/sitio/"

logger = logging.getLogger(__name__)


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extrae texto limpio de un flujo binario de PDF usando descompresión de streams
    zlib y expresiones regulares sin requerir dependencias pesadas externas.
    """
    try:
        text_chunks = []
        stream_pattern = re.compile(rb'stream[\r\n]+(.*?)[\r\n]+endstream', re.DOTALL)
        tj_pattern = re.compile(r'\((.*?)\)\s*Tj')
        tj_array_pattern = re.compile(r'\[(.*?)\]\s*TJ')
        hex_tj_pattern = re.compile(r'<([0-9a-fA-F]+)>\s*Tj')

        for match in stream_pattern.finditer(pdf_bytes):
            stream_data = match.group(1)
            decompressed = None
            try:
                decompressed = zlib.decompress(stream_data)
            except Exception:
                try:
                    decompressed = zlib.decompress(stream_data, -15)
                except Exception:
                    decompressed = stream_data

            if decompressed:
                try:
                    decoded = decompressed.decode('latin-1', errors='ignore')
                except Exception:
                    continue

                # Extraer texto de operadores (string) Tj
                for tj in tj_pattern.finditer(decoded):
                    t = tj.group(1).replace(r'\(', '(').replace(r'\)', ')').replace(r'\\', '\\')
                    if t.strip():
                        text_chunks.append(t.strip())

                # Extraer texto de operadores [(str1) -10 (str2)] TJ
                for arr in tj_array_pattern.finditer(decoded):
                    inside = arr.group(1)
                    sub_parts = re.findall(r'\((.*?)\)', inside)
                    if sub_parts:
                        line = "".join(sub_parts).replace(r'\(', '(').replace(r'\)', ')').replace(r'\\', '\\')
                        if line.strip():
                            text_chunks.append(line.strip())

                # Extraer texto de operadores hexadecimales <48656c6c6f> Tj
                for hex_tj in hex_tj_pattern.finditer(decoded):
                    try:
                        hex_str = hex_tj.group(1)
                        if len(hex_str) % 2 != 0:
                            hex_str += '0'
                        t_bytes = bytes.fromhex(hex_str)
                        t = t_bytes.decode('latin-1', errors='ignore').strip()
                        if t:
                            text_chunks.append(t)
                    except Exception:
                        pass

        clean_text = " ".join(text_chunks)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text
    except Exception as e:
        logger.error(f"Error al extraer texto del PDF: {e}")
        return ""


class SitioInformativoScraper:
    """Scraper para el sitio web institucional y documentos informativos."""

    def __init__(self, base_url: str = BASE_SITIO_URL, cache_dir: str = CACHE_SITIO_DIR):
        self.base_url = base_url
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.http = requests.Session()
        self.http.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9",
        })

    def scrape_completo(self, max_articulos: int = 25) -> dict:
        """
        Ejecuta el scraping incremental del sitio institucional.
        Retorna la estructura de caché actualizada.
        """
        cache = cargar_cache_sitio()
        if not cache:
            cache = {
                "ultima_actualizacion": "",
                "recursos": {}
            }

        recursos = cache.get("recursos", {})

        try:
            resp = self.http.get(self.base_url, timeout=20)
            if resp.status_code != 200:
                logger.warning(f"Error al acceder al sitio informativo: Status {resp.status_code}")
                return cache

            soup = BeautifulSoup(resp.content, "html.parser")

            # 1. Extraer menú de navegación y botones institucionales
            secciones = []
            for nav in soup.find_all(["nav", "ul", "div"], class_=re.compile(r'menu|nav|navbar|header', re.I)):
                for a in nav.find_all("a", href=True):
                    href = a["href"].strip()
                    texto = a.get_text(strip=True)
                    if href and texto and not href.startswith("#") and not href.startswith("javascript:"):
                        full_url = urljoin(self.base_url, href)
                        secciones.append({"titulo": texto, "url": full_url})

            # Guardar la página principal en la caché
            main_hash = hashlib.md5(resp.content).hexdigest()
            main_text = soup.get_text(separator="\n", strip=True)
            recursos[self.base_url] = {
                "titulo": soup.title.string if soup.title else "IES N°5 Tello - Sitio Oficial",
                "url": self.base_url,
                "tipo": "html_principal",
                "fecha_extraccion": datetime.now().isoformat(),
                "hash": main_hash,
                "texto_preview": main_text[:1000],
                "secciones_menu": secciones[:20]
            }

            # 2. Extraer artículos de noticias, publicaciones y entradas
            articulos = soup.find_all(["article", "div"], class_=re.compile(r'post|entry|noticia|item|article', re.I))
            enlaces_articulos = set()

            for art in articulos:
                for a in art.find_all("a", href=True):
                    href = a["href"].strip()
                    if href and not href.startswith("#") and "ies5tello-juj.infd.edu.ar" in href:
                        enlaces_articulos.add(urljoin(self.base_url, href))

            if not enlaces_articulos:
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    if href and "/sitio/" in href and not href.endswith((".jpg", ".png", ".pdf", ".css", ".js")) and href != self.base_url:
                        enlaces_articulos.add(urljoin(self.base_url, href))

            # 3. Extraer enlaces directos a archivos PDF
            enlaces_pdf = set()
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if href.lower().endswith(".pdf") or ".pdf" in href.lower():
                    enlaces_pdf.add((urljoin(self.base_url, href), a.get_text(strip=True) or "Documento PDF"))

            # Procesar artículos de noticias
            count_art = 0
            for url_art in list(enlaces_articulos)[:max_articulos]:
                count_art += 1
                try:
                    self._procesar_pagina_articulo(url_art, recursos, enlaces_pdf)
                except Exception as e:
                    logger.error(f"Error procesando artículo {url_art}: {e}")

            # Procesar archivos PDF encontrados (hasta max_articulos por ciclo)
            for pdf_url, pdf_titulo in list(enlaces_pdf)[:max_articulos]:
                try:
                    self._procesar_pdf(pdf_url, pdf_titulo, recursos)
                except Exception as e:
                    logger.error(f"Error procesando PDF {pdf_url}: {e}")

            cache["ultima_actualizacion"] = datetime.now().isoformat()
            cache["total_recursos"] = len(recursos)
            cache["recursos"] = recursos
            guardar_cache_sitio(cache)
            logger.info(f"Scraping completado: {len(recursos)} recursos indexados.")
            return cache

        except Exception as e:
            logger.error(f"Excepción general en SitioInformativoScraper: {e}")
            return cache

    def _procesar_pagina_articulo(self, url: str, recursos: dict, enlaces_pdf: set):
        if url.lower().endswith(".pdf") or ".pdf" in url.lower():
            self._procesar_pdf(url, os.path.basename(url), recursos)
            return

        etag_prev = recursos.get(url, {}).get("etag")
        headers = {}
        if etag_prev:
            headers["If-None-Match"] = etag_prev

        try:
            r = self.http.get(url, headers=headers, timeout=15)
            if r.status_code == 304:
                return
            if r.status_code != 200:
                return

            if "application/pdf" in r.headers.get("Content-Type", "").lower() or r.content.startswith(b"%PDF"):
                self._procesar_pdf(url, os.path.basename(url), recursos)
                return

            soup = BeautifulSoup(r.content, "html.parser")
            titulo = soup.find(["h1", "h2", "title"])
            titulo_str = titulo.get_text(strip=True) if titulo else url

            fecha_elem = soup.find(class_=re.compile(r'date|fecha|time|published', re.I))
            fecha_str = fecha_elem.get_text(strip=True) if fecha_elem else ""

            content_div = soup.find(["div", "article", "section"], class_=re.compile(r'content|entry-content|post-content|cuerpo', re.I))
            if content_div:
                texto = content_div.get_text(separator="\n", strip=True)
                for a in content_div.find_all("a", href=True):
                    h = a["href"].strip()
                    if ".pdf" in h.lower():
                        enlaces_pdf.add((urljoin(url, h), a.get_text(strip=True) or titulo_str))
            else:
                texto = soup.get_text(separator="\n", strip=True)

            url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
            txt_filename = f"articulo_{url_hash}.txt"
            txt_path = os.path.join(self.cache_dir, txt_filename)

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"TITULO: {titulo_str}\nURL: {url}\nFECHA: {fecha_str}\n\n{texto}")

            recursos[url] = {
                "titulo": titulo_str,
                "url": url,
                "tipo": "articulo",
                "fecha_noticia": fecha_str,
                "fecha_extraccion": datetime.now().isoformat(),
                "etag": r.headers.get("ETag", ""),
                "last_modified": r.headers.get("Last-Modified", ""),
                "archivo_txt": txt_path,
                "texto": texto[:4000]
            }
        except Exception as e:
            logger.error(f"Error al procesar artículo {url}: {e}")

    def _procesar_pdf(self, pdf_url: str, titulo: str, recursos: dict):
        url_hash = hashlib.md5(pdf_url.encode('utf-8')).hexdigest()
        filename_base = f"doc_{url_hash}"
        pdf_path = os.path.join(self.cache_dir, f"{filename_base}.pdf")
        txt_path = os.path.join(self.cache_dir, f"{filename_base}.txt")

        if pdf_url in recursos and os.path.exists(pdf_path) and os.path.exists(txt_path):
            return

        try:
            r = self.http.get(pdf_url, timeout=30)
            if r.status_code != 200:
                return

            pdf_bytes = r.content
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)

            texto_extraido = extract_text_from_pdf_bytes(pdf_bytes)

            if not texto_extraido.strip():
                texto_extraido = f"Documento PDF: {titulo} ({pdf_url})"

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"DOCUMENTO PDF: {titulo}\nURL: {pdf_url}\nFECHA DESCARGA: {datetime.now().isoformat()}\n\n{texto_extraido}")

            recursos[pdf_url] = {
                "titulo": titulo or os.path.basename(urlparse(pdf_url).path),
                "url": pdf_url,
                "tipo": "pdf",
                "fecha_extraccion": datetime.now().isoformat(),
                "tamano_bytes": len(pdf_bytes),
                "archivo_pdf": pdf_path,
                "archivo_txt": txt_path,
                "texto": texto_extraido[:5000]
            }
            logger.info(f"PDF descargado y procesado: {pdf_url} ({len(texto_extraido)} caracteres extraídos)")
        except Exception as e:
            logger.error(f"Error descargando o procesando PDF {pdf_url}: {e}")


def buscar_en_sitio_informativo(query: str, max_resultados: int = 5) -> list[dict]:
    """Busca palabras clave en los artículos y PDFs cacheados del sitio institucional."""
    cache = cargar_cache_sitio()
    recursos = cache.get("recursos", {})
    if not recursos:
        return []

    tokens = [t.lower() for t in query.split() if len(t) > 2]
    if not tokens:
        tokens = [query.lower()]

    resultados = []
    for url, data in recursos.items():
        score = 0
        titulo = data.get("titulo", "").lower()
        texto = data.get("texto", "").lower()

        for tok in tokens:
            if tok in titulo:
                score += 10
            if tok in texto:
                score += texto.count(tok)

        if score > 0:
            resultados.append({
                "score": score,
                "titulo": data.get("titulo"),
                "url": url,
                "tipo": data.get("tipo"),
                "texto": data.get("texto", "")[:400]
            })

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:max_resultados]
