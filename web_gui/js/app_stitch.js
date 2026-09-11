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

// Helper global para evitar mostrar "null" en la interfaz
function cleanText(val, fallback = "—") {
  if (val === null || val === undefined || val === "null" || val === "undefined") return fallback;
  const s = String(val).trim();
  return s ? s : fallback;
}

/**
 * fmtFecha — Convierte "YYYY MM DD HH MM" (formato campus Educativa) a "DD/MM/YYYY HH:MM".
 * Si no coincide con ese formato, devuelve el valor original sin modificar.
 * @param {string} fechaStr
 * @returns {string}
 */
function fmtFecha(fechaStr) {
  if (!fechaStr) return "—";
  const s = String(fechaStr).trim();
  // Formato campus: "2026 08 18 20 51"
  const m = s.match(/^(\d{4})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})$/);
  if (m) {
    const [, yyyy, mm, dd, hh, min] = m;
    return `${dd.padStart(2,"0")}/${mm.padStart(2,"0")}/${yyyy} ${hh.padStart(2,"0")}:${min.padStart(2,"0")}`;
  }
  // Try to parse as standard Date if not matched
  const d = new Date(s);
  if (!isNaN(d.getTime())) {
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yyyy = d.getFullYear();
    const hh = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${dd}/${mm}/${yyyy} ${hh}:${min}`;
  }
  return s;
}

/**
 * edadRelativa — Convierte "YYYY MM DD HH MM" a descripción relativa ("hace 3 días", etc.)
 * @param {string} fechaStr
 * @returns {string}
 */
function edadRelativa(fechaStr) {
  if (!fechaStr) return "—";
  const s = String(fechaStr).trim();
  const m = s.match(/^(\d{4})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})$/);
  if (!m) return s;
  const [, yyyy, mm, dd, hh, min] = m;
  const dt = new Date(Number(yyyy), Number(mm) - 1, Number(dd), Number(hh), Number(min));
  const diff = Math.floor((Date.now() - dt.getTime()) / 1000);
  if (diff < 60) return "hace un momento";
  if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `hace ${Math.floor(diff / 3600)}h`;
  const dias = Math.floor(diff / 86400);
  if (dias === 1) return "ayer";
  if (dias < 7) return `hace ${dias} días`;
  if (dias < 30) return `hace ${Math.floor(dias / 7)} semana(s)`;
  if (dias < 365) return `hace ${Math.floor(dias / 30)} mes(es)`;
  return `hace ${Math.floor(dias / 365)} año(s)`;
}

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
      
      if (sesion.data && sesion.data.profile) {
        appState.usuario = sesion.data.profile;
        actualizarPerfilUI(sesion.data.profile);
      }
      
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

          // Actualizar datos de usuario inmediatamente desde el resultado de login
          if (res.data) {
            appState.usuario = {
              nombre: res.data.nombre || res.data.profile?.nombre || u,
              dni: res.data.usuario || u,
              foto_url: res.data.profile?.foto_url || ""
            };
            actualizarPerfilUI(appState.usuario);
          }

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
  const targetTema = tema || "midnight";
  if (root.getAttribute("data-theme") !== targetTema) {
    root.setAttribute("data-theme", targetTema);
    localStorage.setItem("campus_tema", targetTema);
  }
  const selectTheme = document.getElementById("select-theme");
  if (selectTheme && selectTheme.value !== targetTema) selectTheme.value = targetTema;
}

export async function cargarTodoElCampus(forzar = false) {
  mostrarIndicadorCarga(true);

  try {
    // 1. Perfil del estudiante
    const profRes = await bridge.getProfile();
    if (profRes && profRes.ok && profRes.data) {
      appState.usuario = {
        ...appState.usuario,
        ...profRes.data
      };
      actualizarPerfilUI(appState.usuario);
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
          ...appState.usuario,
          nombre: curRes.data.usuario_nombre
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
    renderCalificacionesGenerales();

    // Si hay un curso disponible, seleccionar el primero y cargar sus datos
    if (appState.cursos.length > 0) {
      const primerCurso = appState.cursos[0];
      appState.cursoActivo = primerCurso;
      const nombreEl = document.getElementById("curso-detail-nombre");
      if (nombreEl) nombreEl.innerText = primerCurso.nombre;
      cargarProgramaCurso(primerCurso.id);
      cargarContactosCurso(primerCurso.id);
      cargarCalificacionesCurso(primerCurso.id);
    }

  } catch (err) {
    console.error("[AppStitch] Error al sincronizar el campus:", err);
  } finally {
    mostrarIndicadorCarga(false);
  }
}

async function cargarImagenAutenticada(url, nombre, imgElementsArray) {
  // Intentaremos los 4 métodos secuencialmente.
  // 1: Base64 en línea, 2: Archivo Local Caché, 3: Inyección de Cookies, 4: SVG Iniciales Dinámico
  for (let metodo = 1; metodo <= 4; metodo++) {
    try {
      const res = await bridge.resolveImage(url, nombre, metodo);
      if (res && res.ok && res.data) {
        if (typeof res.data === 'string') {
          imgElementsArray.forEach(img => { if(img) img.src = res.data; });
          return; // Éxito con M1, M2 o M4
        } else if (res.data.type === 'cookie_inject') {
          // Método 3: setear cookies y usar src nativo
          document.cookie = res.data.cookie_string;
          imgElementsArray.forEach(img => { if(img) img.src = url; });
          return;
        }
      }
    } catch(err) {
      console.warn(`[ImageService] Falló método ${metodo} para la imagen. Probando el siguiente...`);
    }
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

  const nombreCompleto = cleanText(u.nombre || u.usuario, "Estudiante");
  const primerNombre = nombreCompleto.split(" ")[0];

  if (topName) topName.innerText = nombreCompleto;
  if (sideName) sideName.innerText = nombreCompleto;
  if (dashFirstname) dashFirstname.innerText = primerNombre;
  if (cfgUser) cfgUser.innerText = `${nombreCompleto} (${u.dni ? 'DNI: ' + u.dni : 'Activo'})`;

  if (topUserSec) topUserSec.classList.remove("hidden");

  // Iniciar la carga de la imagen con los 4 métodos de contingencia
  cargarImagenAutenticada(u.foto_url, nombreCompleto, [topAvatar, sideAvatar]);
}

function poblarSelectorCursos() {
  const dropdown = document.getElementById("curso-dropdown");
  if (!dropdown) return;

  if (appState.cursos.length === 0) {
    dropdown.innerHTML = `<option value="">Sin materias inscriptas</option>`;
    return;
  }

  dropdown.innerHTML = appState.cursos.map(c => `
    <option value="${c.id}">${cleanText(c.nombre, 'Materia')}</option>
  `).join("");
}

function actualizarBadgesSidebar() {
  const badgeMat = document.getElementById("badge-materias-count");
  const badgePend = document.getElementById("badge-actividades-count");

  if (badgeMat) badgeMat.innerText = appState.cursos.length;
  if (badgePend) badgePend.innerText = appState.pendientes.length;
}

export function switchTab(tabName) {
  // Ocultar todos los contenedores de pestañas instantáneamente sin reflow
  const tabs = document.querySelectorAll(".tab-content");
  tabs.forEach(t => {
    if (!t.classList.contains("hidden")) t.classList.add("hidden");
  });

  // Mostrar el contenedor seleccionado
  const targetTab = document.getElementById(`tab-${tabName}`);
  if (targetTab) targetTab.classList.remove("hidden");

  // Desactivar estilo activo de todos los botones de la barra lateral
  const navBtns = document.querySelectorAll(".nav-btn");
  navBtns.forEach(btn => {
    btn.className = "nav-btn w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-midnight-card transition-colors cursor-pointer";
  });

  // Activar estilo en el botón seleccionado
  const activeBtn = document.getElementById(`btn-nav-${tabName}`);
  if (activeBtn) {
    activeBtn.className = "nav-btn w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold text-indigo-400 bg-indigo-500/10 border border-indigo-500/30 shadow-sm transition-colors cursor-pointer";
  }

  // Carga diferida de datos según la pestaña activa
  if (tabName === "novedades") {
    // Siempre re-renderizar las novedades del campus al abrir el tab
    renderNovedades();
    // Cargar noticias institucionales del sitio si no estaban cargadas
    cargarSitioNoticias();
  } else if (tabName === "calificaciones") {
    renderCalificacionesGenerales();
  }
}

export function switchCursoSubtab(subtabName) {
  // Alternar sub-pestañas dentro del detalle de la materia (Programa, Miembros, Calificaciones)
  const subtabs = document.querySelectorAll(".subtab-content");
  subtabs.forEach(st => st.classList.add("hidden"));

  const targetSubtab = document.getElementById(`subtab-${subtabName}`);
  if (targetSubtab) targetSubtab.classList.remove("hidden");

  // Actualizar estilos de los botones de sub-pestaña
  ["programa", "contactos", "calificaciones"].forEach(st => {
    const btn = document.getElementById(`btn-subtab-${st}`);
    if (btn) {
      if (st === subtabName) {
        btn.className = "px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 text-white shadow-sm transition-all cursor-pointer";
      } else {
        btn.className = "px-3 py-1.5 rounded-lg text-xs font-bold text-slate-400 hover:text-white transition-all cursor-pointer";
      }
    }
  });

  // Cargar datos diferidos si se selecciona la sub-pestaña de miembros o calificaciones
  if (appState.cursoActivo) {
    if (subtabName === "contactos") {
      cargarContactosCurso(appState.cursoActivo.id);
    } else if (subtabName === "calificaciones") {
      cargarCalificacionesCurso(appState.cursoActivo.id);
    }
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

// 1. Renderizar Materias en Escritorio y Pestaña de Materias
export function renderMaterias() {
  const containerDash = document.getElementById("dash-grid-materias");
  const containerTab = document.getElementById("materias-grid");

  if (appState.cursos.length === 0) {
    const emptyHtml = `
      <div class="col-span-full p-8 text-center bg-midnight-card border border-midnight-border rounded-2xl">
        <span class="material-symbols-outlined text-slate-500 text-4xl mb-2">menu_book</span>
        <h4 class="text-sm font-bold text-white">No hay materias registradas</h4>
        <p class="text-xs text-slate-400 mt-1">Presioná "Sincronizar" en la barra superior para actualizar tu cursada.</p>
      </div>
    `;
    if (containerDash) containerDash.innerHTML = emptyHtml;
    if (containerTab) containerTab.innerHTML = emptyHtml;
    return;
  }

  /**
   * buildCard — Genera HTML de tarjeta para una materia.
   * @param {Object} c — curso del appState
   * @param {boolean} enTab — true si está dentro de la pestaña de materias (sólo scroll, sin cambio de tab)
   */
  const buildCard = (c, enTab = false) => {
    const avance = c.avance !== undefined && c.avance !== null ? c.avance : 70;
    const ultAcceso = cleanText(c.ultimo_acceso, "Reciente");
    const novedadTxt = c.items_obl ? `${c.items_obl} actividades` : "Al día";
    const nomMat = cleanText(c.nombre, "Materia");
    const esActivo = appState.cursoActivo && String(appState.cursoActivo.id) === String(c.id);
    const borderClass = esActivo ? "border-2 border-indigo-500 bg-indigo-500/10 shadow-lg shadow-indigo-500/20" : "border border-midnight-border";
    // Desde el dashboard: switchTab('materias') primero, luego scroll al detalle.
    // Desde la pestaña de materias: sólo cambiarCursoActivo() que ya hace scroll.
    const clickAction = enTab
      ? `cambiarCursoActivo('${c.id}')`
      : `switchTab('materias'); cambiarCursoActivo('${c.id}')`;

    return `
      <div onclick="${clickAction}" class="glass-card-interactive p-5 rounded-2xl space-y-3 cursor-pointer ${borderClass} transition-all">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="w-3.5 h-3.5 rounded-full shadow-sm shrink-0" style="background-color: ${c.color}"></span>
            <span class="text-xs font-bold text-white leading-snug">${nomMat}</span>
          </div>
          ${esActivo ? `<span class="px-2 py-0.5 rounded-full bg-indigo-500 text-white text-[9px] font-extrabold uppercase shrink-0">Activa</span>` : ''}
        </div>
        <div class="flex items-center justify-between text-xs text-slate-300">
          <span>Estado: <strong class="text-indigo-400">${novedadTxt}</strong></span>
          <span class="font-bold text-emerald-400">${avance}% completado</span>
        </div>
        <div class="w-full bg-midnight-base rounded-full h-2 overflow-hidden border border-midnight-border">
          <div class="bg-gradient-to-r from-indigo-500 to-cyan-400 h-2 rounded-full" style="width: ${avance}%"></div>
        </div>
        <div class="pt-2 flex justify-between items-center text-[10px] text-slate-400 font-mono">
          <span>Acceso: ${ultAcceso}</span>
          <span class="px-3 py-1.5 ${esActivo ? 'bg-indigo-500 text-white' : 'bg-indigo-600/80 hover:bg-indigo-500 text-white'} rounded-xl text-xs font-bold transition-all">
            ${esActivo ? 'Viendo clases ✓' : 'Ver clases &rarr;'}
          </span>
        </div>
      </div>
    `;
  };

  if (containerDash) containerDash.innerHTML = appState.cursos.map(c => buildCard(c, false)).join("");
  if (containerTab)  containerTab.innerHTML  = appState.cursos.map(c => buildCard(c, true)).join("");
}

// Cargar programa desglosado por unidades e ítems/clases de la materia activa
async function cargarProgramaCurso(cursoId) {
  const container = document.getElementById("curso-programa-container");
  if (!container) return;

  container.innerHTML = `<div class="p-8 text-center text-slate-400 text-xs"><span class="material-symbols-outlined animate-spin text-xl mr-2">sync</span>Cargando clases y contenido de la asignatura...</div>`;

  try {
    const res = await bridge.getPrograma(cursoId);
    if (res && res.ok && res.data) {
      const unidades = res.data.unidades || res.data || [];
      if (!Array.isArray(unidades) || unidades.length === 0) {
        container.innerHTML = `<div class="p-8 text-center text-slate-400 text-xs">No hay clases ni recursos publicados en esta materia.</div>`;
        return;
      }

      container.innerHTML = unidades.map((u, idx) => {
        const itemsList = Array.isArray(u.items) ? u.items : [];
        const itemsHtml = itemsList.length > 0 ? itemsList.map(item => {
          const tipo = (item.tipo || "").toLowerCase();
          let icon = "article";
          let iconColor = "text-slate-400";
          if (tipo.includes("actividad")) { icon = "edit_note"; iconColor = "text-amber-400"; }
          else if (tipo.includes("archivo")) { icon = "attach_file"; iconColor = "text-cyan-400"; }
          else if (tipo.includes("texto")) { icon = "description"; iconColor = "text-indigo-400"; }
          else if (tipo.includes("link")) { icon = "link"; iconColor = "text-emerald-400"; }

          const tituloStr = cleanText(item.titulo || item.nombre, "Clase / Recurso");
          const tipoDescStr = cleanText(item.tipo_desc || item.tipo, "Recurso pedagógico");
          const urlStr = item.url || item.href || "";

          return `
            <div class="p-3 rounded-xl bg-midnight-base/80 border border-midnight-border/60 flex items-center justify-between gap-3 hover:border-indigo-500/40 transition-all">
              <div class="flex items-center gap-3 min-w-0">
                <span class="material-symbols-outlined text-[20px] ${iconColor} shrink-0">${icon}</span>
                <div class="min-w-0">
                  <h5 class="text-xs font-semibold text-white truncate">${tituloStr}</h5>
                  <span class="text-[10px] text-slate-400 block">${tipoDescStr}</span>
                </div>
              </div>
              ${urlStr ? `
                <button onclick="verDetalleItem('${encodeURIComponent(tituloStr)}', '${encodeURIComponent(urlStr)}')" class="px-2.5 py-1 bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 border border-indigo-500/40 rounded-lg text-[10px] font-bold shrink-0 transition-colors cursor-pointer">
                  Ver detalle &rarr;
                </button>
              ` : ''}
            </div>
          `;
        }).join("") : `<div class="text-[11px] text-slate-400 italic p-2">Material pedagógico de la unidad.</div>`;

        return `
          <div class="p-4.5 rounded-2xl bg-midnight-card border border-midnight-border space-y-3">
            <div class="flex items-center justify-between border-b border-midnight-border/60 pb-2.5">
              <h4 class="text-xs font-bold text-white flex items-center gap-2">
                <span class="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-[10px] font-mono border border-indigo-500/30">Unidad ${idx + 1}</span>
                <span>${cleanText(u.nombre || u.titulo, 'Contenido Temático')}</span>
              </h4>
            </div>
            ${u.descripcion ? `<p class="text-[11px] text-slate-300 leading-relaxed">${cleanText(u.descripcion, '')}</p>` : ''}
            <div class="space-y-2 pt-1">
              ${itemsHtml}
            </div>
          </div>
        `;
      }).join("");
    } else {
      container.innerHTML = `<div class="p-8 text-center text-slate-400 text-xs">No se pudieron obtener las clases de la materia.</div>`;
    }
  } catch (err) {
    console.error("Error cargando programa de curso:", err);
    container.innerHTML = `<div class="p-8 text-center text-slate-400 text-xs">No se pudieron obtener las clases de la materia.</div>`;
  }
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
    const plazo = cleanText(p.tiempo_restante_str || p.fecha_limite, "Consultar en el aula");

    return `
      <div class="p-4 rounded-2xl bg-midnight-card border border-midnight-border space-y-2 hover:border-indigo-500/40 transition-all">
        <div class="flex items-center justify-between gap-2">
          <span class="text-xs font-bold text-indigo-400 truncate">${cleanText(p.curso_nombre, "Materia")}</span>
          <span class="px-2.5 py-0.5 rounded-full border text-[10px] font-bold ${badgeStyle}">
            ${vencida ? "Vencida" : "Pendiente"}
          </span>
        </div>
        <h4 class="text-xs font-bold text-white">${cleanText(p.titulo, "Consigna de Trabajo Práctico")}</h4>
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
  const containerDash = document.getElementById("dash-list-novedades");
  const containerTab  = document.getElementById("tab-novedades-list");

  const TIPO_ICON = {
    "email":     "📧",
    "prg_texto": "📄",
    "unidad":    "📦",
    "nota":      "🎓",
    "actividad": "✏️",
    "foro":      "💬",
  };

  if (appState.novedades.length === 0) {
    const emptyHtml = `<div class="p-6 text-center text-slate-400 text-xs">Sin avisos nuevos en el aula virtual.</div>`;
    if (containerDash) containerDash.innerHTML = emptyHtml;
    if (containerTab)  containerTab.innerHTML  = emptyHtml;
    return;
  }

  // Ordenar de más reciente a más antigua (string "YYYY MM DD HH MM" se ordena lexicográficamente)
  const ordenadas = [...appState.novedades].sort((a, b) => {
    const fa = String(a.fecha || "").trim();
    const fb = String(b.fecha || "").trim();
    return fb.localeCompare(fa);
  });

  const buildHtml = (novedades, compact = false) => novedades.map((n) => {
    const icono     = TIPO_ICON[n.clase] || "🔔";
    const fechaFmt  = fmtFecha(n.fecha);
    const edadTxt   = edadRelativa(n.fecha);
    const titulo    = cleanText(n.nombre_item || n.nombre_unidad || n.titulo, "Publicación del campus");
    const curso     = cleanText(n.nombre_curso, "");
    const remitente = n.remitente ? `👤 ${n.remitente}` : "";
    const infoCurso = [remitente, curso ? `📍 ${curso}` : ""].filter(Boolean).join("  •  ");

    if (compact) {
      return `
        <div class="p-3.5 rounded-2xl bg-midnight-base border border-midnight-border space-y-1">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold text-indigo-400">${icono} ${cleanText(n.nombre_curso, "Aviso")}</span>
            <span class="text-[10px] text-slate-500 font-mono" title="${fechaFmt}">${edadTxt}</span>
          </div>
          <h5 class="text-xs font-bold text-white">${titulo}</h5>
        </div>
      `;
    }

    return `
      <div class="p-4 rounded-2xl bg-midnight-card border border-midnight-border space-y-2 hover:border-indigo-500/40 transition-all">
        <div class="flex items-center justify-between gap-2">
          <span class="text-[11px] font-bold text-indigo-400">${icono} ${cleanText(n.clase || "aviso", "aviso").toUpperCase()}</span>
          <span class="px-2 py-0.5 rounded-full bg-midnight-base border border-midnight-border text-[10px] text-slate-400 font-mono" title="${fechaFmt}">${edadTxt}</span>
        </div>
        <h5 class="text-xs font-bold text-white leading-snug">${titulo}</h5>
        ${infoCurso ? `<p class="text-[11px] text-slate-400">${infoCurso}</p>` : ""}
        <p class="text-[11px] text-slate-500 font-mono">📅 ${fechaFmt}</p>
      </div>
    `;
  }).join("");

  if (containerDash) containerDash.innerHTML = buildHtml(ordenadas.slice(0, 8), true);
  if (containerTab)  containerTab.innerHTML  = buildHtml(ordenadas, false);
}

