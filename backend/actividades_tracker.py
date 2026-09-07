"""
backend/actividades_tracker.py — Monitoreo dinámico y registro persistente de actividades pendientes y por vencer.
Aplica el principio de responsabilidad única (Unix: una sola tarea bien hecha).
- Revisa las materias del estudiante omitiendo las entregadas.
- Captura título, fechas de apertura y cierre (hasta), materia y tiempo restante.
- Funciona exclusivamente si el autologueo está activado.
- Guarda un registro persistente con la fecha de última revisión tolerante a reinicios del equipo.
- IMPORTANTE: No emite notificaciones de sistema (Windows). Sus avisos se integran exclusivamente en Novedades y en la UI.
"""
import os
import re
import json
import logging
from datetime import datetime, timedelta
from backend.session import CampusSession
from config import DATA_DIR, cargar_config, tiene_sesion_guardada, formatear_hora_str
import backend.programa as prog_mod

REGISTRO_ACTIVIDADES_FILE = os.path.join(DATA_DIR, "registro_actividades.json")


def cargar_registro(file_path: str = REGISTRO_ACTIVIDADES_FILE) -> dict:
    """Carga el registro persistente de actividades pendientes desde el archivo JSON."""
    if not os.path.exists(file_path):
        return {
            "ultima_revision": "",
            "ultimo_recordatorio": "",
            "actividades_pendientes": [],
            "historial_revisiones": []
        }
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                data = {}
            data.setdefault("ultima_revision", "")
            data.setdefault("ultimo_recordatorio", "")
            data.setdefault("actividades_pendientes", [])
            data.setdefault("historial_revisiones", [])
            return data
    except Exception as e:
        logging.warning(f"Error al cargar {file_path}: {e}")
        return {
            "ultima_revision": "",
            "ultimo_recordatorio": "",
            "actividades_pendientes": [],
            "historial_revisiones": []
        }


