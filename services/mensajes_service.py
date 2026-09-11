"""
services/mensajes_service.py — Servicio de mensajeria interna / webmail del campus.
Responsabilidad unica (SRP): Lectura, redactado y envio de mensajes de correo interno.
Contrato uniforme JSON: {"ok": True, "data": ...} / {"ok": False, "error": "..."}
"""
from typing import Dict, Any, List, Optional
from backend.session import CampusSession
from backend.mensajes import (
    get_mensajes, get_detalle_mensaje, enviar_nuevo_mensaje,
    responder_mensaje, reenviar_mensaje, eliminar_mensaje, vaciar_papelera
)


class MensajesService:
    """Gestiona la mensajeria interna de las aulas."""

    def __init__(self, session: CampusSession):
        self.session = session

    def get_mensajes_bandeja(self, curso_id: str, bandeja: str = "Inbox") -> Dict[str, Any]:
        try:
            mensajes = get_mensajes(self.session, str(curso_id), bandeja=bandeja)
            return {"ok": True, "data": mensajes}
        except Exception as e:
            return {"ok": False, "error": f"Error al obtener bandeja {bandeja}: {str(e)}"}

    def get_detalle_mensaje(self, link_o_id: str, id_curso: str = "", fecha_novedad: str = "", asunto_novedad: str = "") -> Dict[str, Any]:
        try:
            detalle = get_detalle_mensaje(self.session, link_o_id, id_curso=id_curso, fecha_novedad=fecha_novedad, asunto_novedad=asunto_novedad)
            return {"ok": True, "data": detalle}
        except Exception as e:
            return {"ok": False, "error": f"Error al obtener mensaje: {str(e)}"}

    def enviar_mensaje(self, id_curso: str, destinatarios: list | str, asunto: str, cuerpo: str, archivo_adjunto: Optional[str] = None) -> Dict[str, Any]:
        try:
            ok, msg = enviar_nuevo_mensaje(self.session, id_curso, destinatarios, asunto, cuerpo, archivo_adjunto)
            return {"ok": ok, "data" if ok else "error": msg}
        except Exception as e:
            return {"ok": False, "error": f"Error al enviar mensaje: {str(e)}"}

    def responder(self, id_curso: str, id_email: str, destinatario_id: str, asunto: str, cuerpo: str) -> Dict[str, Any]:
        try:
            ok, msg = responder_mensaje(self.session, id_curso, id_email, destinatario_id, asunto, cuerpo)
            return {"ok": ok, "data" if ok else "error": msg}
        except Exception as e:
            return {"ok": False, "error": f"Error al responder mensaje: {str(e)}"}

    def reenviar(self, id_curso: str, id_email: str, destinatario_id: str, asunto: str, nota_adicional: str = "") -> Dict[str, Any]:
        try:
            ok, msg = reenviar_mensaje(self.session, id_curso, id_email, destinatario_id, asunto, nota_adicional)
            return {"ok": ok, "data" if ok else "error": msg}
        except Exception as e:
            return {"ok": False, "error": f"Error al reenviar mensaje: {str(e)}"}

    def eliminar(self, id_curso: str, id_email: str) -> Dict[str, Any]:
        try:
            ok, msg = eliminar_mensaje(self.session, id_curso, id_email)
            return {"ok": ok, "data" if ok else "error": msg}
        except Exception as e:
            return {"ok": False, "error": f"Error al eliminar mensaje: {str(e)}"}

    def vaciar_papelera(self, id_curso: str) -> Dict[str, Any]:
        try:
            ok, msg = vaciar_papelera(self.session, id_curso)
            return {"ok": ok, "data" if ok else "error": msg}
        except Exception as e:
            return {"ok": False, "error": f"Error al vaciar papelera: {str(e)}"}
