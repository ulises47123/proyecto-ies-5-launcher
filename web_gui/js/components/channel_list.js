import { state } from "../state.js";

const CHANNELS = [
  { id: "novedades", name: "novedades", icon: "ph-broadcast" },
  { id: "contactos", name: "contactos-aula", icon: "ph-address-book" },
  { id: "actividades", name: "actividades-tareas", icon: "ph-clipboard-text" },
  { id: "mensajes", name: "correo-interno", icon: "ph-envelope" },
  { id: "calificaciones", name: "calificaciones", icon: "ph-chart-bar" },
  { id: "sitio", name: "noticias-instituto", icon: "ph-newspaper" },
  { id: "ia", name: "asistente-ia", icon: "ph-sparkle" },
];

export class ChannelList {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    state.subscribe((event, data) => {
      if (event === "curso_selected" || event === "channel_selected") {
        this.render();
      }
    });
  }

  render() {
    this.container.innerHTML = "";
    CHANNELS.forEach((ch) => {
      const active = state.selectedChannel === ch.id;
      const btn = document.createElement("button");
      btn.className = `w-full px-2.5 py-1.5 rounded-md flex items-center gap-2 text-sm font-medium transition-colors ${
        active
          ? "bg-discord-activeItem text-discord-textHeader"
          : "text-discord-textMuted hover:bg-discord-hoverItem hover:text-discord-textNormal"
      }`;

      btn.innerHTML = `
        <i class="ph-bold ${ch.icon} text-base"></i>
        <span class="truncate">${ch.name}</span>
      `;

      btn.onclick = () => state.selectChannel(ch.id);
      this.container.appendChild(btn);
    });
  }
}
