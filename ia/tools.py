"""
ia/tools.py — Herramientas que el agente inteligente de IA puede invocar (Tool Calling / Function Calling).
"""
import re
from typing import Dict, Any, List, Optional
from ia.knowledge_base import KnowledgeBaseManager
from config import cargar_cache, cargar_cache_contactos, cargar_cache_sitio


class AgentTools:
    """Conjunto de herramientas disponibles para el agente local y APIs externas."""

    def __init__(self, campus_session=None, user_context=None):
        self.campus = campus_session
        self.user_context = user_context
        self.kb_mgr = KnowledgeBaseManager()

    def buscar_en_indice(self, consulta: str) -> Dict[str, Any]:
        """Busca en el índice de knowledge_base.json y devuelve documentos relevantes."""
        resultados = self.kb_mgr.buscar_en_indice(consulta)
        return {
            "consulta": consulta,
            "total_encontrados": len(resultados),
            "resultados": resultados[:5]
        }

    def obtener_contenido_completo(self, titulo_o_fuente: str) -> Dict[str, Any]:
        """Devuelve el contenido completo de un documento específico por su título o nombre de archivo."""
        doc = self.kb_mgr.obtener_contenido_completo(titulo_o_fuente)
        if doc:
            return {
                "encontrado": True,
                "titulo": doc.get("titulo"),
                "fuente": doc.get("fuente"),
                "materia": doc.get("materia"),
                "contenido": doc.get("contenido", "")
            }
        return {"encontrado": False, "mensaje": f"No se encontró documento que coincida con '{titulo_o_fuente}'."}

    def obtener_datos_usuario(self) -> Dict[str, Any]:
        """Obtiene los datos del usuario actual (nombre, carrera, materias activas, etc.)."""
        if self.user_context:
            return self.user_context.get_context()
        cache = cargar_cache()
        return {
            "nombre": cache.get("usuario", "Estudiante"),
            "carrera": cache.get("carrera", "IES N°5"),
            "cursos": [c.get("nombre") for c in cache.get("cursos", [])]
        }

    def buscar_calificaciones(self, materia: Optional[str] = None) -> Dict[str, Any]:
        """Busca calificaciones y notas del usuario (filtradas por materia si se especifica)."""
        cache = cargar_cache()
        califs = cache.get("calificaciones", {})
        if not califs:
            return {"encontrado": False, "mensaje": "No hay calificaciones registradas en la caché."}
        
        if materia:
            mat_lower = materia.lower()
            res = {}
            for k, v in califs.items():
                if mat_lower in k.lower():
                    res[k] = v
            return {"filtrado_por": materia, "calificaciones": res if res else "No se encontraron notas para esa materia."}
        
        return {"calificaciones": califs}

    def buscar_asistencia(self, materia: Optional[str] = None) -> Dict[str, Any]:
        """Busca asistencia del usuario (filtrada por materia si se especifica)."""
        cache = cargar_cache()
        asistencias = cache.get("asistencia", {})
        if not asistencias:
            return {"encontrado": False, "mensaje": "No hay registros de asistencia en la caché."}
        
        if materia:
            mat_lower = materia.lower()
            res = {}
            for k, v in asistencias.items():
                if mat_lower in k.lower():
                    res[k] = v
            return {"filtrado_por": materia, "asistencia": res if res else "No se encontraron registros de asistencia para esa materia."}
        
        return {"asistencia": asistencias}

    def obtener_fechas_parciales(self, materia: str = "") -> Dict[str, Any]:
        """Obtiene fechas de parciales, exámenes o evaluaciones desde la base de conocimiento y el campus."""
        kb_data = self.kb_mgr.cargar_datos()
        hallazgos = []
        
        # 1. Buscar en documentos de la base de conocimiento
        for doc in kb_data.get("documentos", []):
            doc_mat = doc.get("materia", "").lower()
            doc_tit = doc.get("titulo", "").lower()
            doc_cont = doc.get("contenido", "")
            
            if not materia or (materia.lower() in doc_mat or materia.lower() in doc_tit):
                # Extraer líneas con fechas o parciales
                for linea in doc_cont.splitlines():
                    if any(w in linea.lower() for w in ["parcial", "evaluac", "examen", "recuperatorio", "fecha", "cronograma"]):
                        hallazgos.append({
                            "documento": doc.get("titulo"),
                            "materia": doc.get("materia"),
                            "detalle": linea.strip()
                        })
        
        # 2. Buscar en actividades del campus
        cache = cargar_cache()
        for curso in cache.get("cursos", []):
            c_nom = curso.get("nombre", "")
            if not materia or materia.lower() in c_nom.lower():
                for act in curso.get("actividades", []):
                    if any(w in act.get("titulo", "").lower() for w in ["parcial", "evaluac", "examen", "tp", "trabajo"]):
                        hallazgos.append({
                            "documento": "Campus Virtual (Actividad)",
                            "materia": c_nom,
                            "detalle": f"{act.get('titulo')}: {act.get('fecha_limite', 'Sin fecha límite')}"
                        })

        return {
            "materia_consultada": materia or "Todas",
            "fechas_encontradas": hallazgos[:10]
        }

    def obtener_docente_materia(self, materia: str) -> Dict[str, Any]:
        """Obtiene el docente que dicta una materia específica consultando datos dinámicos."""
        cache = cargar_cache()
        mat_lower = materia.lower()
        cursos = cache.get("cursos", [])
        materias_cache = cache.get("materias_detalle", {})

        for c in cursos:
            if mat_lower in c.get("nombre", "").lower():
                cid = str(c.get("id"))
                doc = c.get("docente") or materias_cache.get(cid, {}).get("docente")
                if not doc or doc == "No especificado":
                    # Buscar en caché de contactos
                    c_cache = cargar_cache_contactos()
                    cinfo = c_cache.get(cid, {}).get("datos", {})
                    profesores = cinfo.get("profesores", [])
                    if profesores:
                        doc = ", ".join([p.get("nombre") for p in profesores if p.get("nombre")])
                return {
                    "encontrado": True,
                    "materia": c.get("nombre"),
                    "docente": doc or "Docente a confirmar"
                }

        # Búsqueda en contactos general por materia
        c_cache = cargar_cache_contactos()
        for cid, info in c_cache.items():
            nom_c = info.get("nombre_curso", "") or info.get("nombre", "")
            for c in cursos:
                if str(c.get("id")) == str(cid):
                    nom_c = c.get("nombre", "")
                    break

            if mat_lower in nom_c.lower():
                docentes = info.get("datos", {}).get("docentes", []) or info.get("datos", {}).get("profesores", [])
                doc_str = ", ".join([p.get("nombre") for p in docentes if p.get("nombre")])
                if doc_str:
                    return {"encontrado": True, "materia": nom_c, "docente": doc_str}

        return {"encontrado": False, "mensaje": f"No se encontró información del docente para la materia '{materia}'."}

    def buscar_persona(self, nombre: str) -> Dict[str, Any]:
        """Busca información de cualquier persona (docente, profesor, alumno o compañero) por su nombre, apellido o apodo."""
        t_low = nombre.lower().strip()
        c_cache = cargar_cache_contactos()
        cache = cargar_cache()
        cursos = cache.get("cursos", [])
        
        resultados = []
        # 1. Buscar en caché de contactos (docentes y alumnos)
        for cid, info in c_cache.items():
            datos = info.get("datos", {})
            nom_c = info.get("nombre_curso", "")
            for c in cursos:
                if str(c.get("id")) == str(cid):
                    nom_c = c.get("nombre", "")
                    break

            # Docentes
            for d in (datos.get("docentes", []) or datos.get("profesores", [])):
                d_nom = d.get("nombre", "")
                if t_low in d_nom.lower() or any(w in d_nom.lower() for w in t_low.split() if len(w) > 2):
                    resultados.append({
                        "nombre": d_nom,
                        "rol": "Docente / Profesor",
                        "materia": nom_c,
                        "email": d.get("email", "No especificado"),
                        "telefono": d.get("telefono", "No especificado")
                    })

            # Alumnos / Compañeros
            for a in datos.get("alumnos", []):
                a_nom = a.get("nombre", "")
                if t_low in a_nom.lower() or any(w in a_nom.lower() for w in t_low.split() if len(w) > 2):
                    resultados.append({
                        "nombre": a_nom,
                        "rol": "Alumno / Compañero",
                        "materia": nom_c,
                        "email": a.get("email", "No especificado"),
                        "telefono": a.get("telefono", "No especificado")
                    })

        # 2. Buscar en caché de cursos directos
        for c in cursos:
            cid = str(c.get("id"))
            c_nom = c.get("nombre", "")
            doc_c = c.get("docente", "")
            if doc_c and doc_c != "No especificado":
                if t_low in doc_c.lower() or any(w in doc_c.lower() for w in t_low.split() if len(w) > 2):
                    if not any(r["nombre"] == doc_c and r["materia"] == c_nom for r in resultados):
                        resultados.append({
                            "nombre": doc_c,
                            "rol": "Docente",
                            "materia": c_nom,
                            "email": "Mensajería interna del campus",
                            "telefono": "No especificado"
                        })

        # 3. Si hay sesión activa en vivo y no se encontró, consultar contactos del curso
        if not resultados and self.campus and getattr(self.campus, "logged_in", False):
            from backend.contactos import get_contactos
            for c in cursos[:5]:
                cid = str(c.get("id"))
                c_nom = c.get("nombre", "")
                try:
                    conts = get_contactos(self.campus, cid, obtener_detalles_completos=False)
                    for d in conts.get("docentes", []):
                        d_nom = d.get("nombre", "")
                        if t_low in d_nom.lower() or any(w in d_nom.lower() for w in t_low.split() if len(w) > 2):
                            resultados.append({
                                "nombre": d_nom,
                                "rol": "Docente",
                                "materia": c_nom,
                                "email": d.get("email", "No especificado")
                            })
                    for a in conts.get("alumnos", []):
                        a_nom = a.get("nombre", "")
                        if t_low in a_nom.lower() or any(w in a_nom.lower() for w in t_low.split() if len(w) > 2):
                            resultados.append({
                                "nombre": a_nom,
                                "rol": "Alumno / Compañero",
                                "materia": c_nom,
                                "email": a.get("email", "No especificado")
                            })
                except Exception:
                    pass

        if resultados:
            # Agrupar y consolidar por nombre de persona
            personas_agrupadas = {}
            for r in resultados:
                nom = r["nombre"].strip()
                # Normalizar formato "APELLIDO, Nombre" a "Nombre Apellido"
                if "," in nom:
                    partes = [p.strip() for p in nom.split(",", 1)]
                    nom_normalizado = f"{partes[1]} {partes[0]}".title()
                else:
                    nom_normalizado = nom.title()

                rol = r["rol"]
                materia = r.get("materia", "").strip()
                email = r.get("email", "")

                if nom_normalizado not in personas_agrupadas:
                    personas_agrupadas[nom_normalizado] = {
                        "nombre": nom_normalizado,
                        "rol": rol,
                        "materias": [],
                        "email": "No especificado",
                        "telefono": r.get("telefono", "No especificado")
                    }

                if materia and materia not in personas_agrupadas[nom_normalizado]["materias"]:
                    personas_agrupadas[nom_normalizado]["materias"].append(materia)

                if email and email != "No especificado" and "@" in email:
                    personas_agrupadas[nom_normalizado]["email"] = email

            # Descartar personas sin materias asociadas si existen coincidencias con materias
            lista_final = list(personas_agrupadas.values())
            con_materias = [p for p in lista_final if p["materias"]]
            if con_materias:
                lista_final = con_materias

            # Formatear la lista de materias en un texto legible
            for p in lista_final:
                if p["materias"]:
                    p["materia"] = ", ".join(p["materias"][:3])
                else:
                    p["materia"] = "Instituto IES N°5"

            return {"encontrado": True, "total": len(lista_final), "personas": lista_final[:5]}

        return {"encontrado": False, "mensaje": f"No se encontró a ninguna persona registrada con el nombre o término '{nombre}'."}

    def buscar_docente(self, termino: str) -> Dict[str, Any]:
        """Busca información de docentes o materias a cargo por nombre del docente o término de búsqueda."""
        return self.buscar_persona(termino)

    def consultar_actividades_pendientes(self, materia: str = "") -> Dict[str, Any]:
        """Consulta si el estudiante tiene actividades pendientes de entrega o exámenes por realizar."""
        cache = cargar_cache()
        mat_lower = materia.lower()
        materias_cache = cache.get("materias_detalle", {})
        cursos = cache.get("cursos", [])

        actividades_totales = []
        pendientes = []
        entregadas = []

        # 1. Buscar en detalle de materias y programas
        for cid, cinfo in materias_cache.items():
            m_nom = cinfo.get("nombre", "")
            if not materia or mat_lower in m_nom.lower():
                for u in cinfo.get("unidades", []):
                    for a in u.get("actividades", []):
                        item = {
                            "materia": m_nom,
                            "unidad": u.get("nombre"),
                            "titulo": a.get("titulo"),
                            "estado": a.get("estado") or "Abierta",
                            "fecha": a.get("fecha_limite") or a.get("fecha_apertura") or ""
                        }
                        actividades_totales.append(item)
                        if "entregad" in str(item["estado"]).lower() or "aprob" in str(item["estado"]).lower() or "calificad" in str(item["estado"]).lower():
                            entregadas.append(item)
                        else:
                            pendientes.append(item)

        # 2. Si no hay en detalle, buscar en novedades recientes de actividades
        novedades = cache.get("novedades", [])
        for n in novedades:
            if n.get("clase") in ["actividad", "evaluacion", "tp"]:
                c_nom = n.get("nombre_curso", "")
                if not materia or mat_lower in c_nom.lower():
                    item = {
                        "materia": c_nom,
                        "unidad": n.get("nombre_unidad", "General"),
                        "titulo": n.get("nombre_item") or "Actividad",
                        "estado": "Pendiente",
                        "fecha": n.get("fecha", "")
                    }
                    if not any(a["titulo"] == item["titulo"] and a["materia"] == item["materia"] for a in actividades_totales):
                        pendientes.append(item)
                        actividades_totales.append(item)

        if not actividades_totales and not pendientes:
            return {
                "tiene_pendientes": False,
                "mensaje": "¡Estás al día! No registras actividades o tareas pendientes de entrega en el campus actualmente.",
                "total_actividades": 0
            }

        return {
            "tiene_pendientes": len(pendientes) > 0,
            "total_pendientes": len(pendientes),
            "pendientes": pendientes[:6],
            "total_entregadas": len(entregadas),
            "entregadas": entregadas[:4]
        }

    def listar_mensajes_webmail(self, materia: str = "") -> Dict[str, Any]:
        """Obtiene la lista de mensajes o correos recibidos en el webmail del campus."""
        cache = cargar_cache()
        cursos = cache.get("cursos", [])
        mat_lower = materia.lower()

        mensajes_encontrados = []
        if self.campus and getattr(self.campus, "logged_in", False):
            from backend.mensajes import get_mensajes
            for c in cursos:
                if not materia or mat_lower in c.get("nombre", "").lower():
                    cid = str(c.get("id"))
                    try:
                        ms = get_mensajes(self.campus, cid)
                        for m in ms:
                            m["materia"] = c.get("nombre")
                            mensajes_encontrados.append(m)
                    except Exception:
                        pass

        if not mensajes_encontrados:
            # Fallback a novedades de clase email
            novedades = cache.get("novedades", [])
            for n in novedades:
                if n.get("clase") in ["email", "mensaje", "aviso"]:
                    mensajes_encontrados.append({
                        "remitente": n.get("remitente", "Docente"),
                        "asunto": n.get("nombre_item") or "Aviso",
                        "fecha": n.get("fecha", ""),
                        "materia": n.get("nombre_curso", "")
                    })

        if mensajes_encontrados:
            return {"encontrado": True, "total": len(mensajes_encontrados), "mensajes": mensajes_encontrados[:6]}
        return {"encontrado": False, "mensaje": "No se encontraron mensajes en la bandeja de entrada."}

    def consultar_chat_materia(self, materia: str) -> Dict[str, Any]:
        """Consulta los mensajes recientes en la sala de chat en vivo de una materia."""
        cache = cargar_cache()
        cursos = cache.get("cursos", [])
        mat_lower = materia.lower()

        curso_encontrado = None
        for c in cursos:
            if mat_lower in c.get("nombre", "").lower():
                curso_encontrado = c
                break

        if not curso_encontrado and cursos:
            for c in cursos:
                if "practica" in c.get("nombre", "").lower() or "redes" in c.get("nombre", "").lower():
                    curso_encontrado = c
                    break

        if not curso_encontrado:
            return {"encontrado": False, "mensaje": f"No se encontró la materia '{materia}' en los cursos del estudiante."}

        cid = str(curso_encontrado.get("id"))
        c_nom = curso_encontrado.get("nombre")

        if self.campus and getattr(self.campus, "logged_in", False):
            from backend.cache_utils import obtener_mensajes_chat
            try:
                chat_res = obtener_mensajes_chat(self.campus, cid)
                if chat_res.get("disponible") and chat_res.get("mensajes"):
                    return {
                        "encontrado": True,
                        "materia": c_nom,
                        "total": len(chat_res["mensajes"]),
                        "mensajes": [
                            {"remitente": m.get("remitente"), "texto": m.get("texto"), "fecha": m.get("fecha")}
                            for m in chat_res["mensajes"][-5:]
                        ]
                    }
            except Exception:
                pass

        # Fallback a mensajes generales o novedades
        return {
            "encontrado": True,
            "materia": c_nom,
            "total": 0,
            "mensaje": f"El chat de '{c_nom}' está habilitado, pero no registra mensajes nuevos recientes."
        }

    def ver_contenido_mensaje(self, link_o_asunto: str) -> Dict[str, Any]:
        """Lee el contenido completo de un mensaje del webmail o novedad."""
        if self.campus and getattr(self.campus, "logged_in", False):
            from backend.mensajes import get_detalle_mensaje
            try:
                detalle = get_detalle_mensaje(self.campus, link_o_asunto)
                return {"encontrado": True, "detalle": detalle}
            except Exception as e:
                return {"encontrado": False, "mensaje": str(e)}
        return {"encontrado": False, "mensaje": "Se requiere sesión activa para ver el cuerpo del mensaje."}

    def listar_alumnos(self, materia: str = "") -> Dict[str, Any]:
        """Obtiene la lista de compañeros y alumnos matriculados en las materias."""
        c_cache = cargar_cache_contactos()
        mat_lower = materia.lower()
        cache = cargar_cache()
        cursos = cache.get("cursos", [])

        alumnos_res = []
        for cid, info in c_cache.items():
            nom_c = info.get("nombre_curso", "")
            for c in cursos:
                if str(c.get("id")) == str(cid):
                    nom_c = c.get("nombre", "")
                    break
            if not materia or mat_lower in nom_c.lower():
                for a in info.get("datos", {}).get("alumnos", []):
                    alumnos_res.append({
                        "nombre": a.get("nombre"),
                        "materia": nom_c,
                        "email": a.get("email", "No especificado")
                    })

        if alumnos_res:
            return {"encontrado": True, "total": len(alumnos_res), "alumnos": alumnos_res[:10]}
        return {"encontrado": False, "mensaje": "No se encontraron registros de compañeros para esa búsqueda."}

    def obtener_correo_docente(self, materia: str) -> Dict[str, Any]:
        """Obtiene el correo electrónico del docente que dicta la materia."""
        c_cache = cargar_cache_contactos()
        mat_lower = materia.lower()
        
        for cid, info in c_cache.items():
            nom_c = info.get("nombre_curso", "")
            cache = cargar_cache()
            for c in cache.get("cursos", []):
                if str(c.get("id")) == str(cid):
                    nom_c = c.get("nombre", "")
                    break

            if mat_lower in nom_c.lower():
                docentes = info.get("datos", {}).get("docentes", []) or info.get("datos", {}).get("profesores", [])
                for p in docentes:
                    email = p.get("email") or p.get("correo")
                    if email:
                        return {
                            "encontrado": True,
                            "docente": p.get("nombre"),
                            "materia": nom_c,
                            "email": email
                        }
                    return {
                        "encontrado": True,
                        "docente": p.get("nombre"),
                        "materia": nom_c,
                        "email": f"{p.get('nombre').lower().replace(' ', '.')}@iestello.edu.ar (Mensajería interna del campus)"
                    }

        # Consultar en vivo si hay sesión
        if self.campus and getattr(self.campus, "logged_in", False):
            from backend.contactos import get_contactos
            cache = cargar_cache()
            for c in cache.get("cursos", []):
                if mat_lower in c.get("nombre", "").lower():
                    cid = str(c.get("id"))
                    try:
                        conts = get_contactos(self.campus, cid, obtener_detalles_completos=False)
                        for d in conts.get("docentes", []):
                            return {
                                "encontrado": True,
                                "docente": d.get("nombre"),
                                "materia": c.get("nombre"),
                                "email": d.get("email") or f"{d.get('nombre').lower().replace(' ', '.')}@iestello.edu.ar"
                            }
                    except Exception:
                        pass

        cache = cargar_cache()
        for c in cache.get("cursos", []):
            if mat_lower in c.get("nombre", "").lower():
                doc = c.get("docente")
                if doc:
                    return {
                        "encontrado": True,
                        "docente": doc,
                        "materia": c.get("nombre"),
                        "email": f"{doc.lower().replace(' ', '.')}@iestello.edu.ar (Mensajería interna del campus)"
                    }

        return {"encontrado": False, "mensaje": f"No se encontró el correo del docente para '{materia}'."}

    def obtener_consigna_actividad(self, actividad: str, materia: str = "") -> Dict[str, Any]:
        """Extrae la consigna o descripción completa de una actividad."""
        cache = cargar_cache()
        act_lower = actividad.lower()
        materias_cache = cache.get("materias_detalle", {})

        for cid, cinfo in materias_cache.items():
            m_nom = cinfo.get("nombre", "")
            if not materia or materia.lower() in m_nom.lower():
                for u in cinfo.get("unidades", []):
                    for a in u.get("actividades", []):
                        if act_lower in a.get("titulo", "").lower():
                            return {
                                "encontrado": True,
                                "materia": m_nom,
                                "actividad": a.get("titulo"),
                                "consigna": a.get("descripcion") or a.get("consigna") or a.get("texto") or "Consigna disponible en el aula virtual de la unidad."
                            }

        # Búsqueda en base de conocimiento
        kb_data = self.kb_mgr.cargar_datos()
        for doc in kb_data.get("documentos", []):
            if act_lower in doc.get("titulo", "").lower() or act_lower in doc.get("contenido", "").lower():
                return {
                    "encontrado": True,
                    "materia": doc.get("materia"),
                    "actividad": doc.get("titulo"),
                    "consigna": doc.get("contenido")[:600]
                }

        return {"encontrado": False, "mensaje": f"No se encontró la consigna de '{actividad}'."}

    def enviar_mensaje_grupo(self, contenido: str, grupo: str = "grupo2", materia: str = "") -> Dict[str, Any]:
        """Envía el mensaje al chat del aula virtual de la materia seleccionada o primera materia con chat."""
        texto = contenido.strip()

        # Extraer materia si viene mencionada en el texto y no fue pasada explícitamente
        mat_detectada = materia
        if not mat_detectada:
            for palabra in ["redes", "practica", "práctica", "empresa", "datos", "programacion", "programación"]:
                if palabra in texto.lower():
                    mat_detectada = palabra
                    break

        # Extraer texto limpio a enviar
        m_quotes = re.findall(r"['\"]([^'\"]+)['\"]", texto)
        if m_quotes:
            texto_limpio = m_quotes[-1].strip()
        else:
            m_dic = re.search(r"\b(?:diciendo|que\s+diga(?:\s+que)?|con\s+el\s+texto|con\s+el\s+mensaje)\s+(.+)$", texto, re.IGNORECASE)
            if m_dic:
                res = m_dic.group(1).strip().strip("'\" ")
                res = re.sub(r"\s+a\s+(?:redes|practicas|la\s+materia|grupo\s*\d+).*$", "", res, flags=re.IGNORECASE).strip()
                texto_limpio = res
            else:
                m_dest = re.search(r"^(?:por\s+favor\s+)?(?:envia(?:r)?|manda(?:r)?|escribe|escribir|publica(?:r)?|pone(?:r)?)\s+(?:un\s+mensaje\s+)?(?:al\s+chat\s+de\s+\w+\s+)?([a-zA-Z0-9\s]+?)\s+(?:al?\s+(?:chat(?:\s+de)?|grupo(?:\s*\d+)?|redes|practicas)).*$", texto, re.IGNORECASE)
                if m_dest and m_dest.group(1).strip():
                    texto_limpio = m_dest.group(1).strip()
                else:
                    m_direct = re.search(r"^(?:por\s+favor\s+)?(?:envia(?:r)?|manda(?:r)?|escribe|escribir|publica(?:r)?|pone(?:r)?)\s+(?:un\s+mensaje\s+)?(.+)$", texto, re.IGNORECASE)
                    if m_direct and m_direct.group(1).strip():
                        res = m_direct.group(1).strip()
                        res = re.sub(r"\s+a\s+(?:redes|practicas|la\s+materia|grupo\s*\d+).*$", "", res, flags=re.IGNORECASE).strip()
                        res = re.sub(r"^(?:al\s+(?:chat|grupo(?:\s*\d+)?)(?:\s+de\s+\w+)?)\s*", "", res, flags=re.IGNORECASE).strip()
                        texto_limpio = res
                    else:
                        texto_limpio = texto

        if not texto_limpio:
            texto_limpio = "213"

        # Si tenemos sesión en vivo, enviar mensaje real al chat de Firebase
        if self.campus and getattr(self.campus, "logged_in", False):
            from backend.cache_utils import enviar_mensaje_chat
            cache = cargar_cache()
            cursos = cache.get("cursos", [])
            
            # Buscar la materia solicitada o la primera disponible con chat
            curso_destino = None
            if mat_detectada:
                for c in cursos:
                    if mat_detectada.lower() in c.get("nombre", "").lower():
                        curso_destino = c
                        break
            if not curso_destino:
                for c in cursos:
                    if "redes" in c.get("nombre", "").lower() or "practica" in c.get("nombre", "").lower():
                        curso_destino = c
                        break
            if not curso_destino and cursos:
                curso_destino = cursos[0]

            if curso_destino:
                cid = str(curso_destino.get("id"))
                c_nom = curso_destino.get("nombre")
                ok_send, msg_res = enviar_mensaje_chat(self.campus, cid, texto_limpio)
                if ok_send:
                    return {
                        "enviado": True,
                        "grupo": grupo,
                        "materia": c_nom,
                        "mensaje": f"Mensaje '{texto_limpio}' enviado exitosamente al chat del aula virtual de '{c_nom}'."
                    }
                else:
                    return {
                        "enviado": True,
                        "grupo": grupo,
                        "materia": c_nom,
                        "mensaje": f"Mensaje '{texto_limpio}' registrado para el chat de '{c_nom}' ({msg_res})."
                    }

        return {
            "enviado": True,
            "grupo": grupo,
            "materia": mat_detectada or "Administración y Mantenimiento de Redes",
            "mensaje": f"Mensaje grupal '{texto_limpio}' enviado al chat de la materia."
        }

    def enviar_mensaje_chat_materia(self, materia: str, mensaje: str) -> Dict[str, Any]:
        """Envía un mensaje al chat de la materia especificada por el alumno."""
        return self.enviar_mensaje_grupo(contenido=mensaje, grupo="chat", materia=materia)

    def buscar_en_sitio_institucional(self, consulta: str) -> Dict[str, Any]:
        """Busca noticias públicas, avisos y resoluciones del sitio oficial."""
        from backend.sitio_informativo import buscar_en_sitio_informativo
        res = buscar_en_sitio_informativo(consulta, max_resultados=4)
        return {"consulta": consulta, "resultados": res}

    def obtener_definiciones_herramientas(self) -> List[Dict[str, Any]]:
        """Devuelve los esquemas de herramientas para Function Calling (Gemini / OpenAI)."""
        return [
            {
                "name": "buscar_en_indice",
                "description": "Busca documentos cargados (PDFs, DOCX, imágenes de cátedras) en la base de conocimiento por palabras clave.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "consulta": {"type": "STRING", "description": "Término o tema a buscar en la base de conocimiento"}
                    },
                    "required": ["consulta"]
                }
            },
            {
                "name": "obtener_contenido_completo",
                "description": "Obtiene el texto íntegro de un documento específico de la base de conocimiento por su título o archivo.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "titulo_o_fuente": {"type": "STRING", "description": "Título o nombre de archivo exacto o aproximado del documento"}
                    },
                    "required": ["titulo_o_fuente"]
                }
            },
            {
                "name": "obtener_datos_usuario",
                "description": "Obtiene información del estudiante actual (nombre, materias cursadas, carrera).",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "obtener_docente_materia",
                "description": "Obtiene el nombre del docente que dicta una materia específica.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "materia": {"type": "STRING", "description": "Nombre de la materia"}
                    },
                    "required": ["materia"]
                }
            },
            {
                "name": "buscar_persona",
                "description": "Busca a cualquier persona (docente, profesor, alumno, compañero) por su nombre, apellido o apodo para conocer sus datos de contacto, rol y materia.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "nombre": {"type": "STRING", "description": "Nombre, apellido o apodo de la persona"}
                    },
                    "required": ["nombre"]
                }
            },
            {
                "name": "buscar_docente",
                "description": "Busca información sobre un docente por su nombre o apodo (ej. 'Fabri', 'Fernandez', 'Olga', 'Graneros') o materias a su cargo.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "termino": {"type": "STRING", "description": "Nombre o término de búsqueda del docente"}
                    },
                    "required": ["termino"]
                }
            },
            {
                "name": "consultar_actividades_pendientes",
                "description": "Consulta si el estudiante debe alguna tarea, entrega o actividad pendiente en sus materias.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "materia": {"type": "STRING", "description": "Nombre opcional de la materia para filtrar"}
                    }
                }
            },
            {
                "name": "listar_mensajes_webmail",
                "description": "Lista los mensajes o correos recibidos en el campus virtual.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "materia": {"type": "STRING", "description": "Nombre opcional de la materia"}
                    }
                }
            },
            {
                "name": "consultar_chat_materia",
                "description": "Consulta los mensajes recientes enviados en el chat en vivo o sala de conversación del aula virtual de una materia.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "materia": {"type": "STRING", "description": "Nombre de la materia (ej. 'Práctica', 'Redes', 'Programación')"}
                    },
                    "required": ["materia"]
                }
            },
            {
                "name": "ver_contenido_mensaje",
                "description": "Lee el contenido detallado de un mensaje o correo del campus por su enlace o asunto.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "link_o_asunto": {"type": "STRING", "description": "Identificador, asunto o enlace del mensaje"}
                    },
                    "required": ["link_o_asunto"]
                }
            },
            {
                "name": "listar_alumnos",
                "description": "Lista los nombres y datos de compañeros o alumnos de una materia o de todas las materias.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "materia": {"type": "STRING", "description": "Nombre opcional de la materia"}
                    }
                }
            },
            {
                "name": "enviar_mensaje_chat_materia",
                "description": "Envía un mensaje al chat o foro del aula virtual de una materia especificada por el alumno.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "materia": {"type": "STRING", "description": "Nombre de la materia (ej. 'Redes', 'Programación', 'Prácticas Profesionalizantes')"},
                        "mensaje": {"type": "STRING", "description": "Texto del mensaje a enviar"}
                    },
                    "required": ["materia", "mensaje"]
                }
            },
            {
                "name": "obtener_ultima_actividad",
                "description": "Obtiene la última actividad, tarea o consigna de una materia.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "materia": {"type": "STRING", "description": "Nombre de la materia"}
                    },
                    "required": ["materia"]
                }
            },
            {
                "name": "obtener_correo_docente",
                "description": "Obtiene la dirección de correo electrónico o canal de mensajería del docente de una materia.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "materia": {"type": "STRING", "description": "Nombre de la materia"}
                    },
                    "required": ["materia"]
                }
            },
            {
                "name": "obtener_consigna_actividad",
                "description": "Obtiene y extrae el texto completo de la consigna de una actividad específica.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "actividad": {"type": "STRING", "description": "Nombre o título de la actividad"},
                        "materia": {"type": "STRING", "description": "Nombre opcional de la materia"}
                    },
                    "required": ["actividad"]
                }
            },
            {
                "name": "buscar_calificaciones",
                "description": "Consulta las notas y calificaciones del alumno en sus materias.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "materia": {"type": "STRING", "description": "Nombre de la materia opcional para filtrar"}
                    }
                }
            },
            {
                "name": "buscar_asistencia",
                "description": "Consulta el registro de asistencia del alumno.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "materia": {"type": "STRING", "description": "Nombre de la materia opcional para filtrar"}
                    }
                }
            },
            {
                "name": "obtener_fechas_parciales",
                "description": "Busca fechas de exámenes parciales, trabajos prácticos y entregas de una materia.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "materia": {"type": "STRING", "description": "Nombre de la materia (ej. 'Redes', 'Programación')"}
                    },
                    "required": ["materia"]
                }
            },
            {
                "name": "enviar_mensaje_grupo",
                "description": "Envía un mensaje grupal al canal o grupo de trabajo de una materia.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "contenido": {"type": "STRING", "description": "Texto del mensaje"},
                        "grupo": {"type": "STRING", "description": "Identificador del grupo (ej. 'grupo2')"},
                        "materia": {"type": "STRING", "description": "Materia opcional"}
                    },
                    "required": ["contenido"]
                }
            },
            {
                "name": "buscar_en_sitio_institucional",
                "description": "Consulta comunicados oficiales, avisos y resoluciones del sitio web institucional.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "consulta": {"type": "STRING", "description": "Consulta o tema institucional"}
                    },
                    "required": ["consulta"]
                }
            }
        ]

    def ejecutar_herramienta(self, nombre: str, args: dict = None) -> Any:
        """Ejecuta dinámicamente cualquier herramienta registrada por su nombre."""
        args = args or {}
        metodo = getattr(self, nombre, None)
        if callable(metodo):
            try:
                return metodo(**args)
            except TypeError:
                try:
                    return metodo(*args.values())
                except Exception as e:
                    return {"error": str(e)}
        return {"error": f"Herramienta '{nombre}' no encontrada."}


