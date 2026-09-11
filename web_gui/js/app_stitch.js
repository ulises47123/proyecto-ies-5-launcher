/**
 * app_stitch.js — Controlador dinámico reactivo para Campus Virtual IES N°5
 * Responsabilidad única (SRP):
 * - Gestionar la interfaz de usuario web híbrida.
 * - Coordinar llamadas asíncronas con el puente Pyloid IPC (`bridge.js`).
 * - Formatear y renderizar materias, actividades pendientes, notas, directorio de contactos y chat de IA.
 */
import { bridge } from "./bridge.js";

export const appState = {
  usuario: null,
  cursos: [],
  pendientes: [],
  novedades: [],
  cursoActivo: null,
  programaCache: {},
  contactosCache: {},
  calificacionesCache: {},
  mensajesCache: {}
};

const CURSO_COLORS = [
  "#6366f1", "#06b6d4", "#10b981", "#8b5cf6", "#f59e0b", "#f43f5e", "#ec4899", "#3b82f6"
];

document.addEventListener("DOMContentLoaded", async () => {
  console.log("[AppStitch] Inicializando interfaz oficial v3.0...");

  // Restaurar tema visual guardado
  const savedTema = localStorage.getItem("campus_tema") || "midnight";
  aplicarTemaVisual(savedTema);

  setupEventListeners();

  // Intentar restaurar sesión de usuario de forma transparente
  try {
    const sesion = await bridge.restoreSession();
    if (sesion && sesion.ok) {
      console.log("[AppStitch] Sesión previa restaurada exitosamente.");
      const viewLogin = document.getElementById("view-login");
      if (viewLogin) viewLogin.classList.add("hidden");
      await cargarTodoElCampus();
      return;
    }
  } catch (err) {
    console.log("[AppStitch] Sin sesión transparente guardada:", err);
  }

  // Si no hay sesión previa activa, mostrar pantalla de inicio de sesión
  const viewLogin = document.getElementById("view-login");
  if (viewLogin) viewLogin.classList.remove("hidden");
});

function setupEventListeners() {
  // Formulario de Inicio de Sesión
  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.onsubmit = async (e) => {
      e.preventDefault();
      const errBox = document.getElementById("login-error");
      const btnSubmit = document.getElementById("btn-login-submit");
      if (errBox) errBox.classList.add("hidden");

      const u = document.getElementById("login-user").value.trim();
      const p = document.getElementById("login-pass").value;
      const recordar = document.getElementById("login-recordar") ? document.getElementById("login-recordar").checked : true;
      const autologin = document.getElementById("login-autologin") ? document.getElementById("login-autologin").checked : true;

      if (!u || !p) {
        if (errBox) {
          errBox.innerText = "Por favor, ingresá tu usuario y contraseña.";
          errBox.classList.remove("hidden");
        }
        return;
      }

      if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = `<span class="material-symbols-outlined text-[18px] animate-spin">sync</span><span>Conectando con el campus...</span>`;
      }

      try {
        const res = await bridge.login(u, p, recordar, autologin);
        if (res && res.ok) {
          const viewLogin = document.getElementById("view-login");
          if (viewLogin) viewLogin.classList.add("hidden");
          await cargarTodoElCampus();
        } else {
          if (errBox) {
            errBox.innerText = res?.error || "Usuario o clave incorrectos en la plataforma IES N°5.";
            errBox.classList.remove("hidden");
          }
        }
      } catch (error) {
        if (errBox) {
          errBox.innerText = "Error de conexión con el servidor: " + error.toString();
          errBox.classList.remove("hidden");
        }
      } finally {
        if (btnSubmit) {
          btnSubmit.disabled = false;
          btnSubmit.innerHTML = `<span>Ingresar al Campus</span><span class="material-symbols-outlined text-[18px]">arrow_forward</span>`;
        }
      }
    };
  }

  // Tecla ESC para cerrar modales
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeModal();
      const tutModal = document.getElementById("modal-tutorial");
      if (tutModal) tutModal.classList.add("hidden");
    }
  });

  const modalDetalle = document.getElementById("modal-detalle");
  if (modalDetalle) {
    modalDetalle.onclick = (e) => {
      if (e.target === modalDetalle) closeModal();
    };
  }
}

