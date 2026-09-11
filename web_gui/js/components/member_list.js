import { state } from "../state.js";

export class MemberList {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    state.subscribe((event, data) => {
      if (event === "contactos_changed") this.render();
    });
  }

  render() {
    this.container.innerHTML = "";
    const { docentes, alumnos } = state.contactos;

    if (docentes && docentes.length > 0) {
      this._renderSection("DOCENTES", docentes, true);
    }
    if (alumnos && alumnos.length > 0) {
      this._renderSection("COMPAÑEROS", alumnos, false);
    }
  }

  _renderSection(title, list, isDocente) {
    const groupTitle = document.createElement("div");
    groupTitle.className = "text-[11px] font-bold text-discord-textMuted tracking-wider uppercase px-2 mb-1 mt-2";
    groupTitle.innerText = `${title} — ${list.length}`;
    this.container.appendChild(groupTitle);

    list.forEach((m) => {
      const item = document.createElement("div");
      item.className = "flex items-center gap-2.5 px-2 py-1.5 rounded-md hover:bg-discord-hoverItem cursor-pointer transition-colors";
      const foto = m.foto_url || "https://ies5tello-juj.infd.edu.ar/aula/skins/redinfod/img/comunes/thumb_40x45.jpg";

      item.innerHTML = `
        <div class="w-8 h-8 rounded-full overflow-hidden bg-discord-serverbar shrink-0">
          <img src="${foto}" alt="${m.nombre}" class="w-full h-full object-cover">
        </div>
        <div class="min-w-0">
          <div class="text-xs font-medium ${isDocente ? "text-discord-accent font-bold" : "text-discord-textNormal"} truncate">${m.nombre}</div>
          <div class="text-[10px] text-discord-textMuted truncate">${isDocente ? "Docente" : (m.email !== "No especificado" ? m.email : "Estudiante")}</div>
        </div>
      `;

      item.onclick = () => {
        alert(`Ficha de Contacto:
Nombre: ${m.nombre}
Rol: ${m.rol}
Email: ${m.email}
Tel: ${m.telefono}`);
      };

      this.container.appendChild(item);
    });
  }
}