// 4. Directorio de Contactos Integrado (Docentes & Alumnos de la Materia Activa)
async function cargarContactosCurso(cursoId) {
  const container = document.getElementById("curso-contactos-container");
  if (!container) return;

  try {
    const res = await bridge.getContactos(cursoId);
    if (res && res.ok && res.data) {
      appState.contactosCache[cursoId] = res.data;
      renderContactos(res.data);
    }
  } catch (err) {
    console.warn("Error cargando contactos:", err);
  }
}

function renderContactos(miembrosData) {
  const container = document.getElementById("curso-contactos-container");
  if (!container) return;

  let list = [];
  if (Array.isArray(miembrosData)) {
    list = miembrosData;
  } else if (miembrosData && typeof miembrosData === "object") {
    const doc = Array.isArray(miembrosData.docentes) ? miembrosData.docentes.map(d => ({ ...d, rol: "Docente" })) : [];
    const alum = Array.isArray(miembrosData.alumnos) ? miembrosData.alumnos.map(a => ({ ...a, rol: "Alumno" })) : [];
    const cont = Array.isArray(miembrosData.contactos) ? miembrosData.contactos : [];
    list = [...doc, ...alum, ...cont];
  }

  if (!list || list.length === 0) {
    container.innerHTML = `<div class="col-span-full p-8 text-center text-slate-400 text-xs">No hay miembros en el directorio de esta materia.</div>`;
    return;
  }

  container.innerHTML = list.map((m, idx) => {
    const nombreStr = cleanText(m.nombre || m.apellido_nombre || m.usuario, "Miembro IES N°5");
    const esDocente = (m.rol || m.tipo || "").toLowerCase().includes("docente") || (m.tipo || "").toLowerCase().includes("profesor");
    const badgeRole = esDocente ? "bg-purple-500/20 text-purple-300 border-purple-500/40" : "bg-cyan-500/20 text-cyan-300 border-cyan-500/40";
    const imgId = `avatar-contacto-${idx}-${Date.now()}`;

    // Despachar la carga dinámica en background
    setTimeout(() => {
      const imgEl = document.getElementById(imgId);
      if (imgEl) cargarImagenAutenticada(m.foto_url, nombreStr, [imgEl]);
    }, 10);

    return `
      <div class="glass-card-interactive p-4 rounded-2xl flex items-center gap-3.5">
        <img id="${imgId}" alt="${nombreStr}" class="w-12 h-12 rounded-full border border-midnight-bright object-cover bg-slate-800 shrink-0">
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 mb-1">
            <span class="px-2 py-0.5 rounded-full border text-[9px] font-bold uppercase ${badgeRole}">
              ${esDocente ? 'Docente' : 'Alumno'}
            </span>
          </div>
          <h5 class="text-xs font-bold text-white truncate">${nombreStr}</h5>
          <span class="text-[10px] text-slate-400 truncate block">${cleanText(m.email, 'Campus IES N°5')}</span>
        </div>
      </div>
    `;
  }).join("");
}