export function aplicarTemaVisual(tema) {
  const root = document.documentElement;
  root.setAttribute("data-theme", tema || "midnight");
  const selectTheme = document.getElementById("select-theme");
  if (selectTheme) selectTheme.value = tema || "midnight";
  localStorage.setItem("campus_tema", tema || "midnight");
}

export async function cargarTodoElCampus(forzar = false) {
  mostrarIndicadorCarga(true);
  switchTab("escritorio");

  try {
    // 1. Perfil del estudiante
    const profRes = await bridge.getProfile();
    if (profRes && profRes.ok && profRes.data) {
      appState.usuario = profRes.data;
      actualizarPerfilUI(profRes.data);
    }

    // 2. Materias y avisos del escritorio
    const curRes = await bridge.getCursos(forzar);
    if (curRes && curRes.ok && curRes.data) {
      appState.cursos = (curRes.data.cursos || []).map((c, idx) => ({
        ...c,
        color: CURSO_COLORS[idx % CURSO_COLORS.length]
      }));
      appState.novedades = curRes.data.novedades || [];

      if (curRes.data.usuario_nombre && (!appState.usuario || !appState.usuario.nombre)) {
        appState.usuario = {
          nombre: curRes.data.usuario_nombre,
          dni: appState.usuario?.dni || ""
        };
        actualizarPerfilUI(appState.usuario);
      }
    }

    // 3. Actividades pendientes de entrega
    try {
      const pendRes = await bridge.getPendientes();
      if (pendRes && pendRes.ok && pendRes.data) {
        const raw = pendRes.data;
        appState.pendientes = Array.isArray(raw) ? raw : (raw.actividades_pendientes || raw.pendientes || []);
      }
    } catch (e) {
      console.warn("No se pudieron cargar actividades pendientes:", e);
    }

    // 4. Renderizar componentes de UI
    poblarSelectorCursos();
    renderEstadisticasEscritorio();
    renderMaterias();
    renderPendientes();
    renderNovedades();
    actualizarBadgesSidebar();

    // Si hay un curso disponible, cargar directorio de contactos e información en segundo plano
    if (appState.cursos.length > 0) {
      const primerCursoId = appState.cursos[0].id;
      appState.cursoActivo = appState.cursos[0];
      cargarContactosCurso(primerCursoId);
      cargarCalificacionesCurso(primerCursoId);
    }

  } catch (err) {
    console.error("[AppStitch] Error al sincronizar el campus:", err);
  } finally {
    mostrarIndicadorCarga(false);
  }
}

function actualizarPerfilUI(u) {
  if (!u) return;

  const topUserSec = document.getElementById("topbar-user-section");
  const topName = document.getElementById("topbar-user-name");
  const topAvatar = document.getElementById("topbar-user-avatar");

  const sideName = document.getElementById("sidebar-user-name");
  const sideAvatar = document.getElementById("sidebar-user-avatar");
  const dashFirstname = document.getElementById("dash-user-firstname");
  const cfgUser = document.getElementById("cfg-user-info");

  const nombreCompleto = u.nombre || u.usuario || "Estudiante";
  const primerNombre = nombreCompleto.split(" ")[0];

  if (topName) topName.innerText = nombreCompleto;
  if (sideName) sideName.innerText = nombreCompleto;
  if (dashFirstname) dashFirstname.innerText = primerNombre;
  if (cfgUser) cfgUser.innerText = `${nombreCompleto} (${u.dni ? 'DNI: ' + u.dni : 'Activo'})`;

  if (topUserSec) topUserSec.classList.remove("hidden");

  if (u.foto_url) {
    if (topAvatar) topAvatar.src = u.foto_url;
    if (sideAvatar) sideAvatar.src = u.foto_url;
  }
}

function poblarSelectorCursos() {
  const dropdown = document.getElementById("curso-dropdown");
  if (!dropdown) return;

  if (appState.cursos.length === 0) {
    dropdown.innerHTML = `<option value="">Sin materias inscriptas</option>`;
    return;
  }

  dropdown.innerHTML = appState.cursos.map(c => `
    <option value="${c.id}">${c.nombre}</option>
  `).join("");
}

function actualizarBadgesSidebar() {
  const badgeMat = document.getElementById("badge-materias-count");
  const badgePend = document.getElementById("badge-actividades-count");

  if (badgeMat) badgeMat.innerText = appState.cursos.length;
  if (badgePend) badgePend.innerText = appState.pendientes.length;
}

