/**
 * bridge.js — Encapsula TODAS las llamadas a Pyloid (SRP estricto).
 * Es el único archivo que interactúa con la API IPC de Pyloid expuesta en window.
 */

class PyloidBridge {
  constructor() {
    this._ipc = null;
    this._ready = false;
  }

  async init() {
    return new Promise((resolve) => {
      const checkIPC = () => {
        if (window.ipc && window.ipc.CampusAPI) {
          this._ipc = window.ipc.CampusAPI;
          this._ready = true;
          console.log("[Bridge] Pyloid IPC conectado exitosamente.");
          resolve(true);
        } else {
          setTimeout(checkIPC, 50);
        }
      };
      checkIPC();
    });
  }

  async _call(method, ...args) {
    if (!this._ready || !this._ipc) {
      await this.init();
    }
    return new Promise((resolve) => {
      try {
        this._ipc[method](...args, (res) => {
          try {
            const parsed = typeof res === "string" ? JSON.parse(res) : res;
            resolve(parsed);
          } catch (e) {
            resolve(res);
          }
        });
      } catch (err) {
        resolve({ ok: false, error: err.toString() });
      }
    });
  }

  // ── Métodos de Autenticación ──
  async checkAuth() { return this._call("check_auth"); }
  async restoreSession() { return this._call("restore_session"); }
  async login(user, pass, remember, autologin) {
    return this._call("login", String(user), String(pass), Boolean(remember), Boolean(autologin));
  }
  async logout() { return this._call("logout"); }
  async getProfile() { return this._call("get_profile"); }

  // ── Materias / Cursos ──
  async getCursos(force = false) { return this._call("get_cursos", Boolean(force)); }
  async getContactos(cursoId, force = false) { return this._call("get_contactos", String(cursoId), Boolean(force)); }
  async getPerfil(cursoId, usuarioId) { return this._call("get_perfil", String(cursoId), String(usuarioId)); }
  async getPrograma(cursoId) { return this._call("get_programa", String(cursoId)); }
  async getActividadDetalle(url) { return this._call("get_actividad_detalle", String(url)); }
  async getPendientes() { return this._call("get_pendientes"); }

  // ── Calificaciones ──
  async getCalificaciones(cursoId) { return this._call("get_calificaciones", String(cursoId)); }

  // ── Webmail / Mensajería ──
  async getMensajes(cursoId, bandeja = "Inbox") { return this._call("get_mensajes", String(cursoId), String(bandeja)); }
  async getMensajeDetalle(linkOId, cursoId = "") { return this._call("get_mensaje_detalle", String(linkOId), String(cursoId)); }
  async enviarMensaje(cursoId, destinatarios, asunto, cuerpo, archivoAdjunto = "") {
    return this._call("enviar_mensaje", String(cursoId), String(destinatarios), String(asunto), String(cuerpo), String(archivoAdjunto));
  }
  async responderMensaje(cursoId, emailId, destinatarioId, asunto, cuerpo) {
    return this._call("responder_mensaje", String(cursoId), String(emailId), String(destinatarioId), String(asunto), String(cuerpo));
  }
  async reenviarMensaje(cursoId, emailId, destinatarioId, asunto, nota = "") {
    return this._call("reenviar_mensaje", String(cursoId), String(emailId), String(destinatarioId), String(asunto), String(nota));
  }
  async eliminarMensaje(cursoId, emailId) { return this._call("eliminar_mensaje", String(cursoId), String(emailId)); }
  async vaciarPapelera(cursoId) { return this._call("vaciar_papelera", String(cursoId)); }

  // ── Sitio Institucional ──
  async getSitioNoticias(force = false) { return this._call("get_sitio_noticias", Boolean(force)); }
  async buscarSitio(query, maxRes = 10) { return this._call("buscar_sitio", String(query), Number(maxRes)); }

  // ── Inteligencia Artificial ──
  async askIA(prompt) { return this._call("ask_ia", String(prompt)); }
}

export const bridge = new PyloidBridge();
