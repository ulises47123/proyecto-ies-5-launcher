"""
ia/engine.py — Motor de IA: modo local inteligente con soporte de actividades, docentes y formato limpio.
"""
import re
import requests
from datetime import datetime
from config import cargar_api_key, cargar_api, guardar_api, cargar_cache, cargar_cache_contactos
from backend.escritorio import fmt_fecha, es_reciente

TIPOS_NOV = {
    "email":     "Correo",
    "prg_texto": "Texto / Contenido",
    "unidad":    "Nueva Unidad",
    "nota":      "Calificación",
    "actividad": "Actividad",
    "foro":      "Foro",
}


def _limpiar_formato(texto: str) -> str:
    """Limpia asteriscos de markdown excesivos o innecesarios para una presentación clara."""
    # Mantener texto legible sin dobles asteriscos
    return texto.replace("**", "").replace("__", "")


class IAEngine:
    """Motor IA con modo local y soporte de API externa."""

    def __init__(self, campus_session):
        self.campus = campus_session
        self.cursos    = []
        self.novedades = []
        self.cache_data = {}
        
        # Prioridad de carga:
        # 1. Clave guardada de forma segura con DPAPI (~/.campus_tello/api_key)
        # 2. Clave legada en ~/.campus_tello/api
        # 3. Variables de entorno (GEMINI_API_KEY / OPENAI_API_KEY)
        # 4. Modo local (sin clave)
        import os
        key = cargar_api_key()
        provider = "gemini"

        if not key:
            prov_leg, key_leg = cargar_api()
            if key_leg:
                provider = prov_leg or "gemini"
                key = key_leg

        if not key:
            if os.environ.get("GEMINI_API_KEY"):
                provider = "gemini"
                key = os.environ.get("GEMINI_API_KEY")
            elif os.environ.get("OPENAI_API_KEY"):
                provider = "openai"
                key = os.environ.get("OPENAI_API_KEY")

        self.api_key   = key
        self.api_prov  = provider

    def actualizar_datos(self, cursos: list, novedades: list, cache_data: dict = None):
        self.cursos    = cursos
        self.novedades = novedades
        if cache_data:
            self.cache_data = cache_data
        else:
            self.cache_data = cargar_cache()

    def set_api(self, provider: str, key: str):
        self.api_prov = provider.lower()
        self.api_key  = key
        guardar_api(provider, key)

    def tiene_api(self) -> bool:
        return bool(self.api_key)

    # ── Respuesta principal ──────────────────────────────────
    def responder(self, pregunta: str) -> str:
        if self.api_key:
            try:
                resp = self._api_responder(pregunta)
                return _limpiar_formato(resp)
            except Exception as e:
                return f"Nota: Error con la API ({e}). Usando modo local:\n\n" + self._local_responder(pregunta)
        return self._local_responder(pregunta)

    # ── API externa ──────────────────────────────────────────
    def _contexto(self) -> str:
        """Genera contexto completo del campus para la API incluyendo materias, docentes, actividades, novedades, sitio y Facebook."""
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
        cache = self.cache_data or cargar_cache()
        materias_cache = cache.get("materias_detalle", {})

        lines = [
            f"Fecha y hora actual: {ahora}",
            f"Alumno: {self.campus.nombre or self.campus.usuario}",
            "",
            "=== MATERIAS Y DOCENTES ===",
        ]
        
        for c in self.cursos:
            cid = str(c.get("id"))
            c_info = materias_cache.get(cid, {})
            doc = c.get('docente') or c_info.get('docente') or "No especificado"
            av = f"{c['avance']}%" if c.get('avance') is not None else "sin datos"
            ua = fmt_fecha(c['ultimo_acceso']) if c.get('ultimo_acceso') else "nunca"
            lines.append(f"• {c['nombre']} (ID:{cid}) | Docente: {doc} | Avance: {av} | Último acceso: {ua}")
        
        lines.append("")
        lines.append("=== ACTIVIDADES REGISTRADAS ===")
        act_found = False
        for cid, cinfo in materias_cache.items():
            m_nom = cinfo.get("nombre", "")
            for u in cinfo.get("programa", []):
                for it in u.get("items", []):
                    if it.get("tipo") == "actividad":
                        act_found = True
                        lines.append(f"• Actividad: {it.get('titulo')} | Materia: {m_nom} | Unidad: {u.get('nombre')}")
        if not act_found:
            lines.append("• No hay actividades pendientes o registradas en el programa actualmente.")

        lines.append("")
        lines.append("=== NOVEDADES DEL CAMPUS ===")
        if self.novedades:
            for n in self.novedades:
                edad     = fmt_fecha(n.get('fecha', ''))
                reciente = es_reciente(n.get('fecha', ''), 7)
                tipo     = TIPOS_NOV.get(n.get('clase'), n.get('clase', 'Aviso'))
                desc     = n.get('nombre_item') or n.get('nombre_unidad') or ""
                flag     = "RECIENTE" if reciente else "ANTERIOR"
                curso    = n.get('nombre_curso', '')
                lines.append(f"• [{flag}] {tipo}: {desc} | Materia: {curso} | {edad}")
        else:
            lines.append("• No hay novedades recientes registradas.")

        # Información del sitio institucional público
        from config import cargar_cache_sitio, cargar_cache_fb
        sitio_cache = cargar_cache_sitio()
        recursos_sitio = sitio_cache.get("recursos", {})
        if recursos_sitio:
            lines.append("")
            lines.append("=== NOVEDADES Y DOCUMENTOS DEL SITIO INSTITUCIONAL PÚBLICO ===")
            for u, r in list(recursos_sitio.items())[:6]:
                t_str = "PDF" if r.get("tipo") == "pdf" else "Noticia"
                lines.append(f"• [{t_str}] {r.get('titulo')}: {r.get('texto', '')[:200]} (URL: {u})")

        # Publicaciones de Facebook
        fb_cache = cargar_cache_fb()
        fb_posts = fb_cache.get("posts", [])
        if fb_posts:
            lines.append("")
            lines.append("=== PUBLICACIONES DE FACEBOOK INSTITUCIONAL ===")
            for p in fb_posts[:5]:
                ocr_info = f" [OCR imagen: {p.get('ocr_texto')}]" if p.get('ocr_texto') else ""
                lines.append(f"• ({p.get('fecha', '')}) {p.get('texto', '')}{ocr_info}")

        return "\n".join(lines)

    def _api_responder(self, pregunta: str) -> str:
        sistema = (
            "Sos el asistente virtual del campus IES N°5 José Eugenio Tello (Argentina). "
            "Respondés en español de forma amigable, directa, precisa y profesional. "
            "IMPORTANTE: NO uses asteriscos (**) ni formato excesivo. "
            "Escribí los títulos de forma clara y separá el cuerpo del mensaje.\n\n"
            + self._contexto()
        )
        if self.api_prov == "gemini":
            return self._gemini(sistema, pregunta)
        elif self.api_prov == "openai":
            return self._openai(sistema, pregunta)
        raise ValueError(f"Proveedor desconocido: {self.api_prov}")

    def _gemini(self, sistema: str, pregunta: str) -> str:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"gemini-3.6-flash:generateContent?key={self.api_key}")
        payload = {"contents": [{"role": "user", "parts": [
            {"text": sistema + "\n\n---\nPREGUNTA: " + pregunta}
        ]}]}
        
        # Reintentos automáticos ante 503 / sobrecarga temporal
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                r = requests.post(url, json=payload, timeout=30)
                if r.status_code == 503 and attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                r.raise_for_status()
                candidates = r.json().get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    for p in parts:
                        if "text" in p:
                            return p["text"]
                return "No se pudo generar una respuesta con el modelo seleccionado."
            except requests.exceptions.HTTPError as e:
                if attempt < max_retries - 1 and r.status_code in (503, 429):
                    time.sleep(2 * (attempt + 1))
                    continue
                raise e

    def _openai(self, sistema: str, pregunta: str) -> str:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": "gpt-4o-mini", "messages": [
                {"role": "system", "content": sistema},
                {"role": "user",   "content": pregunta},
            ]}, timeout=30
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    # ── Modo local ───────────────────────────────────────────
    def _local_responder(self, pregunta: str) -> str:
        q = pregunta.lower().strip()
        cache = self.cache_data or cargar_cache()
        materias_cache = cache.get("materias_detalle", {})

        if any(w in q for w in ["hola", "buen", "buenas", "hi", "saludos"]):
            return ("¡Hola! Soy tu asistente del campus IES N°5 Tello.\n\n"
                    "Puedo brindarte información sobre tus materias, novedades del campus, progreso académico, "
                    "docentes y actividades pendientes.")

        # Datos personales del alumno dinámicos
        from backend.user import get_current_user
        user_info = get_current_user(self.campus)
        dni = user_info.get("dni") or (getattr(self.campus, "usuario", "") if self.campus else "") or cache.get("usuario", "")
        nombre = user_info.get("nombre") or (getattr(self.campus, "nombre", "") if self.campus else "") or cache.get("nombre", "")

        # Fallback dinámico a caché de contactos si no estuviera disponible
        if not nombre or nombre == dni or nombre.isdigit():
            c_cache = cargar_cache_contactos()
            for cid, cinfo in c_cache.items():
                datos = cinfo.get("datos", {})
                for a in datos.get("alumnos", []):
                    if (dni and a.get("id") == dni) or (dni and a.get("documento") == dni):
                        nombre = a.get("nombre", "")
                        break
                if nombre:
                    break

        if not nombre:
            nombre = "Estudiante"
        if not dni:
            dni = "No disponible"

        if any(w in q for w in ["cómo me llamo", "como me llamo", "mi nombre", "cuál es mi nombre", "cual es mi nombre"]):
            return f"DATOS PERSONALES:\n\nTu nombre registrado en el campus es:\n👤 {nombre}"

        if any(w in q for w in ["cuál es mi dni", "cual es mi dni", "mi dni", "mi documento", "cuál es mi documento", "mi usuario"]):
            return f"DATOS PERSONALES:\n\nTu número de DNI / Usuario es:\n🆔 {dni}"

        if any(w in q for w in ["quién soy", "quien soy", "mis datos"]):
            return f"DATOS PERSONALES DEL ESTUDIANTE:\n\n👤 Nombre completo: {nombre}\n🆔 Documento / DNI: {dni}\n🏛️ Institución: IES N°5 José Eugenio Tello"

        # Materias y Docentes
        if any(w in q for w in ["profesor", "docente", "quien dicta", "quién dicta", "docentes", "profesores"]) or (
            any(w in q for w in ["materia", "curso", "tengo este año", "qué materias tengo", "materias actuales", "cursando"])
        ):
            cursos_actuales = self.cursos
            if not cursos_actuales and cache.get("cursos"):
                cursos_actuales = cache.get("cursos", [])

            if not cursos_actuales:
                return "Las materias aún no se cargaron. Aguardá unos segundos y reintentá."

            # Determinar el ciclo lectivo más reciente de forma dinámica
            anios_disponibles = [c.get("anio") for c in cursos_actuales if c.get("anio")]
            max_anio = max(anios_disponibles) if anios_disponibles else None
            
            if max_anio:
                materias_activas = [c for c in cursos_actuales if c.get("anio") == max_anio or str(max_anio) in c.get("nombre", "")]
            else:
                materias_activas = cursos_actuales

            lista = materias_activas if materias_activas else cursos_actuales

            lines = []
            for c in lista:
                cid = str(c.get("id"))
                nom = c.get('nombre', 'Materia')
                # Obtener docente desde curso o caché
                doc = c.get('docente', '')
                if not doc:
                    c_cache = materias_cache.get(cid, {})
                    doc = c_cache.get("docente", "")
                if not doc:
                    doc = "Consultar en sección Contactos"
                
                av = f"{c['avance']}%" if c.get('avance') is not None else "0%"
                lines.append(f"• {nom}\n  Docente: {doc}\n  Progreso: {av}")

            return "MATERIAS DEL CICLO LECTIVO ACTUAL:\n\n" + "\n\n".join(lines)

        # Actividades entregadas
        if any(w in q for w in ["entregada", "entregado", "realizada", "realizadas", "completada", "completadas"]):
            actividades_entregadas = []
            for cid, cinfo in materias_cache.items():
                m_nom = cinfo.get("nombre", "")
                for u in cinfo.get("programa", []):
                    for it in u.get("items", []):
                        if it.get("tipo") == "actividad" and it.get("estado_color") == "green":
                            f_ap = f" ({it.get('fecha_apertura')})" if it.get('fecha_apertura') else ""
                            actividades_entregadas.append(f"🟢 {it.get('titulo')}\n  Materia: {m_nom}{f_ap}")

            if actividades_entregadas:
                return "ACTIVIDADES ENTREGADAS (AÑO ACTUAL):\n\n" + "\n\n".join(actividades_entregadas)
            else:
                return ("ACTIVIDADES ENTREGADAS:\n\n"
                        "No se registran actividades marcadas como entregadas en tus materias del ciclo actual.")

        # Actividades pendientes / por entregar / consignas
        if any(w in q for w in ["actividad", "pendiente", "por entregar", "sin entregar", "faltan", "tarea", "consigna", "tp", "trabajo", "pendientes"]):
            actividades_pend = []
            actividades_todas = []
            for cid, cinfo in materias_cache.items():
                m_nom = cinfo.get("nombre", "")
                for u in cinfo.get("programa", []):
                    for it in u.get("items", []):
                        if it.get("tipo") == "actividad":
                            color_dot = "🟢" if it.get("estado_color") == "green" else ("🟠" if it.get("estado_color") == "orange" else "🔴")
                            f_ap = f"\n  Fechas: {it.get('fecha_apertura')}" if it.get('fecha_apertura') else ""
                            item_str = f"{color_dot} {it.get('titulo')}\n  Materia: {m_nom} | Estado: {it.get('estado', 'Pendiente')}{f_ap}"
                            actividades_todas.append(item_str)
                            if it.get("estado_color") in ("orange", "red") or "pendiente" in it.get("estado", "").lower():
                                actividades_pend.append(item_str)

            if actividades_pend:
                return "ACTIVIDADES PENDIENTES / ABIERTAS:\n\n" + "\n\n".join(actividades_pend)
            elif actividades_todas:
                return ("ESTADO DE ACTIVIDADES:\n\n"
                        "¡Excelente! No tienes actividades pendientes por entregar en tus materias actuales.\n\n"
                        "Últimas actividades registradas:\n\n" + "\n\n".join(actividades_todas[:6]))
            else:
                return ("ACTIVIDADES:\n\n"
                        "No se registran actividades cargadas en las materias del ciclo actual.")

        # Novedades / Notificaciones
        if any(w in q for w in ["novedad", "notif", "aviso", "nuevo", "publicó", "hay algo", "reciente", "mensaje"]) and not any(w in q for w in ["sitio", "facebook", "fb", "web", "beca", "becas", "examen", "mesas", "resolucion", "inscripcion", "pdf", "documento"]):
            novs = self.novedades or cache.get("novedades", [])
            if not novs:
                return "NOVEDADES DEL CAMPUS:\n\nNo hay novedades recientes registradas en el aula."
            
            lines = []
            for n in novs[:8]:
                edad     = fmt_fecha(n.get('fecha', ''))
                reciente = es_reciente(n.get('fecha', ''), 7)
                tipo     = TIPOS_NOV.get(n.get('clase'), n.get('clase', 'Aviso'))
                desc     = n.get('nombre_item') or n.get('nombre_unidad') or ""
                flag     = "[Reciente]" if reciente else "[Anterior]"
                curso    = (n.get('nombre_curso') or '')[:40]
                
                line = f"{flag} {tipo}"
                if desc:
                    line += f": {desc}"
                line += f"\n  Materia: {curso} ({edad})"
                lines.append(line)

            return "NOVEDADES RECIENTES DEL CAMPUS:\n\n" + "\n\n".join(lines)

        # Consultas de Facebook institucional
        if any(w in q for w in ["facebook", "fb", "red social", "redes", "publicó en facebook", "publicaron en facebook"]):
            from backend.facebook_scraper import buscar_en_facebook
            fb_res = buscar_en_facebook(q)
            if fb_res:
                lines = []
                for p in fb_res[:4]:
                    f = p.get("fecha", "")
                    txt = p.get("texto", "")[:250]
                    ocr = p.get("ocr_texto", "")
                    img_info = f" ({len(p.get('imagenes', []))} imagen/es)" if p.get("imagenes") else ""
                    
                    item_str = f"📢 Publicación ({f}){img_info}:\n{txt}"
                    if ocr and not ocr.startswith("[OCR"):
                        item_str += f"\n  📝 Texto en imagen (OCR): {ocr[:200]}..."
                    lines.append(item_str)
                return "PUBLICACIONES DE FACEBOOK INSTITUCIONAL:\n\n" + "\n\n".join(lines)
            else:
                from config import cargar_cache_fb
                fb_cache = cargar_cache_fb()
                posts = fb_cache.get("posts", [])
                if posts:
                    lines = []
                    for p in posts[:3]:
                        lines.append(f"📢 Publicación ({p.get('fecha', '')}):\n{p.get('texto', '')[:250]}")
                    return "ÚLTIMAS PUBLICACIONES DE FACEBOOK:\n\n" + "\n\n".join(lines)
                return ("FACEBOOK INSTITUCIONAL:\n\n"
                        "No se registran publicaciones cacheadas de Facebook aún. "
                        "Podés configurar tus credenciales en Ajustes o hacer clic en 'Actualizar' en el menú.")

        # Consultas del sitio institucional (noticias públicas, PDFs, becas, inscripciones, etc.)
        if any(w in q for w in ["sitio", "página", "web", "institucional", "beca", "becas", "resolución", "resolucion", "documento", "pdf", "inscripción", "inscripcion", "mesa", "mesas", "comunicado", "parte de prensa", "noticia", "novedades del sitio"]):
            from backend.sitio_informativo import buscar_en_sitio_informativo
            sitio_res = buscar_en_sitio_informativo(q)
            if sitio_res:
                lines = []
                for item in sitio_res[:4]:
                    t_str = "📄 Documento PDF" if item.get("tipo") == "pdf" else "🌐 Noticia/Página"
                    lines.append(f"{t_str}: {item.get('titulo')}\n  Enlace: {item.get('url')}\n  Extracto: {item.get('texto')[:220]}...")
                return "INFORMACIÓN DEL SITIO INSTITUCIONAL:\n\n" + "\n\n".join(lines)
            else:
                from config import cargar_cache_sitio
                sitio_cache = cargar_cache_sitio()
                recursos = sitio_cache.get("recursos", {})
                if recursos:
                    lines = []
                    for u, r in list(recursos.items())[:4]:
                        t_str = "📄 PDF" if r.get("tipo") == "pdf" else "🌐 Noticia"
                        lines.append(f"• {t_str}: {r.get('titulo')}\n  URL: {u}")
                    return "RECURSOS Y NOVEDADES RECIENTES DEL SITIO:\n\n" + "\n\n".join(lines)
                return ("SITIO INSTITUCIONAL:\n\n"
                        "Aún no se ha completado la sincronización del sitio web. "
                        "Podés pulsar el botón 'Actualizar' para indexar las noticias y documentos ahora.")

        # Progreso / Rendimiento / Estadísticas
        if any(w in q for w in ["progreso", "avance", "cuánto llevé", "porcentaje", "estadística", "rendimiento"]):
            cursos_actuales = self.cursos or cache.get("cursos", [])
            if not cursos_actuales:
                return "Aguardá un momento mientras se obtienen los datos..."
            
            anios = [c.get("anio") for c in cursos_actuales if c.get("anio")]
            max_anio = max(anios) if anios else None

            lines = []
            if max_anio:
                for c in cursos_actuales:
                    if c.get("anio") == max_anio or str(max_anio) in c.get("nombre", ""):
                        av = c.get('avance', 0) if c.get('avance') is not None else 0
                        lines.append(f"• {c['nombre']}: {av}% completado")
            if not lines:
                for c in cursos_actuales:
                    av = c.get('avance', 0) if c.get('avance') is not None else 0
                    lines.append(f"• {c['nombre']}: {av}% completado")
            return "PROGRESO ACADÉMICO POR MATERIA:\n\n" + "\n".join(lines)

        # Ayuda
        if any(w in q for w in ["ayuda", "funciones", "qué podés", "comandos"]):
            return ("OPCIONES DISPONIBLES:\n\n"
                    "Podés preguntarme sobre:\n"
                    "• ¿Qué materias tengo? — Lista las asignaturas del año lectivo actual y sus docentes.\n"
                    "• Novedades recientes — Notificaciones y publicaciones del aula virtual.\n"
                    "• Sitio institucional y documentos — Consulta noticias públicas, resoluciones y PDFs del IES N°5.\n"
                    "• Facebook — Consulta publicaciones y comunicados de la página institucional.\n"
                    "• Mi progreso — Porcentaje de avance en cada materia.\n"
                    "• Actividades pendientes — Tareas y trabajos prácticos en las unidades.")

        # Búsqueda general en fuentes externas si no hubo coincidencia estándar
        from backend.sitio_informativo import buscar_en_sitio_informativo
        from backend.facebook_scraper import buscar_en_facebook

        ext_res = buscar_en_sitio_informativo(q, max_resultados=2)
        fb_res = buscar_en_facebook(q, max_resultados=2)

        if ext_res or fb_res:
            res_lines = []
            if ext_res:
                res_lines.append("INFORMACIÓN DEL SITIO INSTITUCIONAL:")
                for r in ext_res:
                    res_lines.append(f"• {r.get('titulo')}\n  URL: {r.get('url')}\n  {r.get('texto')[:180]}...")
            if fb_res:
                if res_lines:
                    res_lines.append("")
                res_lines.append("INFORMACIÓN DE FACEBOOK:")
                for f in fb_res:
                    res_lines.append(f"• {f.get('fecha')}: {f.get('texto', '')[:180]}...")
            return "\n".join(res_lines)

        return ("No encontré información directa para esa consulta.\n\n"
                "Podés probar consultando: 'materias', 'docentes', 'novedades', 'sitio web', 'facebook', 'progreso' o 'actividades'.")

