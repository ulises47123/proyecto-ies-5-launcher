"""
ia/agent.py — Agente inteligente con Tool Calling, búsqueda en base de conocimiento, contexto de usuario y doble API con fallback.
"""
import re
from typing import Dict, Any, List, Optional
from ia.tools import AgentTools
from ia.user_context import UserContextManager
from ia.prompt_builder import PromptBuilder
from ia.fallback_manager import FallbackManager
from ia.knowledge_base import KnowledgeBaseManager
from config import cargar_cache, cargar_config, cargar_gemini_key, cargar_openai_key
import ia.agy_sidecar as agy_sidecar


class IntelligentAgent:
    """Agente central de IA con capacidades de Tool Calling, análisis local, AGY CLI y fallback a modelos externos."""

    def __init__(self, campus_session=None):
        self.campus = campus_session
        self.context_mgr = UserContextManager(campus_session)
        self.tools = AgentTools(campus_session, self.context_mgr)
        self.kb_mgr = KnowledgeBaseManager()
        self.fallback_mgr = FallbackManager(timeout=25)

    def tiene_api_activa(self) -> bool:
        """Verifica si AGY o alguna API externa (Gemini o OpenAI) está configurada y activa."""
        cfg = cargar_config()
        if cfg.get("usar_asistente_agy", False) and agy_sidecar.esta_instalado():
            return True
        g_ok = cfg.get("api_gemini_activa", True) and bool(cargar_gemini_key())
        o_ok = cfg.get("api_openai_activa", True) and bool(cargar_openai_key())
        return g_ok or o_ok

    def get_saludo_inicial(self) -> str:
        """Genera el saludo personalizado para el usuario."""
        nombre = self.context_mgr.get_user_name()
        return f"¡Hola, {nombre}! Soy tu Asistente Virtual. ¿Cómo puedo ayudarte hoy con tus materias o consultas académicas?"

    def procesar_consulta(self, pregunta: str) -> str:
        """
        Lógica del agente:
        1. Si el Asistente Avanzado AGY está activo, consulta directamente en modo low token.
        2. Si hay APIs externas activas (Gemini / OpenAI), delega al modelo con Tool Calling.
        3. Si el bot local está activo, resuelve con el motor local offline.
        """
        q = pregunta.strip()
        if not q:
            return "Por favor, escribe una pregunta o consulta."

        cfg = cargar_config()
        user_ctx = self.context_mgr.get_context()
        kb_docs = self.kb_mgr.listar_documentos()
        system_prompt = PromptBuilder.build_system_prompt(user_ctx, kb_docs)

        # 1. Modo Asistente Avanzado AGY CLI (si está activo)
        if cfg.get("usar_asistente_agy", False) and agy_sidecar.esta_instalado():
            ok, resp_agy = agy_sidecar.ejecutar_consulta(
                pregunta=q,
                contexto_sistema=system_prompt,
                effort="low"
            )
            if ok and resp_agy:
                return resp_agy

        # 2. Modo Agente Inteligente con IA Externa (Gemini / OpenAI) y Tool Calling
        g_ok = cfg.get("api_gemini_activa", True) and bool(cargar_gemini_key())
        o_ok = cfg.get("api_openai_activa", True) and bool(cargar_openai_key())
        if g_ok or o_ok:
            tools_schema = self.tools.obtener_definiciones_herramientas()
            resp, prov = self.fallback_mgr.responder_con_fallback(
                prompt=q,
                system_prompt=system_prompt,
                tools_declarations=tools_schema,
                tools_executor=self.tools
            )
            if resp:
                return resp

        # 3. Si el bot local fue desactivado en Ajustes y no hay respuesta externa
        if cfg.get("solo_ia_api", False) or not cfg.get("bot_local_activo", True):
            return "⚠️ El asistente local está desactivado y no hay conexión con servicios externos de IA en este momento."

        # 4. Fallback inmediato al motor local offline
        return self._procesar_consulta_local(q)

    def _procesar_consulta_local(self, q: str) -> str:
        """Motor de resolución local inteligente y offline sin requerir LLM externo."""
        q_lower = q.lower().strip()

        # 1. Herramienta: Fecha y hora actual
        if any(w in q_lower for w in ["qué día es hoy", "que dia es hoy", "qué fecha", "que fecha", "qué día estamos", "que dia estamos", "la fecha", "qué hora", "que hora"]):
            from datetime import datetime
            dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
            meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
            now = datetime.now()
            dia_sem = dias[now.weekday()]
            mes_nom = meses[now.month - 1]
            return f"Hoy es {dia_sem} {now.day} de {mes_nom} de {now.year}."

        # 2. Herramienta: Actividades y tareas pendientes
        if any(w in q_lower for w in ["debo alguna actividad", "debo actividad", "debo tareas", "actividad pendiente", "actividades pendientes", "tarea pendiente", "tareas pendientes", "tengo que entregar", "tengo entregas", "debo algo"]):
            res_act = self.tools.consultar_actividades_pendientes()
            if not res_act.get("tiene_pendientes"):
                return "¡Estás al día! No registras actividades o tareas pendientes de entrega en el campus actualmente."
            lineas = ["Tienes las siguientes actividades pendientes:"]
            for a in res_act.get("pendientes", []):
                lineas.append(f"• {a.get('materia')}: {a.get('titulo')} (Vence: {a.get('fecha', 'Sin fecha')})")
            return "\n".join(lineas)

        # 3. Herramienta: Envío de mensaje a chat o grupo
        es_lectura = any(w in q_lower for w in ["leer", "ver chat", "hay mensaje", "mensajes del chat", "mensajes en el chat", "que dijeron"])
        es_comando_envio = not es_lectura and (
            bool(re.search(r"\b(?:escribe|escribir|envia|enviar|manda|mandar|publica|publicar|pone|poner)\b", q_lower))
            or any(num in q_lower.split() for num in ["213", "999", "444"])
            or "grupo2" in q_lower
        )
        if es_comando_envio:
            mat = ""
            for palabra in ["redes", "practica", "práctica", "empresa", "datos", "programacion", "programación"]:
                if palabra in q_lower:
                    mat = palabra
                    break
            res_envio = self.tools.enviar_mensaje_chat_materia(materia=mat, mensaje=q)
            return f"📤 {res_envio.get('mensaje')}"

        # 4. Herramienta: Consultar / Leer mensajes del chat
        if any(w in q_lower for w in ["leer mensaje", "leer chat", "ver chat", "hay mensaje en el chat", "mensajes del chat", "mensajes en el chat", "chat de", "novedades del chat", "mensajes de", "mensajes recientes"]):
            mat = ""
            for palabra in ["redes", "practica", "práctica", "empresa", "datos", "programacion", "programación"]:
                if palabra in q_lower:
                    mat = palabra
                    break
            res_chat = self.tools.consultar_chat_materia(materia=mat)
            if res_chat.get("encontrado") and res_chat.get("mensajes"):
                lineas = [f"Mensajes recientes en el chat de {res_chat.get('materia')}:"]
                for m in res_chat["mensajes"]:
                    lineas.append(f"• [{m.get('fecha')}] {m.get('remitente')}: {m.get('texto')}")
                return "\n".join(lineas)
            return res_chat.get("mensaje") or "No hay mensajes recientes en el chat."

        # 5. Herramienta: Buscar personas (compañeros y docentes)
        if any(w in q_lower for w in ["quién es", "quien es", "conoces a", "conoce a", "contacto de", "datos de"]) and not any(w in q_lower for w in ["mi profesor", "profesor de", "docente de", "quién dicta"]):
            match = re.search(r"(?:quién es|quien es|conoces a|conoce a|contacto de|datos de)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+)", q, re.IGNORECASE)
            nom_busq = match.group(1).strip() if match else q
            res_p = self.tools.buscar_persona(nom_busq)
            if res_p.get("encontrado"):
                lineas = ["Información encontrada:"]
                for p in res_p.get("personas", []):
                    lineas.append(f"• {p.get('nombre')} ({p.get('rol')}) - {p.get('materia')} | Correo: {p.get('email', 'No especificado')}")
                return "\n".join(lineas)
            return res_p.get("mensaje")

        # 6. Herramienta: Listar compañeros de cursada
        if any(w in q_lower for w in ["mis compañeros", "mis companeros", "compañeros de", "alumnos de", "quiénes cursan", "quienes cursan"]):
            res_a = self.tools.listar_alumnos()
            if res_a.get("encontrado"):
                lineas = ["Compañeros encontrados:"]
                for a in res_a.get("alumnos", []):
                    lineas.append(f"• {a.get('nombre')} ({a.get('materia')})")
                return "\n".join(lineas)
            return res_a.get("mensaje")

        # 7. Herramienta: Datos personales / Nombre / Perfil
        if any(w in q_lower for w in ["quién soy", "quien soy", "cómo me llamo", "como me llamo", "mi nombre", "mi usuario", "mis datos", "mi dni", "mi perfil"]):
            ctx = self.context_mgr.get_context()
            nombre = ctx.get("nombre_completo", "Estudiante")
            dni = ctx.get("dni", "")
            carrera = ctx.get("carrera", "Tecnicatura Superior en Soporte de Infraestructura de TI")
            institucion = ctx.get("institucion", "IES N°5 'José Eugenio Tello'")
            dni_str = f" (DNI: {dni})" if dni else ""
            return f"Te llamas {nombre}{dni_str}, estudiante registrado en la carrera de {carrera} en el {institucion}."

        # 8. Herramienta: Fechas de parciales y evaluaciones
        if any(w in q_lower for w in ["cuándo es el parcial", "cuando es el parcial", "cuándo son los parciales", "cuando son los parciales", "fechas de parciales", "fecha de examen", "parcial de", "parciales de", "evaluación de", "evaluacion de"]):
            materia_detectada = ""
            for palabra in ["redes", "programación", "programacion", "base de datos", "sistemas", "inglés", "ingles", "matemática", "matematica", "práctica", "practica"]:
                if palabra in q_lower:
                    materia_detectada = palabra
                    break

            res_parciales = self.tools.obtener_fechas_parciales(materia_detectada)
            fechas = res_parciales.get("fechas_encontradas", [])
            if fechas:
                lines = [f"FECHAS Y EVALUACIONES ({res_parciales.get('materia_consultada').upper()}):"]
                for f in fechas:
                    doc = f.get("documento")
                    mat = f.get("materia")
                    det = f.get("detalle")
                    lines.append(f"• [{mat}] ({doc}):\n  {det}")
                return "\n\n".join(lines)

            busq = self.tools.buscar_en_indice(materia_detectada or q)
            if busq.get("total_encontrados", 0) > 0:
                doc = busq["resultados"][0]
                doc_full = self.tools.obtener_contenido_completo(doc["fuente"])
                return f"Según el documento '{doc['titulo']}':\n\n{doc_full.get('contenido', '')[:500]}..."

        # 9. Herramienta: Docente de una materia específica
        if any(w in q_lower for w in ["quién dicta", "quien dicta", "profesor de", "profesora de", "docente de", "quién da", "quien da", "profesores", "docentes"]):
            for palabra in ["redes", "programación", "programacion", "base de datos", "sistemas", "inglés", "ingles", "matemática", "matematica", "práctica", "practica", "algoritmos", "arquitectura"]:
                if palabra in q_lower:
                    res_doc = self.tools.obtener_docente_materia(palabra)
                    if res_doc.get("encontrado"):
                        return f"DOCENTE A CARGO:\n• Materia: {res_doc.get('materia')}\n• Docente: {res_doc.get('docente')}"

        # 10. Herramienta: Correo del docente
        if any(w in q_lower for w in ["correo del docente", "correo de", "email del docente", "email de", "contacto del docente", "contacto de"]):
            for palabra in ["redes", "programación", "programacion", "base de datos", "sistemas", "inglés", "ingles", "matemática", "matematica", "práctica", "practica"]:
                if palabra in q_lower:
                    res_mail = self.tools.obtener_correo_docente(palabra)
                    if res_mail.get("encontrado"):
                        return f"INFORMACIÓN DE CONTACTO:\n• Docente: {res_mail.get('docente')}\n• Materia: {res_mail.get('materia')}\n• Correo / Canal: {res_mail.get('email')}"

        # 11. Herramienta: Última actividad de materia específica
        if any(w in q_lower for w in ["última actividad", "ultima actividad", "última tarea", "ultima tarea", "reciente de"]):
            for palabra in ["redes", "programación", "programacion", "base de datos", "sistemas", "inglés", "ingles", "matemática", "matematica", "práctica", "practica"]:
                if palabra in q_lower:
                    res_act = self.tools.obtener_ultima_actividad(palabra)
                    if res_act.get("encontrado"):
                        a = res_act.get("actividad", {})
                        return f"ÚLTIMA ACTIVIDAD ({res_act.get('materia')}):\n• Título: {a.get('titulo')}\n• Unidad: {a.get('unidad')}\n• Estado: {a.get('estado')}\n• Fecha: {a.get('fecha') or 'Sin fecha'}"

        # 12. Herramienta: Extraer consigna de actividad
        if any(w in q_lower for w in ["extrae la consigna", "extraer consigna", "consigna de", "consigna de la actividad", "qué pide la actividad", "que pide la actividad"]):
            match = re.search(r'(?:consigna de(?: la actividad)?|actividad)\s+([^\?\.\n]+)', q, re.IGNORECASE)
            act_nom = match.group(1).strip() if match else q
            res_con = self.tools.obtener_consigna_actividad(act_nom)
            if res_con.get("encontrado"):
                return f"CONSIGNA DE LA ACTIVIDAD '{res_con.get('actividad')}' ({res_con.get('materia')}):\n\n{res_con.get('consigna')}"

        # 8. Herramienta: Búsqueda en Base de Conocimiento (Planes, Programas, Unidades)
        busqueda_kb = self.tools.buscar_en_indice(q)
        if busqueda_kb.get("total_encontrados", 0) > 0:
            mejor_doc = busqueda_kb["resultados"][0]
            if mejor_doc.get("score", 0) >= 4 or any(w in q_lower for w in ["plan", "planificación", "planificacion", "programa", "índice", "indice", "unidad", "contenidos"]):
                doc_full = self.tools.obtener_contenido_completo(mejor_doc["fuente"])
                indice_str = ", ".join(mejor_doc.get("indice", [])[:5])
                return (
                    f"INFORMACIÓN ENCONTRADA EN BASE DE CONOCIMIENTO:\n"
                    f"📄 Documento: {mejor_doc.get('titulo')} [{mejor_doc.get('materia')}]\n"
                    f"📌 Secciones: {indice_str}\n\n"
                    f"{doc_full.get('contenido', '')[:600]}..."
                )

        # 9. Herramienta: Calificaciones y notas
        if any(w in q_lower for w in ["calificación", "calificacion", "calificaciones", "mis notas", "qué nota", "que nota", "promedio", "aprobé"]):
            res_califs = self.tools.buscar_calificaciones()
            califs = res_califs.get("calificaciones", {})
            if isinstance(califs, dict) and califs:
                lines = ["CALIFICACIONES REGISTRADAS:"]
                for mat, notas in califs.items():
                    if isinstance(notas, list):
                        n_str = ", ".join([f"{n.get('nombre', 'Nota')}: {n.get('valor', '-')}" for n in notas])
                        lines.append(f"• {mat}: {n_str}")
                    else:
                        lines.append(f"• {mat}: {notas}")
                return "\n".join(lines)
            return "No se encontraron calificaciones registradas en la sesión actual."

        # 10. Herramienta: Materias cursadas y docentes dinámicos (Prueba 1)
        if any(w in q_lower for w in ["mis materias", "qué materias", "que materias", "materias tengo", "asignaturas", "mis cursos", "quiénes las dictan", "quienes las dictan"]):
            ctx = self.context_mgr.get_context()
            materias = ctx.get("materias", [])
            if materias:
                lines = ["TUS MATERIAS Y DOCENTES A CARGO (Ciclo actual):"]
                for m in materias:
                    docs = ", ".join(m.get("docentes", [])) or "Docente a confirmar"
                    lines.append(f"• {m.get('nombre')} — {m.get('avance', 0)}% avance\n  Docente(s): {docs}")
                return "\n\n".join(lines)

        # 11. Herramienta: Sitio Institucional
        if any(w in q_lower for w in ["sitio", "página", "web", "institucional", "beca", "becas", "resolución", "resolucion", "comunicado", "mesa"]):
            res_sitio = self.tools.buscar_en_sitio_institucional(q)
            items = res_sitio.get("resultados", [])
            if items:
                lines = ["COMUNICADOS Y RESOLUCIONES DEL SITIO WEB:"]
                for it in items[:3]:
                    lines.append(f"• {it.get('titulo')}\n  Enlace: {it.get('url')}\n  {it.get('texto', '')[:180]}...")
                return "\n\n".join(lines)

        # 12. Mensaje de ayuda / orientativo local si no hubo coincidencia
        return (
            "No encontré información directa en tus materias o documentos cargados.\n\n"
            "Podés preguntarme sobre:\n"
            "• Materias y docentes a cargo (ej. '¿Cuáles son mis materias y quiénes las dictan?').\n"
            "• Fechas de parciales (ej. '¿Cuándo son los parciales de Redes?').\n"
            "• Última actividad o consigna (ej. '¿Cuál fue la última actividad de Redes?').\n"
            "• Correo de un docente (ej. '¿Cuál es el correo del docente que dicta Redes?').\n"
            "• Enviar mensaje a un grupo (ej. 'grupo2 reunión hoy').\n"
            "• Calificaciones y progreso académico."
        )
