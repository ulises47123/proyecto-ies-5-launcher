import { state } from "../state.js";
import { bridge } from "../bridge.js";

export class UserPanel {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    state.subscribe((event, data) => {
      if (event === "user_changed") this.render();
    });
  }

  render() {
    const user = state.user || { nombre: "Usuario", dni: "" };
    const avatar = user.foto_url || "https://ies5tello-juj.infd.edu.ar/aula/skins/redinfod/img/comunes/thumb_40x45.jpg";

    this.container.innerHTML = `
      <div class="flex items-center gap-2.5 min-w-0">
        <div class="relative w-8 h-8 rounded-full overflow-hidden bg-discord-serverbar shrink-0">
          <img src="${avatar}" alt="Avatar" class="w-full h-full object-cover">
          <div class="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-discord-green border-2 border-discord-userpanel"></div>
        </div>
        <div class="min-w-0">
          <div class="text-xs font-bold text-discord-textHeader truncate">${user.nombre}</div>
          <div class="text-[10px] text-discord-textMuted truncate">${user.dni || "Online"}</div>
        </div>
      </div>
      <button id="btn-logout" title="Cerrar Sesión" class="p-1.5 hover:bg-discord-activeItem rounded text-discord-textMuted hover:text-red-400 transition-colors">
        <i class="ph-bold ph-sign-out text-base"></i>
      </button>
    `;

    const btnLogout = this.container.querySelector("#btn-logout");
    if (btnLogout) {
      btnLogout.onclick = async () => {
        await bridge.logout();
        window.location.reload();
      };
    }
  }
}
