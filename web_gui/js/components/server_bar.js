import { state } from "../state.js";

export class ServerBar {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.courseTitleEl = document.getElementById("course-title");
    this.btnHome = document.getElementById("btn-home");

    if (this.btnHome) {
      this.btnHome.onclick = () => {
        if (state.cursos && state.cursos.length > 0) {
          state.selectCurso(state.cursos[0]);
        }
        state.selectChannel("novedades");
      };
    }

    state.subscribe((event, data) => {
      if (event === "cursos_changed") this.render();
      if (event === "curso_selected") {
        this.updateActive(data);
        if (this.courseTitleEl && data) {
          this.courseTitleEl.innerText = data.nombre || "Campus IES N°5";
          this.courseTitleEl.title = data.nombre || "";
        }
      }
    });
  }

  render() {
    this.container.innerHTML = "";
    state.cursos.forEach((curso) => {
      const btn = document.createElement("button");
      btn.className = "w-12 h-12 rounded-[24px] hover:rounded-[16px] bg-discord-channellist hover:bg-discord-accent text-discord-textHeader font-bold text-xs flex items-center justify-center transition-all duration-200 relative group shrink-0";
      btn.title = curso.nombre || "Materia";

      // Iniciales del curso
      const words = (curso.nombre || "Materia").split(" ").filter(w => w.length > 2);
      const initials = (words.slice(0, 2).map(w => w[0]).join("") || "M").toUpperCase();

      btn.innerHTML = `
        <span>${initials}</span>
        <div class="indicator absolute left-0 w-1 h-2 rounded-r-full bg-white opacity-0 group-hover:opacity-100 transition-all"></div>
      `;

      btn.onclick = () => state.selectCurso(curso);
      this.container.appendChild(btn);
    });
  }

  updateActive(selectedCurso) {
    const buttons = this.container.querySelectorAll("button");
    state.cursos.forEach((c, i) => {
      const btn = buttons[i];
      if (!btn) return;
      const indicator = btn.querySelector(".indicator");
      if (selectedCurso && String(c.id) === String(selectedCurso.id)) {
        btn.classList.remove("rounded-[24px]", "bg-discord-channellist");
        btn.classList.add("rounded-[16px]", "bg-discord-accent");
        if (indicator) {
          indicator.classList.remove("h-2", "opacity-0");
          indicator.classList.add("h-8", "opacity-100");
        }
      } else {
        btn.classList.remove("rounded-[16px]", "bg-discord-accent");
        btn.classList.add("rounded-[24px]", "bg-discord-channellist");
        if (indicator) {
          indicator.classList.remove("h-8", "opacity-100");
          indicator.classList.add("h-2", "opacity-0");
        }
      }
    });
  }
}
