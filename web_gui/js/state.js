/**
 * state.js — Maneja el estado global reactivo de la aplicación.
 */

class AppState {
  constructor() {
    this.user = null;
    this.cursos = [];
    this.selectedCurso = null;
    this.selectedChannel = "novedades";
    this.contactos = { docentes: [], alumnos: [] };
    this.listeners = [];
  }

  subscribe(fn) {
    this.listeners.push(fn);
  }

  notify(event, data) {
    this.listeners.forEach((fn) => fn(event, data, this));
  }

  setUser(user) {
    this.user = user;
    this.notify("user_changed", user);
  }

  setCursos(cursos) {
    this.cursos = cursos || [];
    this.notify("cursos_changed", this.cursos);
  }

  selectCurso(curso) {
    this.selectedCurso = curso;
    this.notify("curso_selected", curso);
  }

  selectChannel(channelId) {
    this.selectedChannel = channelId;
    this.notify("channel_selected", channelId);
  }

  setContactos(contactos) {
    this.contactos = contactos || { docentes: [], alumnos: [] };
    this.notify("contactos_changed", this.contactos);
  }
}

export const state = new AppState();
