"""
ia/prompt_builder.py — Construcción de prompts personalizados adaptados al perfil del estudiante y las herramientas disponibles.
"""
from typing import Dict, Any, List


class PromptBuilder:
    """Construye el System Prompt y mensajes para los modelos de lenguaje."""

    @staticmethod
    def build_system_prompt(user_context: Dict[str, Any], kb_docs: List[Dict[str, Any]] = None) -> str:
        from datetime import datetime
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        now = datetime.now()
        dia_sem = dias[now.weekday()]
        mes_nom = meses[now.month - 1]
        fecha_actual_str = f"{dia_sem}, {now.day} de {mes_nom} de {now.year} (Hora local: {now.strftime('%H:%M')})"

        nombre = user_context.get("nombre_pila", "Estudiante")
        carrera = user_context.get("carrera", "IES N°5 'José E. Tello'")
        materias = user_context.get("materias", [])

        mat_str = ""
        if materias:
            mat_lines = []
            for m in materias:
                docs = ", ".join(m.get("docentes", []))
                mat_lines.append(f"- {m.get('nombre')} (Docente(s): {docs}, Avance: {m.get('avance', 0)}%)")
            mat_str = "Materias y Docentes a cargo del estudiante:\n" + "\n".join(mat_lines)

        kb_str = ""
        if kb_docs:
            kb_str = "\nDocumentos cargados en la Base de Conocimiento local:\n" + "\n".join(
                [f"- {d.get('titulo')} [{d.get('materia', 'General')}]: {', '.join(d.get('indice', [])[:4])}" for d in kb_docs[:8]]
            )

        return (
            f"Eres el Asistente Virtual Inteligente oficial del I.E.S. Nº5 'José E. Tello'.\n"
            f"FECHA Y HORA ACTUAL: {fecha_actual_str}\n"
            f"Estás interactuando con el/la estudiante {nombre} de la carrera '{carrera}'.\n\n"
            f"DIRECTIVAS DE ESTILO Y TONO:\n"
            f"1. Sé amable, humano, directo y habla en español (tono amigable de estudiante/tutor argentino).\n"
            f"2. IMPORTANTE: Evita el formato robótico con exceso de asteriscos dobles (**) o viñetas innecesarias en cada palabra. Escribe párrafos fluidos y limpios.\n"
            f"3. Conoces la fecha y hora actual y puedes responderla directamente cuando te pregunten qué día es hoy o la fecha.\n"
            f"4. Si te preguntan por actividades o tareas pendientes, consulta 'consultar_actividades_pendientes' y responde claramente si debe entregas.\n"
            f"5. Si te piden enviar un mensaje a un chat de una materia, utiliza la herramienta 'enviar_mensaje_chat_materia' indicando la materia y el mensaje.\n"
            f"6. Si te preguntan por una persona (docente o compañero), busca sus datos y menciona directamente su información relevante sin agregar personas no relacionadas ni volcados innecesarios.\n"
            f"7. Nunca devuelvas código JSON ni diccionarios crudos en tus respuestas finales.\n\n"
            f"INFORMACIÓN DEL ALUMNO:\n{mat_str}\n{kb_str}"
        )
