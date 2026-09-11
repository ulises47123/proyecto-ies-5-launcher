import { bridge } from "./bridge.js";
import { state } from "./state.js";
import { ServerBar } from "./components/server_bar.js";
import { ChannelList } from "./components/channel_list.js";
import { UserPanel } from "./components/user_panel.js";
import { MemberList } from "./components/member_list.js";
import { MainContent } from "./components/main_content.js";

document.addEventListener("DOMContentLoaded", async () => {
  console.log("[App] Inicializando Frontend Web estilo Discord...");

  // Instanciar componentes
  new ServerBar("server-list");
  new ChannelList("channel-list");
  new UserPanel("user-panel");
  new MemberList("member-list");
  new MainContent("view-container");

  // Toggle Member List
  const btnToggleMembers = document.getElementById("btn-toggle-members");
  const memberSidebar = document.getElementById("member-sidebar");
  if (btnToggleMembers && memberSidebar) {
    btnToggleMembers.onclick = () => {
      memberSidebar.classList.toggle("hidden");
    };
  }

  // Verificar sesión y autenticación
  await initSessionFlow();
});

async function initSessionFlow() {
  const modal = document.getElementById("login-modal");
  const form = document.getElementById("login-form");
  const errBox = document.getElementById("login-error");

  // 1. Intentar restaurar sesión guardada
  const rest = await bridge.restoreSession();
  if (rest && rest.ok) {
    console.log("[App] Sesión restaurada con éxito:", rest);
    modal.classList.add("hidden");
    await loadInitialData();
    return;
  }

  // 2. Si no hay sesión, mostrar modal de login
  modal.classList.remove("hidden");

  form.onsubmit = async (e) => {
    e.preventDefault();
    errBox.classList.add("hidden");
    const u = document.getElementById("login-user").value;
    const p = document.getElementById("login-pass").value;
    const r = document.getElementById("login-recordar").checked;
    const a = document.getElementById("login-autologin").checked;

    const res = await bridge.login(u, p, r, a);
    if (res && res.ok) {
      modal.classList.add("hidden");
      await loadInitialData();
    } else {
      errBox.innerText = res?.error || "Usuario o clave incorrectos.";
      errBox.classList.remove("hidden");
    }
  };
}

async function loadInitialData() {
  // Cargar perfil
  const prof = await bridge.getProfile();
  if (prof && prof.ok) {
    state.setUser(prof.data);
  }

  // Cargar cursos
  const cur = await bridge.getCursos();
  if (cur && cur.ok) {
    state.setCursos(cur.data.cursos || []);
    if (cur.data.cursos && cur.data.cursos.length > 0) {
      state.selectCurso(cur.data.cursos[0]);
    }
  }
}