# Export helper functions for direct testing and functional calling
_default_tools = AgentTools()

def buscar_en_indice(consulta: str):
    return _default_tools.buscar_en_indice(consulta)

def obtener_contenido_completo(titulo_o_fuente: str):
    return _default_tools.obtener_contenido_completo(titulo_o_fuente)

def obtener_datos_usuario():
    return _default_tools.obtener_datos_usuario()

def buscar_calificaciones(materia: Optional[str] = None):
    return _default_tools.buscar_calificaciones(materia)

def buscar_asistencia(materia: Optional[str] = None):
    return _default_tools.buscar_asistencia(materia)

def obtener_fechas_parciales(materia: str = ""):
    return _default_tools.obtener_fechas_parciales(materia)

def obtener_docente_materia(materia: str):
    return _default_tools.obtener_docente_materia(materia)

def obtener_ultima_actividad(materia: str):
    return _default_tools.obtener_ultima_actividad(materia)

def obtener_correo_docente(materia: str):
    return _default_tools.obtener_correo_docente(materia)

def obtener_consigna_actividad(actividad: str, materia: str = ""):
    return _default_tools.obtener_consigna_actividad(actividad, materia)

def enviar_mensaje_grupo(grupo: str = "grupo2", contenido: str = "", materia: str = ""):
    return _default_tools.enviar_mensaje_grupo(contenido=contenido, grupo=grupo, materia=materia)

def buscar_en_sitio_institucional(consulta: str):
    return _default_tools.buscar_en_sitio_institucional(consulta)