export function switchTab(tabName) {
  // Ocultar todos los contenedores de pestañas
  const tabs = document.querySelectorAll(".tab-content");
  tabs.forEach(t => t.classList.add("hidden"));

  // Mostrar el contenedor seleccionado
  const targetTab = document.getElementById(`tab-${tabName}`);
  if (targetTab) targetTab.classList.remove("hidden");

  // Desactivar estilo activo de todos los botones de la barra lateral
  const navBtns = document.querySelectorAll(".nav-btn");
  navBtns.forEach(btn => {
    btn.className = "nav-btn w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-midnight-card transition-all cursor-pointer";
  });

  // Activar estilo en el botón seleccionado
  const activeBtn = document.getElementById(`btn-nav-${tabName}`);
  if (activeBtn) {
    activeBtn.className = "nav-btn w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold text-indigo-400 bg-indigo-500/10 border border-indigo-500/30 shadow-sm transition-all cursor-pointer";
  }

  // Carga diferida de datos según la pestaña activa
  if (tabName === "novedades" && appState.novedades.length === 0) {
    cargarSitioNoticias();
  }
}

function renderEstadisticasEscritorio() {
  const statMat = document.getElementById("dash-stat-materias");
  const statPend = document.getElementById("dash-stat-pendientes");
  const statNov = document.getElementById("dash-stat-novedades");

  if (statMat) statMat.innerText = appState.cursos.length;
  if (statPend) statPend.innerText = appState.pendientes.length;
  if (statNov) statNov.innerText = appState.novedades.length;
}