// 5. Registro de Calificaciones por Materia y General
async function cargarCalificacionesCurso(cursoId) {
  const container = document.getElementById("curso-calificaciones-container");
  if (!container) return;

  try {
    const res = await bridge.getCalificaciones(cursoId);
    if (res && res.ok && res.data) {
      const notas = res.data.calificaciones || res.data || [];
      appState.calificacionesCache[cursoId] = notas;
      renderCalificaciones(notas);
    }
  } catch (err) {
    console.warn("Error cargando calificaciones:", err);
  }
}

function renderCalificaciones(notas) {
  const container = document.getElementById("curso-calificaciones-container");
  if (!container) return;

  if (!notas || notas.length === 0) {
    container.innerHTML = `<div class="p-8 text-center text-slate-400 text-xs">No hay notas registradas para esta materia.</div>`;
    return;
  }

  container.innerHTML = notas.map(n => `
    <div class="p-4 rounded-2xl bg-midnight-card border border-midnight-border flex items-center justify-between">
      <div class="min-w-0 flex-1">
        <h5 class="text-xs font-bold text-white truncate">${cleanText(n.nombre || n.evaluacion || n.titulo, 'Evaluación')}</h5>
        <span class="text-[10px] text-slate-400 font-mono">${cleanText(n.categoria || n.docente, '')}${n.fecha ? ' · ' + n.fecha : ''}</span>
        ${n.observaciones ? `<p class="text-[10px] text-slate-500 mt-1 truncate">${n.observaciones}</p>` : ''}
      </div>
      <div class="text-right ml-4 shrink-0">
        <span class="text-lg font-extrabold text-emerald-400 font-mono">${cleanText(n.nota, '—')}</span>
        <span class="block text-[10px] text-slate-400">${cleanText(n.estado || '', 'Calificado')}</span>
      </div>
    </div>
  `).join("");
}

