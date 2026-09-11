"""
services — Capa de servicios desacoplada para la arquitectura SRP y GUI Web.
Aisla la logica de negocio y el acceso a datos del frontend.
"""
from services.auth_service import AuthService
from services.cursos_service import CursosService
from services.contactos_service import ContactosService
from services.actividades_service import ActividadesService
from services.mensajes_service import MensajesService
from services.calificaciones_service import CalificacionesService
from services.sitio_service import SitioService
from services.ia_service import IAService

__all__ = [
    "AuthService",
    "CursosService",
    "ContactosService",
    "ActividadesService",
    "MensajesService",
    "CalificacionesService",
    "SitioService",
    "IAService",
]