// 1. Renderizar Materias
export function renderMaterias() {
  const container = document.getElementById("curso-programa-container");
  if (!container) return;

  if (appState.cursos.length === 0) {
    container.innerHTML = `
      <div class="p-8 text-center bg-midnight-card border border-midnight-border rounded-2xl">
        <span class="material-symbols-outlined text-slate-500 text-4xl mb-2">menu_book</span>
        <h4 class="text-sm font-bold text-white">No hay materias registradas</h4>
        <p class="text-xs text-slate-400 mt-1">Presioná "Sincronizar" en la barra superior para actualizar tu cursada.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = appState.cursos.map((c) => {
    const avance = c.avance !== undefined ? c.avance : 70;
    const ultAcceso = c.ultimo_acceso || "Reciente";
    const novedadTxt = c.no_leidos ? `${c.no_leidos} sin leer` : "Al día";

    return `
      <div class="glass-card-interactive p-5 rounded-2xl space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="w-3 h-3 rounded-full" style="background-color: ${c.color}"></span>
            <span class="text-xs font-bold text-white">${c.nombre}</span>
          </div>
          <span class="text-[10px] font-mono text-slate-400">Acceso: ${ultAcceso}</span>
        </div>
        <div class="flex items-center justify-between text-xs text-slate-300">
          <span>Estado: <strong class="text-indigo-400">${novedadTxt}</strong></span>
          <span class="font-bold text-emerald-400">${avance}% completado</span>
        </div>
        <div class="w-full bg-midnight-base rounded-full h-2 overflow-hidden border border-midnight-border">
          <div class="bg-gradient-to-r from-indigo-500 to-cyan-400 h-2 rounded-full" style="width: ${avance}%"></div>
        </div>
      </div>
    `;
  }).join("");
}

// 2. Renderizar Actividades Pendientes
export function renderPendientes() {
  const containerDash = document.getElementById("dash-list-pendientes");
  const containerTab = document.getElementById("actividades-container");

  if (appState.pendientes.length === 0) {
    const emptyHtml = `
      <div class="p-6 text-center text-slate-400 text-xs">
        <span class="material-symbols-outlined text-emerald-400 text-3xl mb-1 block">task_alt</span>
        <span>¡Felicitaciones! No tenés entregas pendientes.</span>
      </div>
    `;
    if (containerDash) containerDash.innerHTML = emptyHtml;
    if (containerTab) containerTab.innerHTML = emptyHtml;
    return;
  }

  const itemsHtml = appState.pendientes.map((p) => {
    const vencida = p.vencida || false;
    const badgeStyle = vencida ? "bg-rose-500/20 text-rose-300 border-rose-500/40" : "bg-amber-500/20 text-amber-300 border-amber-500/40";
    const plazo = p.tiempo_restante_str || p.fecha_limite || "Consultar en el aula";

    return `
      <div class="p-4 rounded-2xl bg-midnight-card border border-midnight-border space-y-2 hover:border-indigo-500/40 transition-all">
        <div class="flex items-center justify-between gap-2">
          <span class="text-xs font-bold text-indigo-400 truncate">${p.curso_nombre || "Materia"}</span>
          <span class="px-2.5 py-0.5 rounded-full border text-[10px] font-bold ${badgeStyle}">
            ${vencida ? "Vencida" : "Pendiente"}
          </span>
        </div>
        <h4 class="text-xs font-bold text-white">${p.titulo || "Consigna de Trabajo Práctico"}</h4>
        <div class="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-1">
          <span>Fecha Límite: ${plazo}</span>
          <button onclick="verDetalleItem('${encodeURIComponent(p.titulo || '')}', '${encodeURIComponent(p.fecha_limite || '')}')" class="text-indigo-400 hover:text-indigo-300 font-bold cursor-pointer">Ver consingna &rarr;</button>
        </div>
      </div>
    `;
  }).join("");

  if (containerDash) containerDash.innerHTML = itemsHtml;
  if (containerTab) containerTab.innerHTML = itemsHtml;
}

// 3. Renderizar Novedades del Aula
export function renderNovedades() {
  const container = document.getElementById("dash-list-novedades");
  if (!container) return;

  if (appState.novedades.length === 0) {
    container.innerHTML = `<div class="p-6 text-center text-slate-400 text-xs">Sin avisos nuevos en el aula virtual.</div>`;
    return;
  }

  container.innerHTML = appState.novedades.map((n) => `
    <div class="p-3.5 rounded-2xl bg-midnight-base border border-midnight-border space-y-1">
      <div class="flex items-center justify-between">
        <span class="text-[11px] font-bold text-indigo-400">${n.nombre_curso || "Aviso"}</span>
        <span class="text-[10px] text-slate-500 font-mono">${n.fecha || ""}</span>
      </div>
      <h5 class="text-xs font-bold text-white">${n.nombre_item || n.titulo || "Publicación"}</h5>
      <p class="text-[11px] text-slate-300 line-clamp-2">${n.resumen || "Ingresá al aula para leer el comunicado completo."}</p>
    </div>
  `).join("");
}

// 4. Directorio de Contactos
async function cargarContactosCurso(cursoId) {
  const container = document.getElementById("curso-contactos-container");
  if (!container) return;

  try {
    const res = await bridge.getContactos(cursoId);
    if (res && res.ok && res.data) {
      const miembros = res.data.contactos || res.data || [];
      appState.contactosCache[cursoId] = miembros;
      renderContactos(miembros);
    }
  } catch (err) {
    console.warn("Error cargando contactos:", err);
  }
}

function renderContactos(miembros) {
  const container = document.getElementById("curso-contactos-container");
  if (!container) return;

  if (!miembros || miembros.length === 0) {
    container.innerHTML = `<div class="col-span-full p-8 text-center text-slate-400 text-xs">No hay miembros en el directorio de esta materia.</div>`;
    return;
  }

  container.innerHTML = miembros.map(m => {
    const esDocente = (m.rol || "").toLowerCase().includes("docente") || (m.tipo || "").toLowerCase().includes("profesor");
    const badgeRole = esDocente ? "bg-purple-500/20 text-purple-300 border-purple-500/40" : "bg-cyan-500/20 text-cyan-300 border-cyan-500/40";
    const foto = m.foto_url || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z'/%3E%3C/svg%3E";

    return `
      <div class="glass-card-interactive p-4 rounded-2xl flex items-center gap-3.5">
        <img src="${foto}" alt="${m.nombre}" class="w-12 h-12 rounded-full border border-midnight-bright object-cover bg-slate-800 shrink-0">
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 mb-1">
            <span class="px-2 py-0.5 rounded-full border text-[9px] font-bold uppercase ${badgeRole}">
              ${esDocente ? 'Docente' : 'Alumno'}
            </span>
          </div>
          <h5 class="text-xs font-bold text-white truncate">${m.nombre}</h5>
          <span class="text-[10px] text-slate-400 truncate block">${m.email || 'Campus IES N°5'}</span>
        </div>
      </div>
    `;
  }).join("");
}

// 5. Registro de Calificaciones
async function cargarCalificacionesCurso(cursoId) {
  const container = document.getElementById("calificaciones-container");
  if (!container) return;

  try {
    const res = await bridge.getCalificaciones(cursoId);
    if (res && res.ok && res.data) {
      const notas = res.data.calificaciones || res.data || [];
      renderCalificaciones(notas);
    }
  } catch (err) {
    console.warn("Error cargando calificaciones:", err);
  }
}

function renderCalificaciones(notas) {
  const container = document.getElementById("calificaciones-container");
  if (!container) return;

  if (!notas || notas.length === 0) {
    container.innerHTML = `<div class="p-8 text-center text-slate-400 text-xs">No hay notas registradas para esta materia.</div>`;
    return;
  }

  container.innerHTML = notas.map(n => `
    <div class="p-4 rounded-2xl bg-midnight-card border border-midnight-border flex items-center justify-between">
      <div>
        <h5 class="text-xs font-bold text-white">${n.evaluacion || n.titulo || 'Evaluación'}</h5>
        <span class="text-[10px] text-slate-400 font-mono">Fecha: ${n.fecha || 'Reciente'}</span>
      </div>
      <div class="text-right">
        <span class="text-lg font-extrabold text-emerald-400 font-mono">${n.nota || 'Aprobado'}</span>
        <span class="block text-[10px] text-slate-400">${n.estado || 'Calificado'}</span>
      </div>
    </div>
  `).join("");
}

// 6. Sitio Noticias Oficiales
async function cargarSitioNoticias() {
  const container = document.getElementById("sitio-noticias-container");
  if (!container) return;

  container.innerHTML = `<div class="col-span-full p-8 text-center text-slate-400 text-xs"><span class="material-symbols-outlined animate-spin text-xl mr-2">sync</span>Cargando publicaciones del sitio oficial...</div>`;

  try {
    const res = await bridge.getSitioNoticias();
    if (res && res.ok && res.data) {
      const noticias = res.data.noticias || res.data || [];
      if (noticias.length === 0) {
        container.innerHTML = `<div class="col-span-full p-8 text-center text-slate-400 text-xs">No se encontraron noticias recientes.</div>`;
        return;
      }

      container.innerHTML = noticias.map(n => `
        <div class="glass-card-interactive p-5 rounded-2xl space-y-3">
          <span class="text-[10px] font-mono text-indigo-400">${n.fecha || 'Comunicado Oficial'}</span>
          <h4 class="text-xs font-bold text-white leading-snug">${n.titulo}</h4>
          <p class="text-[11px] text-slate-300 leading-relaxed line-clamp-3">${n.resumen || ''}</p>
          ${n.url ? `<a href="${n.url}" target="_blank" class="inline-block text-indigo-400 hover:text-indigo-300 font-bold text-[11px]">Leer completo &rarr;</a>` : ''}
        </div>
      `).join("");
    }
  } catch (err) {
    container.innerHTML = `<div class="col-span-full p-8 text-center text-rose-400 text-xs">Error al cargar noticias institucionales.</div>`;
  }
}

// 7. Chat con IA Gemini
export async function sendIAMsg(q) {
  const logs = document.getElementById("ia-chat-messages");
  if (!logs) return;

  // Mensaje del usuario
  logs.innerHTML += `
    <div class="flex gap-3 items-start justify-end">
      <div class="bg-gradient-to-r from-indigo-600 to-violet-600 p-3.5 rounded-2xl text-xs text-white max-w-lg shadow-md font-sans">
        ${q}
      </div>
    </div>
  `;
  logs.scrollTop = logs.scrollHeight;

  // Indicador de procesamiento
  const thinkingId = "ia-thinking-" + Date.now();
  logs.innerHTML += `
    <div id="${thinkingId}" class="flex gap-3 items-start">
      <div class="w-8 h-8 rounded-full bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 flex items-center justify-center shrink-0">
        <span class="material-symbols-outlined text-[18px]">smart_toy</span>
      </div>
      <div class="p-3.5 rounded-2xl bg-midnight-card border border-midnight-border text-xs text-slate-300 max-w-lg flex items-center gap-2">
        <span class="material-symbols-outlined text-sm animate-spin text-cyan-400">sync</span>
        <span>Consultando el Campus Virtual...</span>
      </div>
    </div>
  `;
  logs.scrollTop = logs.scrollHeight;

  try {
    const res = await bridge.askIA(q);
    const thinkingEl = document.getElementById(thinkingId);
    if (thinkingEl) thinkingEl.remove();

    const respText = res?.data?.respuesta || res?.respuesta || res?.data || "No pude obtener una respuesta del servidor.";

    logs.innerHTML += `
      <div class="flex gap-3 items-start">
        <div class="w-8 h-8 rounded-full bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 flex items-center justify-center shrink-0">
          <span class="material-symbols-outlined text-[18px]">smart_toy</span>
        </div>
        <div class="p-4 rounded-2xl bg-midnight-card border border-midnight-border text-xs text-slate-200 max-w-xl leading-relaxed shadow-md space-y-2">
          ${respText.replace(/\n/g, '<br>')}
        </div>
      </div>
    `;
    logs.scrollTop = logs.scrollHeight;
  } catch (err) {
    const thinkingEl = document.getElementById(thinkingId);
    if (thinkingEl) thinkingEl.remove();

    logs.innerHTML += `
      <div class="flex gap-3 items-start">
        <div class="w-8 h-8 rounded-full bg-rose-500/20 border border-rose-500/40 text-rose-300 flex items-center justify-center shrink-0">
          <span class="material-symbols-outlined text-[18px]">error</span>
        </div>
        <div class="p-3.5 rounded-2xl bg-midnight-card border border-rose-500/30 text-xs text-rose-300 max-w-lg">
          Error en la consulta: ${err.toString()}
        </div>
      </div>
    `;
    logs.scrollTop = logs.scrollHeight;
  }
}

// Global Modal Control
export function verDetalleItem(titulo, detalle) {
  const titEl = document.getElementById("modal-tit");
  const bodyEl = document.getElementById("modal-body");
  const modalEl = document.getElementById("modal-detalle");

  if (titEl) titEl.innerText = decodeURIComponent(titulo);
  if (bodyEl) bodyEl.innerText = decodeURIComponent(detalle);
  if (modalEl) modalEl.classList.remove("hidden");
}

export function closeModal() {
  const modalEl = document.getElementById("modal-detalle");
  if (modalEl) modalEl.classList.add("hidden");
}

// Funciones globales expuestas al ámbito window
window.switchTab = switchTab;
window.aplicarTemaVisual = aplicarTemaVisual;
window.forzarSincronizacion = async () => await cargarTodoElCampus(true);
window.cerrarSesion = async () => {
  if (confirm("¿Seguro que querés cerrar la sesión?")) {
    try { await bridge.logout(); } catch(e){}
    appState.usuario = null;
    document.getElementById("topbar-user-section")?.classList.add("hidden");
    document.getElementById("view-login")?.classList.remove("hidden");
  }
};
window.cambiarCursoActivo = (cursoId) => {
  const c = appState.cursos.find(x => String(x.id) === String(cursoId));
  if (c) {
    appState.cursoActivo = c;
    cargarContactosCurso(c.id);
    cargarCalificacionesCurso(c.id);
  }
};
window.usarPromptChip = (txt) => {
  const inp = document.getElementById("ia-chat-input");
  if (inp) {
    inp.value = txt;
    document.getElementById("ia-chat-form")?.requestSubmit();
  }
};
window.enviarMensajeIA = async (e) => {
  e.preventDefault();
  const inp = document.getElementById("ia-chat-input");
  if (!inp) return;
  const q = inp.value.trim();
  if (!q) return;
  inp.value = "";
  await sendIAMsg(q);
};
window.guardarAjustes = async () => {
  const key = document.getElementById("cfg-gemini-key")?.value.trim();
  if (key) {
    try {
      await bridge.saveConfig(JSON.stringify({ gemini_api_key: key }));
      alert("Clave API guardada con éxito.");
    } catch(e) {
      alert("Configuración actualizada.");
    }
  }
};
window.verDetalleItem = verDetalleItem;
window.closeModal = closeModal;