// Renderizar Registro General de Calificaciones (Todas las Materias Inscriptas)
export function renderCalificacionesGenerales() {
  const container = document.getElementById("calificaciones-general-container");
  const promedioEl = document.getElementById("calif-promedio-global");
  if (!container) return;

  if (appState.cursos.length === 0) {
    container.innerHTML = `<div class="p-8 text-center text-slate-400 text-xs">No se encontraron materias para mostrar calificaciones generales.</div>`;
    return;
  }

  container.innerHTML = appState.cursos.map(c => {
    const notasCurso = appState.calificacionesCache[c.id] || [];
    const avance = c.avance !== undefined && c.avance !== null ? c.avance : 70;

    return `
      <div class="glass-card-interactive p-5 rounded-2xl space-y-3">
        <div class="flex items-center justify-between border-b border-midnight-border pb-3">
          <div class="flex items-center gap-2">
            <span class="w-3.5 h-3.5 rounded-full" style="background-color: ${c.color}"></span>
            <h4 class="text-xs font-bold text-white">${cleanText(c.nombre, 'Materia')}</h4>
          </div>
          <span class="px-2.5 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-[10px] font-bold">
            ${avance >= 60 ? 'Cursada Regular' : 'En proceso'}
          </span>
        </div>

        <div class="space-y-2">
          ${notasCurso.length === 0 ? `
            <div class="text-[11px] text-slate-400 italic">Notas de evaluaciones pendientes de publicación.</div>
          ` : notasCurso.map(n => `
            <div class="flex items-center justify-between text-xs py-1 border-b border-midnight-border/40">
              <span class="text-slate-300">${cleanText(n.nombre || n.evaluacion || n.titulo, 'Evaluación')}</span>
              <span class="font-bold text-emerald-400 font-mono">${cleanText(n.nota, '—')}</span>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }).join("");

  if (promedioEl) promedioEl.innerText = appState.cursos.length > 0 ? "8.50" : "--";
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
          <span class="text-[10px] font-mono text-indigo-400">${cleanText(n.fecha, 'Comunicado Oficial')}</span>
          <h4 class="text-xs font-bold text-white leading-snug">${cleanText(n.titulo, 'Noticia')}</h4>
          <p class="text-[11px] text-slate-300 leading-relaxed line-clamp-3">${cleanText(n.resumen, '')}</p>
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

    if (!res || !res.ok) {
      logs.innerHTML += `
        <div class="flex gap-3 items-start">
          <div class="w-8 h-8 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300 flex items-center justify-center shrink-0">
            <span class="material-symbols-outlined text-[18px]">key</span>
          </div>
          <div class="p-3.5 rounded-2xl bg-midnight-card border border-amber-500/30 text-xs text-amber-300 max-w-lg">
            Ingresá tu API Key de Gemini en la sección <strong>Ajustes & Configuración</strong> para habilitar respuestas completas del asistente.
          </div>
        </div>
      `;
      logs.scrollTop = logs.scrollHeight;
      return;
    }

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
export async function verDetalleItem(titulo, detalleOrUrl) {
  const titEl = document.getElementById("modal-tit");
  const bodyEl = document.getElementById("modal-body");
  const modalEl = document.getElementById("modal-detalle");

  const titStr = decodeURIComponent(titulo || "Detalle");
  const rawDet = decodeURIComponent(detalleOrUrl || "");

  if (titEl) titEl.innerText = titStr;
  if (modalEl) modalEl.classList.remove("hidden");

  // Si rawDet parece una URL de actividad/recurso del campus
  if (rawDet.startsWith("http") || rawDet.includes(".cgi")) {
    if (bodyEl) bodyEl.innerHTML = `<div class="p-6 text-center text-slate-400 text-xs"><span class="material-symbols-outlined animate-spin text-xl mr-2">sync</span>Cargando consigna y detalles del aula virtual...</div>`;

    try {
      const res = await bridge.getActividadDetalle(rawDet);
      if (res && res.ok && res.data) {
        const info = res.data;
        const consigna = info.consigna || info.descripcion || info.texto || info.titulo || "Sin consigna adicional especificada.";
        const fecha = info.fecha_limite || info.fecha_apertura || "";
        const estado = info.estado || "";

        let html = "";
        if (fecha || estado) {
          html += `
            <div class="flex items-center justify-between p-3 rounded-xl bg-midnight-base border border-midnight-border mb-4 text-xs font-mono">
              ${fecha ? `<span class="text-slate-300">📅 Límite / Apertura: <strong>${fecha}</strong></span>` : ''}
              ${estado ? `<span class="px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 text-[10px] font-bold">${estado}</span>` : ''}
            </div>
          `;
        }
        html += `<div class="prose prose-invert max-w-none text-xs text-slate-200 leading-relaxed whitespace-pre-line">${consigna}</div>`;
        if (bodyEl) bodyEl.innerHTML = html;
      } else {
        if (bodyEl) bodyEl.innerText = rawDet;
      }
    } catch (e) {
      if (bodyEl) bodyEl.innerText = rawDet;
    }
  } else {
    if (bodyEl) bodyEl.innerText = rawDet;
  }
}

export function closeModal() {
  const modalEl = document.getElementById("modal-detalle");
  if (modalEl) modalEl.classList.add("hidden");
}

function mostrarIndicadorCarga(cargando) {
  const syncIcon = document.getElementById("sync-icon");
  const syncText = document.getElementById("sync-text");

  if (cargando) {
    if (syncIcon) syncIcon.classList.add("animate-spin");
    if (syncText) syncText.innerText = "Sincronizando...";
  } else {
    if (syncIcon) syncIcon.classList.remove("animate-spin");
    if (syncText) syncText.innerText = "Sincronizado";
  }
}

// Funciones globales expuestas al ámbito window
window.switchTab = switchTab;
window.switchCursoSubtab = switchCursoSubtab;
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

    // 1. Sincronizar el valor del selector desplegable en la barra lateral
    const selectEl = document.getElementById("curso-dropdown");
    if (selectEl) selectEl.value = String(cursoId);

    // 2. Actualizar el título de la materia seleccionada
    const nombreEl = document.getElementById("curso-detail-nombre");
    if (nombreEl) nombreEl.innerText = c.nombre;

    // 3. Re-renderizar tarjetas para destacar la materia activa
    renderMaterias();

    // 4. Cargar programa, miembros y notas
    cargarProgramaCurso(c.id);
    cargarContactosCurso(c.id);
    cargarCalificacionesCurso(c.id);

    // 5. Scroll suave al detalle de la materia si está en la pestaña de materias
    const targetTab = document.getElementById("tab-materias");
    if (targetTab && !targetTab.classList.contains("hidden")) {
      const detailBox = document.getElementById("curso-detail-container");
      if (detailBox) {
        detailBox.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
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
