import os
import tempfile
import base64
import hashlib
from typing import Dict, Any
from backend.session import CampusSession

class ImageService:
    """
    Servicio para resolver imágenes autenticadas (fotos de perfil) que requieren sesión.
    Implementa 4 métodos distintos para asegurar que la imagen siempre llegue al frontend webview.
    """
    
    def __init__(self, session: CampusSession):
        self.session = session
        self.cache_dir = os.path.join(tempfile.gettempdir(), "campus_tello_images")
        os.makedirs(self.cache_dir, exist_ok=True)

    def resolver_imagen(self, url: str, nombre_usuario: str = "", metodo: int = 1) -> Dict[str, Any]:
        """
        Intenta cargar la foto de perfil usando 4 métodos diferentes.
        """
        if not url or url == "null":
            return {"ok": True, "data": self._metodo_4_svg_iniciales(nombre_usuario)}

        try:
            if metodo == 1:
                return {"ok": True, "data": self._metodo_1_base64(url)}
            elif metodo == 2:
                return {"ok": True, "data": self._metodo_2_archivo_local(url)}
            elif metodo == 3:
                return {"ok": True, "data": self._metodo_3_cookies_js(url)}
            else:
                return {"ok": True, "data": self._metodo_4_svg_iniciales(nombre_usuario)}
        except Exception as e:
            # Si falla la red (ej. 404), cae siempre al método 4 (Fallback seguro)
            return {"ok": True, "data": self._metodo_4_svg_iniciales(nombre_usuario)}

    # =========================================================================
    # MÉTODO 1: BASE64 INYECTADO (El más seguro contra CORS/Cookies)
    # =========================================================================
    def _metodo_1_base64(self, url: str) -> str:
        """Descarga la imagen con la sesión de Python y la codifica en Base64."""
        r = self.session.get(url, stream=True)
        r.raise_for_status()
        b64 = base64.b64encode(r.content).decode("utf-8")
        mime = r.headers.get("Content-Type", "image/jpeg")
        return f"data:{mime};base64,{b64}"

    # =========================================================================
    # MÉTODO 2: CACHÉ EN DISCO (Mejor rendimiento, usa file:///)
    # =========================================================================
    def _metodo_2_archivo_local(self, url: str) -> str:
        """Descarga la imagen a una carpeta temporal y devuelve la ruta absoluta file:///."""
        hash_url = hashlib.md5(url.encode()).hexdigest()
        ext = url.split(".")[-1].split("?")[0]
        if len(ext) > 4: ext = "jpg"
        
        file_path = os.path.join(self.cache_dir, f"{hash_url}.{ext}")
        
        # Si ya está en caché, devolverla
        if not os.path.exists(file_path):
            r = self.session.get(url, stream=True)
            r.raise_for_status()
            with open(file_path, "wb") as f:
                f.write(r.content)
                
        return f"file:///{file_path.replace(chr(92), '/')}"

    # =========================================================================
    # MÉTODO 3: EXPORTACIÓN DE COOKIES (Para usar <img src="..."> nativo en JS)
    # =========================================================================
    def _metodo_3_cookies_js(self, url: str) -> Dict[str, Any]:
        """No descarga la imagen, sino que exporta las cookies de sesión para inyectarlas en document.cookie."""
        cookies = self.session.http.cookies.get_dict()
        cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        return {
            "type": "cookie_inject",
            "url": url,
            "cookie_string": cookie_str
        }

    # =========================================================================
    # MÉTODO 4: GENERACIÓN DINÁMICA DE SVG CON INICIALES (Fallback Absoluto)
    # =========================================================================
    def _metodo_4_svg_iniciales(self, nombre: str) -> str:
        """Si todo falla o no hay imagen, crea un SVG estilizado con las iniciales."""
        nombre = nombre.strip() or "Usuario"
        partes = nombre.split()
        iniciales = partes[0][0].upper() if partes else "U"
        if len(partes) > 1:
            iniciales += partes[-1][0].upper()
            
        color_fondo = "#4f46e5" # Indigo 600
        
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
            <rect width="100" height="100" fill="{color_fondo}" rx="50"/>
            <text x="50" y="50" font-family="Arial, sans-serif" font-size="40" font-weight="bold" fill="white" text-anchor="middle" dominant-baseline="central">{iniciales}</text>
        </svg>'''
        
        b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
        return f"data:image/svg+xml;base64,{b64}"