def guardar_registro(data: dict, file_path: str = REGISTRO_ACTIVIDADES_FILE):
    """Guarda el registro persistente de actividades pendientes en formato JSON."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning(f"Error al guardar {file_path}: {e}")


def autologueo_esta_activo(config: dict = None) -> bool:
    """
    Verifica si la función de autologueo (recordar sesión / auto-login) está habilitada.
    El tracker solo opera si esta condición se cumple.
    """
    return tiene_sesion_guardada()


def calcular_tiempo_restante(fecha_apertura_str: str) -> dict:
    """
    Parsea las fechas desde la cadena de texto de la plataforma (ej: 'Abierta desde ... hasta 09/09/2026 23:59').
    Calcula horas restantes, días restantes, y banderas de vencimiento.
    """
    res = {
        "fecha_limite": "",
        "horas_restantes": None,
        "dias_restantes": None,
        "por_vencer": False,
        "vencida": False,
        "tiempo_restante_str": "Sin fecha límite especificada"
    }

    if not fecha_apertura_str:
        return res

    m_hasta = re.search(r'hasta\s*(\d{2}/\d{2}/\d{4}(?:\s*\d{2}:\d{2})?)', fecha_apertura_str, re.I)
    if not m_hasta:
        # Fallback a buscar cualquier fecha DD/MM/AAAA
        m_fecha = re.search(r'(\d{2}/\d{2}/\d{4}(?:\s*\d{2}:\d{2})?)', fecha_apertura_str)
        if not m_fecha:
            return res
        f_str = m_fecha.group(1).strip()
    else:
        f_str = m_hasta.group(1).strip()

    res["fecha_limite"] = f_str
    try:
        fmt = "%d/%m/%Y %H:%M" if " " in f_str else "%d/%m/%Y"
        dt_lim = datetime.strptime(f_str, fmt)
        if fmt == "%d/%m/%Y":
            # Si no tiene hora, considerar fin del día (23:59)
            dt_lim = dt_lim.replace(hour=23, minute=59, second=59)

        ahora = datetime.now()
        diff = dt_lim - ahora
        horas = diff.total_seconds() / 3600.0
        dias = diff.days

        res["horas_restantes"] = round(horas, 1)
        res["dias_restantes"] = dias

        if horas < 0:
            res["vencida"] = True
            dias_pasados = abs(dias)
            res["tiempo_restante_str"] = f"Venció hace {dias_pasados} día(s)" if dias_pasados > 0 else "Venció recientemente"
        else:
            if horas <= 48:
                res["por_vencer"] = True
            if dias == 0:
                h_int = max(1, int(horas))
                res["tiempo_restante_str"] = f"¡Vence hoy! (Quedan {h_int} hs aprox.)"
            elif dias == 1:
                res["tiempo_restante_str"] = "Vence mañana"
            else:
                res["tiempo_restante_str"] = f"Vence en {dias} días"
    except Exception as ex:
        logging.debug(f"Error parseando fecha '{f_str}': {ex}")

    return res


def debe_ejecutar_revision(config: dict = None, registro: dict = None) -> bool:
    """
    Determina si corresponde realizar un escaneo según el intervalo de días configurado
    y la marca temporal de la última revisión.
    """
    if config is None:
        config = cargar_config()
    if not autologueo_esta_activo(config):
        return False
    if not config.get("monitorear_actividades_pendientes", True):
        return False

    if registro is None:
        registro = cargar_registro()

    ultima_str = registro.get("ultima_revision", "")
    if not ultima_str:
        return True

    try:
        dt_ult = datetime.fromisoformat(ultima_str)
        intervalo_dias = max(1, int(config.get("intervalo_revision_actividades_dias", 1)))
        delta_requerido = timedelta(days=intervalo_dias)
        return (datetime.now() - dt_ult) >= delta_requerido
    except Exception:
        return True


def debe_mostrar_recordatorio_frecuente(config: dict = None, registro: dict = None) -> bool:
    """
    Verifica si el usuario tiene activada la opción de recordatorios insistentes
    y si ha transcurrido el intervalo en horas (ej: cada 1 o 2 horas) cuando hay
    actividades próximas a vencer.
    """
    if config is None:
        config = cargar_config()
    if not autologueo_esta_activo(config):
        return False
    if not config.get("recordatorio_frecuente_vencimiento", True):
        return False

    if registro is None:
        registro = cargar_registro()

    # Verificar si hay actividades pendientes por vencer (no vencidas)
    pendientes = registro.get("actividades_pendientes", [])
    hay_por_vencer = any(a.get("por_vencer", False) and not a.get("vencida", False) for a in pendientes)
    if not hay_por_vencer:
        return False

    ult_rec_str = registro.get("ultimo_recordatorio", "")
    if not ult_rec_str:
        return True

    try:
        dt_rec = datetime.fromisoformat(ult_rec_str)
        intervalo_hs = max(1, int(config.get("intervalo_recordatorio_horas", 2)))
        return (datetime.now() - dt_rec) >= timedelta(hours=intervalo_hs)
    except Exception:
        return True


def escanear_actividades_pendientes(
    sess: CampusSession,
    cursos: list[dict] = None,
    config: dict = None,
    forzar: bool = False
) -> list[dict]:
    """
    Escanea las materias del estudiante extrayendo las actividades que aún adeuda.
    - Omite las actividades que ya fueron entregadas o completadas.
    - Captura: id_curso, materia, título, fecha apertura, fecha límite y tiempo restante.
    - Guarda los datos de forma persistente en registro_actividades.json con la marca temporal.
    """
    if config is None:
        config = cargar_config()

    if not autologueo_esta_activo(config) and not forzar:
        logging.info("Tracker de actividades inactivo (autologueo no habilitado).")
        return []

    registro = cargar_registro()

    # Si no se fuerza y aún no pasó el intervalo, devolver lo que ya teníamos registrado
    if not forzar and not debe_ejecutar_revision(config, registro):
        return registro.get("actividades_pendientes", [])

    logging.info("Iniciando escaneo de actividades pendientes en el campus...")
    actividades_adeudadas = []

    if cursos is None:
        try:
            from backend.escritorio import get_escritorio
            cursos, _, _ = get_escritorio(sess)
        except Exception:
            cursos = []

    # Respetar la configuración de materias anteriores
    mostrar_anteriores = config.get("mostrar_materias_anteriores", False)
    if not mostrar_anteriores and cursos:
        anios = [c.get("anio") for c in cursos if c.get("anio")]
        max_anio = max(anios) if anios else None
        if max_anio:
            cursos = [c for c in cursos if c.get("anio") == max_anio or str(max_anio) in c.get("nombre", "")]

    for c in (cursos or []):
        cid = str(c.get("id", "")).strip()
        cnom = c.get("nombre", "Materia").strip()
        if not cid:
            continue

        try:
            unidades = prog_mod.get_programa(sess, cid)
            for u in unidades:
                items = u.get("items", [])
                for it in items:
                    tipo = it.get("tipo", "")
                    tipo_desc = it.get("tipo_desc", "").lower()

                    # Solo nos interesan ítems de tipo actividad
                    if tipo != "actividad" and "actividad" not in tipo_desc:
                        continue

                    estado = it.get("estado", "").strip()
                    estado_lower = estado.lower()

                    # Omitir si ya está entregada o aprobada/completada
                    if any(k in estado_lower for k in ["entregad", "completad", "aprobado", "calificado"]):
                        continue

                    # Capturar datos de la actividad adeudada
                    f_apertura = it.get("fecha_apertura", "").strip()
                    tiempo_info = calcular_tiempo_restante(f_apertura)

                    act_item = {
                        "id_curso": cid,
                        "curso_nombre": cnom,
                        "titulo": it.get("titulo", "Actividad sin título").strip(),
                        "url": it.get("url", ""),
                        "fecha_apertura": f_apertura,
                        "fecha_limite": tiempo_info.get("fecha_limite", ""),
                        "estado": estado if estado else "Pendiente",
                        "horas_restantes": tiempo_info.get("horas_restantes"),
                        "dias_restantes": tiempo_info.get("dias_restantes"),
                        "por_vencer": tiempo_info.get("por_vencer", False),
                        "vencida": tiempo_info.get("vencida", False),
                        "tiempo_restante_str": tiempo_info.get("tiempo_restante_str", "")
                    }
                    actividades_adeudadas.append(act_item)
        except Exception as ex:
            logging.warning(f"Error escaneando actividades para el curso {cid} ({cnom}): {ex}")

    # Actualizar registro persistente
    ahora_iso = datetime.now().isoformat()
    registro["ultima_revision"] = ahora_iso
    registro["actividades_pendientes"] = actividades_adeudadas
    
    # Mantener historial de las últimas 5 fechas de revisión
    hist = registro.get("historial_revisiones", [])
    hist.append(ahora_iso)
    registro["historial_revisiones"] = hist[-10:]

    guardar_registro(registro)
    logging.info(f"Escaneo finalizado: {len(actividades_adeudadas)} actividades adeudadas registradas.")
    return actividades_adeudadas


def marcar_recordatorio_emitido():
    """Registra la marca temporal del último recordatorio frecuente mostrado en la UI."""
    registro = cargar_registro()
    registro["ultimo_recordatorio"] = datetime.now().isoformat()
    guardar_registro(registro)


def generar_novedades_actividades_pendientes(registro=None) -> list[dict]:
    """
    Convierte las actividades adeudadas del registro persistente (o lista) en tarjetas dinámicas
    para presentarlas de forma destacada en la sección de Novedades.
    """
    if registro is None:
        registro = cargar_registro()

    if isinstance(registro, dict):
        pendientes = list(registro.get("actividades_pendientes", []))
    elif isinstance(registro, list):
        pendientes = list(registro)
    else:
        pendientes = []

    # Requerimiento: 1º van las vencidas, después las que debe (en ese orden exacto)
    def _sort_key(act):
        es_vencida = 0 if act.get("vencida", False) else 1
        hr = act.get("horas_restantes")
        hr_val = float(hr) if hr is not None else 999999.0
        return (es_vencida, hr_val if es_vencida == 1 else -abs(hr_val))

    pendientes = sorted(pendientes, key=_sort_key)

    novedades_actividades = []

    for a in pendientes:
        por_vencer = a.get("por_vencer", False)
        vencida = a.get("vencida", False)
        curso_id = a.get("id_curso") or a.get("curso_id") or ""
        titulo = a.get("titulo", "Actividad")
        curso_nombre = a.get("curso_nombre", "Materia")

        if vencida:
            icono = "⏰"
            tag = "Cerrada sin entregar"
        elif por_vencer:
            icono = "🔥"
            tag = "¡Por vencer!"
        else:
            icono = "✏️"
            tag = "Pendiente de entrega"

        f_limite = formatear_hora_str(a.get("fecha_limite") or "Sin fecha")
        f_apertura = formatear_hora_str(a.get("fecha_apertura", "No especificado"))

        nov = {
            "id": f"act_pend_{curso_id}_{abs(hash(titulo)) % 100000}",
            "tipo": "actividad",
            "titulo": f"{icono} {titulo}",
            "curso": curso_nombre,
            "id_curso": curso_id,
            "autor": curso_nombre,
            "fecha": f_limite,
            "url": a.get("url", ""),
            "texto": (
                f"Materia: {curso_nombre}\n"
                f"Estado: {a.get('estado', 'Pendiente')}\n"
                f"Período: {f_apertura}\n"
                f"Plazo: {a.get('tiempo_restante_str', '')}"
            ),
            "leido": False,
            "es_actividad_adeudada": True,
            "por_vencer": por_vencer,
            "vencida": vencida,
            "tag_alerta": tag,
            "tiempo_restante_str": a.get("tiempo_restante_str", "")
        }
        novedades_actividades.append(nov)

    return novedades_actividades

