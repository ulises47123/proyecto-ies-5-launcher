/**
 * app_stitch.js — Controlador dinámico reactivo para Campus Virtual IES N°5 (Pyloid IPC)
 * Cumple con el principio de Responsabilidad Única (SRP):
 * - Coordina los datos de sesión, materias, pendientes, novedades, contactos y programa desglosado.
 * - Toda la información mostrada es 100% dinámica basada en el usuario autenticado.
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
  "#2563eb", "#38bdf8", "#10b981", "#8b5cf6", "#f59e0b", "#06b6d4", "#f43f5e", "#ec4899"
];

document.addEventListener("DOMContentLoaded", async () => {
  console.log("[AppStitch] Inicializando interfaz dinámica oficial...");

  const savedTema = localStorage.getItem("campus_tema") || "midnight";
  aplicarTemaVisual(savedTema);

  setupEventListeners();

  // Intentar restaurar sesión previa de forma transparente
  try {
    const sesion = await bridge.restoreSession();
    if (sesion && sesion.ok) {
      console.log("[AppStitch] Sesión guardada restaurada:", sesion);
      document.getElementById("view-login").classList.add("hidden");
      await cargarTodoElCampus();
      return;
    }
  } catch (err) {
    console.log("[AppStitch] Sin sesión guardada activa o error al restaurar:", err);
  }

  // Si no hay sesión válida, asegurar pantalla de login limpia
  document.getElementById("view-login").classList.remove("hidden");
});

function setupEventListeners() {
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
        btnSubmit.innerHTML = `<span class="material-symbols-outlined text-[18px] animate-spin">sync</span><span>Verificando credenciales...</span>`;
      }

      try {
        const res = await bridge.login(u, p, recordar, autologin);
        if (res && res.ok) {
          document.getElementById("view-login").classList.add("hidden");
          await cargarTodoElCampus();
        } else {
          if (errBox) {
            errBox.innerText = res?.error || "Usuario o clave incorrectos en el campus virtual.";
            errBox.classList.remove("hidden");
          }
        }
      } catch (error) {
        if (errBox) {
          errBox.innerText = "Error de conexión: " + error.toString();
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

  const iaForm = document.getElementById("ia-form");
  if (iaForm) {
    iaForm.onsubmit = handleIASubmit;
  }

  // Manejador del Selector de Temas Visuales (Fase de optimización UI)
  const selectTheme = document.getElementById("select-theme");
  if (selectTheme) {
    selectTheme.onchange = (e) => {
      aplicarTemaVisual(e.target.value);
    };
  }

  // Guardar configuración del formulario de Ajustes
  const formPerfilAjustes = document.getElementById("form-perfil-ajustes");
  if (formPerfilAjustes) {
    formPerfilAjustes.onsubmit = async (e) => {
      e.preventDefault();
      const apiKeyVal = document.getElementById("ajustes-api-key")?.value.trim() || "";
      const themeVal = document.getElementById("select-theme")?.value || "midnight";
      const syncVal = document.getElementById("select-auto-sync")?.value || "10";

      try {
        await bridge.saveConfig({
          gemini_api_key: apiKeyVal,
          tema: themeVal,
          auto_sync_minutos: syncVal
        });
        alert("Configuración y perfil guardados exitosamente.");
      } catch (err) {
        alert("Configuración guardada localmente.");
      }
    };
  }

  // Cierre de Modales con Tecla ESC y Clic en Fondo (UX Best Practice)
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

function aplicarTemaVisual(tema) {
  const root = document.documentElement;
  root.setAttribute("data-theme", tema || "midnight");
  const selectTheme = document.getElementById("select-theme");
  if (selectTheme) selectTheme.value = tema || "midnight";
  localStorage.setItem("campus_tema", tema || "midnight");
}

export async function cargarTodoElCampus(forzar = false) {
  // Mostrar la app principal y ocultar login
  const appMain = document.getElementById("app-main");
  const viewLogin = document.getElementById("view-login");
  if (viewLogin) viewLogin.classList.add("hidden");
  if (appMain) { appMain.classList.remove("hidden"); appMain.classList.add("flex"); }

  mostrarIndicadorCarga(true);
  showSection("materias"); // navegación correcta desde el inicio

  try {
    // 0. Cargar configuración persistente (Tema, API Keys)
    try {
      const cfgRes = await bridge.getConfig();
      if (cfgRes && cfgRes.ok && cfgRes.data) {
        const cData = cfgRes.data;
        if (cData.tema) aplicarTemaVisual(cData.tema);
        const apiKeyInp = document.getElementById("ajustes-api-key");
        if (apiKeyInp && cData.gemini_api_key) apiKeyInp.value = cData.gemini_api_key;
        const autoSyncSel = document.getElementById("select-auto-sync");
        if (autoSyncSel && cData.auto_sync_minutos) autoSyncSel.value = String(cData.auto_sync_minutos);
      }
    } catch (e) {}

    // 1. Obtener perfil del usuario que ingresó
    const profRes = await bridge.getProfile();
    if (profRes && profRes.ok && profRes.data) {
      appState.usuario = profRes.data;
      actualizarPerfilUI(profRes.data);
    }

    // 2. Obtener materias y novedades del escritorio oficial
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

    // 3. Obtener actividades pendientes reales
    try {
      const pendRes = await bridge.getPendientes();
      if (pendRes && pendRes.ok && pendRes.data) {
        const raw = pendRes.data;
        appState.pendientes = Array.isArray(raw) ? raw : (raw.actividades_pendientes || raw.pendientes || []);
      }
    } catch (e) {
      console.warn("No se pudieron cargar actividades pendientes:", e);
    }

    // 4. Renderizar vistas dinámicas
    renderMaterias();
    renderPendientes();
    renderNovedades();
    renderEstadisticas();
    actualizarBadgesSidebar();

  } catch (err) {
    console.error("[AppStitch] Error cargando campus:", err);
  } finally {
    mostrarIndicadorCarga(false);
  }
}

function actualizarPerfilUI(u) {
  if (!u) return;
  const nombreEl = document.getElementById("sidebar-user-nombre");
  const dniEl = document.getElementById("sidebar-user-dni");
  const avatarImg = document.getElementById("user-avatar-img");
  const avatarIcon = document.getElementById("user-avatar-icon");

  if (nombreEl) nombreEl.innerText = u.nombre || u.usuario || "—";
  if (dniEl) dniEl.innerText = u.dni ? `DNI: ${u.dni}` : (u.usuario ? `Usuario: ${u.usuario}` : "—");

  const topCarrera = document.getElementById("top-carrera");
  if (topCarrera) topCarrera.innerText = u.carrera || u.carreras || "";

  const inpNom = document.getElementById("ajustes-perfil-nombre");
  const inpDni = document.getElementById("ajustes-perfil-dni");
  const inpMail = document.getElementById("ajustes-perfil-email");
  const inpTel = document.getElementById("ajustes-perfil-telefono");
  if (inpNom && u.nombre) inpNom.value = u.nombre;
  if (inpDni && u.dni) inpDni.value = u.dni;
  if (inpMail && u.email) inpMail.value = u.email;
  if (inpTel && u.telefono) inpTel.value = u.telefono;

  if (u.foto_url && avatarImg && avatarIcon) {
    avatarImg.onerror = () => {
      avatarImg.classList.add("hidden");
      avatarIcon.classList.remove("hidden");
    };
    avatarImg.src = u.foto_url;
    avatarImg.classList.remove("hidden");
    avatarIcon.classList.add("hidden");
  }
}

function actualizarBadgesSidebar() {
  const badgeMat = document.getElementById("badge-materias-count");
  const badgePend = document.getElementById("badge-pendientes-count");
  const pillMat = document.getElementById("badge-materias-pill");
  const pillPend = document.getElementById("badge-pendientes-pill");

  const totalCursos = appState.cursos.length;
  const totalPend = appState.pendientes.length;

  if (badgeMat) badgeMat.innerText = totalCursos;
  if (badgePend) badgePend.innerText = totalPend;
  if (pillMat) pillMat.innerText = `${totalCursos} Materias Activas`;
  if (pillPend) pillPend.innerText = `${totalPend} Entregas`;

  const statMat = document.getElementById("stat-materias-count");
  const statPend = document.getElementById("stat-pendientes-count");
  if (statMat) statMat.innerText = `${totalCursos} Asignaturas`;
  if (statPend) statPend.innerText = `${totalPend} entregas`;
}

// 1. Renderizar Mis Materias dinámicas
export function renderMaterias() {
  const container = document.getElementById("materias-grid");
  if (!container) return;

  if (appState.cursos.length === 0) {
    container.innerHTML = `
      <div class="col-span-full p-8 text-center bg-midnight-card border border-midnight-border rounded-xl">
        <span class="material-symbols-outlined text-slate-500 text-4xl mb-2">school</span>
        <h4 class="text-sm font-bold text-white">No se encontraron materias registradas</h4>
        <p class="text-xs text-slate-400 mt-1">Presiona "Actualizar" en el sidebar para sincronizar con el campus virtual.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = appState.cursos.map((c) => {
    const avance = c.avance !== undefined ? c.avance : 60;
    const ultAcceso = c.ultimo_acceso || "Reciente";
    const estadoTxt = c.items_obligatorios || c.items_obl || (c.no_leidos ? `${c.no_leidos} novedades` : "Al día");

    return `
      <div class="bg-midnight-card border border-midnight-border rounded-xl p-4 flex flex-col justify-between hover:border-blue-500/50 hover:shadow-lg transition-all">
        <div>
          <div class="flex items-center justify-between gap-2 mb-2">
            <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${c.color}"></span>
            <span class="text-[10px] text-slate-400 font-mono">Último acceso: ${ultAcceso}</span>
          </div>
          <h4 class="text-sm font-bold text-white mb-2 leading-snug">${c.nombre}</h4>
          <div class="text-[11px] text-slate-400 mb-3">Estado: <span class="text-slate-200 font-semibold">${estadoTxt}</span></div>
        </div>
        <div class="pt-3 border-t border-midnight-border/60 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="w-20 bg-midnight-base rounded-full h-1.5 overflow-hidden">
              <div class="bg-emerald-400 h-1.5 rounded-full" style="width: ${avance}%"></div>
            </div>
            <span class="text-[10px] font-bold text-emerald-400">${avance}%</span>
          </div>
          <button onclick="window.appBridgeUI.abrirCursoDetalle('${c.id}')" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs rounded-lg shadow-md shadow-blue-600/30 flex items-center gap-1 transition-all cursor-pointer">
            <span>Entrar &rarr;</span>
          </button>
        </div>
      </div>
    `;
  }).join("");
}

// 2. Renderizar Pendientes dinámicos
export function renderPendientes() {
  const container = document.getElementById("pendientes-list");
  if (!container) return;

  if (appState.pendientes.length === 0) {
    container.innerHTML = `
      <div class="p-8 text-center bg-midnight-card border border-midnight-border rounded-xl">
        <span class="material-symbols-outlined text-emerald-400 text-4xl mb-2">check_circle</span>
        <h4 class="text-sm font-bold text-white">¡No tienes actividades pendientes de entrega!</h4>
        <p class="text-xs text-slate-400 mt-1">Estás al día con todas las consignas del aula virtual.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = appState.pendientes.map((p) => {
    const vencida = p.vencida || false;
    const badgeColor = vencida ? "bg-rose-500/20 text-rose-300 border-rose-500/40" : "bg-amber-500/20 text-amber-300 border-amber-500/40";
    const plazo = p.tiempo_restante_str || p.fecha_limite || "Consultar en el aula";

    return `
      <div class="bg-midnight-card border border-midnight-border rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-md hover:border-amber-500/40 transition-all">
        <div class="space-y-1 flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold text-amber-400 truncate">${p.curso_nombre || "Materia"}</span>
            <span class="text-[10px] px-2 py-0.5 rounded border font-semibold ${badgeColor}">
              ${vencida ? "Vencida" : "Entrega Requerida"}
            </span>
          </div>
          <h4 class="text-sm font-bold text-white">${p.titulo || "Consigna de actividad"}</h4>
          <p class="text-xs text-slate-400 font-mono">${p.fecha_apertura || ""} ${p.fecha_limite ? "• Cierre: " + p.fecha_limite : ""}</p>
        </div>
        <div class="flex items-center gap-3 shrink-0">
          <span class="text-xs font-bold font-mono ${vencida ? 'text-rose-400' : 'text-amber-400'}">${plazo}</span>
          <button onclick="window.appBridgeUI.irAMateriaDesdePendiente('${p.id_curso || ''}', '${encodeURIComponent(p.url || '')}', '${encodeURIComponent(p.titulo || '')}')" class="px-3.5 py-2 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 font-semibold text-xs rounded-lg flex items-center gap-1 transition-all cursor-pointer">
            <span>Ver actividad &rarr;</span>
          </button>
        </div>
      </div>
    `;
  }).join("");
}

// 3. Renderizar Novedades dinámicas
export function renderNovedades() {
  const container = document.getElementById("novedades-list");
  if (!container) return;

  if (appState.novedades.length === 0) {
    container.innerHTML = `
      <div class="p-8 text-center bg-midnight-card border border-midnight-border rounded-xl">
        <span class="material-symbols-outlined text-slate-500 text-4xl mb-2">notifications_off</span>
        <h4 class="text-sm font-bold text-white">No hay avisos recientes</h4>
        <p class="text-xs text-slate-400 mt-1">El escritorio institucional no reporta novedades sin leer.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = appState.novedades.map((n, idx) => `
    <div class="bg-midnight-card border border-midnight-border rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-md hover:border-blue-500/40 transition-all">
      <div class="space-y-1.5 flex-1 min-w-0">
        <div class="flex items-center justify-between sm:justify-start gap-3">
          <span class="text-xs font-bold text-blue-400 truncate">${n.nombre_curso || "Aviso Institucional"}</span>
          <span class="text-[11px] text-slate-400 font-mono shrink-0">${n.fecha || ""}</span>
        </div>
        <h4 class="text-sm font-bold text-white">${n.nombre_item || n.titulo || (n.clase ? 'Nuevo ' + n.clase : "Aviso")}</h4>
        <p class="text-xs text-slate-300 leading-relaxed line-clamp-2">${n.resumen || (n.cant ? `${n.cant} mensaje(s) recibidos.` : "Ingresa para ver el comunicado completo.")}</p>
      </div>
      <button onclick="window.appBridgeUI.verNovedadDetalle(${idx})" class="px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-600 text-white font-semibold text-xs rounded-lg shadow-md shadow-blue-600/30 flex items-center gap-1 shrink-0 transition-all cursor-pointer">
        <span>Ver novedad &rarr;</span>
      </button>
    </div>
  `).join("");
}

// 4. Renderizar Estadísticas
export function renderEstadisticas() {
  const container = document.getElementById("stats-progress-list");
  if (!container) return;

  if (appState.cursos.length === 0) {
    container.innerHTML = `<div class="p-4 text-center text-slate-500 text-xs">Sin materias para calcular estadísticas.</div>`;
    return;
  }

  container.innerHTML = appState.cursos.map((c) => {
    const nombreMat = (c.nombre && c.nombre !== 'null') ? c.nombre : "Materia sin título";
    const ultAcceso = (c.ultimo_acceso && c.ultimo_acceso !== 'null') ? c.ultimo_acceso : "—";
    const avance = (c.avance !== undefined && c.avance !== null && c.avance !== 'null') ? c.avance : 65;
    return `
      <div class="bg-midnight-base/80 border border-midnight-border/70 rounded-xl p-3.5 flex items-center justify-between gap-4">
        <div class="min-w-0 flex-1">
          <h5 class="text-xs font-bold text-white truncate">${nombreMat}</h5>
          <span class="text-[10px] text-slate-400">Último acceso: ${ultAcceso}</span>
        </div>
        <div class="flex items-center gap-3 shrink-0">
          <div class="w-32 bg-midnight-card rounded-full h-2 overflow-hidden border border-midnight-border/60">
            <div class="bg-gradient-to-r from-blue-500 to-cyan-400 h-2 rounded-full" style="width: ${avance}%"></div>
          </div>
          <span class="text-xs font-mono font-bold text-cyan-300 w-10 text-right">${avance}%</span>
        </div>
      </div>
    `;
  }).join("");
}

// VISTA DETALLADA DE MATERIA CON DESPLEGABLES / ACORDEÓN
export async function abrirCursoDetalle(cursoId) {
  let curso = appState.cursos.find(c => String(c.id) === String(cursoId));
  if (!curso && appState.cursos.length > 0) curso = appState.cursos[0];
  if (!curso) return;

  appState.cursoActivo = curso;

  const titleEl = document.getElementById("curso-detail-nombre");
  if (titleEl) titleEl.innerText = curso.nombre;

  showSection("curso-detail");
  switchCursoTab("programa");

  cargarSubtabPrograma(curso.id);
  cargarSubtabMensajes(curso.id);
  cargarSubtabCalificaciones(curso.id);
  cargarSubtabContactos(curso.id);
}

// Subtab 1: Programa con desplegables interactivos de Unidades e Ítems
async function cargarSubtabPrograma(cursoId) {
  const container = document.getElementById("curso-unidades-container");
  if (!container) return;
  container.innerHTML = `<div class="p-8 text-center text-slate-400 text-xs"><span class="material-symbols-outlined animate-spin text-xl mr-2 align-middle">sync</span>Cargando programa y unidades...</div>`;

  try {
    const res = await bridge.getPrograma(cursoId);
    const unidades = res?.data || [];
    appState.programaCache[cursoId] = unidades;

    if (unidades.length === 0) {
      container.innerHTML = `<div class="p-8 text-center bg-midnight-card border border-midnight-border rounded-xl text-slate-400 text-xs">No se encontraron unidades o clases cargadas en esta materia.</div>`;
      return;
    }

    container.innerHTML = unidades.map((u, uIdx) => {
      const items = u.items || [];
      const uIdSafe = `unidad-accordion-${uIdx}`;
      return `
        <div class="bg-midnight-card border border-midnight-border rounded-xl overflow-hidden shadow-sm">
          <!-- Cabecera Desplegable de la Unidad -->
          <button onclick="window.appBridgeUI.toggleUnidad('${uIdSafe}')" class="w-full bg-midnight-sidebar hover:bg-midnight-hover px-4 py-3 font-bold text-xs text-white flex items-center justify-between border-b border-midnight-border transition-colors text-left cursor-pointer">
            <div class="flex items-center gap-2.5 min-w-0">
              <span id="${uIdSafe}-arrow" class="material-symbols-outlined text-blue-400 text-base transition-transform transform rotate-90">expand_more</span>
              <span class="truncate">${u.nombre || "Unidad Temática"}</span>
            </div>
            <span class="text-[10px] font-mono text-cyan-300 shrink-0 ml-2">${items.length} Recursos</span>
          </button>
          
          <!-- Contenedor Desplegable de Subtemas/Ítems -->
          <div id="${uIdSafe}" class="p-3 divide-y divide-midnight-border/50 text-xs block">
            ${items.length === 0 ? `<div class="p-3 text-slate-400 text-center italic">Sin ítems en esta unidad.</div>` : items.map((it, iIdx) => {
              const esAct = it.tipo && (it.tipo.includes("actividad") || it.tipo_desc.toLowerCase().includes("actividad"));
              const iconName = esAct ? "assignment" : (it.tipo === "archivo" ? "attach_file" : "description");
              const estado = it.estado || "";
              const estadoColor = it.estado_color || "slate";
              
              let badgeColor = "bg-midnight-base text-slate-300 border-midnight-border";
              if (estadoColor === "green" || estado.toLowerCase().includes("entregad")) badgeColor = "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
              else if (estadoColor === "red" || estado.toLowerCase().includes("cerrad")) badgeColor = "bg-rose-500/20 text-rose-300 border-rose-500/40";
              else if (estadoColor === "orange" || estado.toLowerCase().includes("pendient")) badgeColor = "bg-amber-500/20 text-amber-300 border-amber-500/40";

              const clickAttr = it.url ? `onclick="window.appBridgeUI.verDetalleItem('${encodeURIComponent(it.url)}', '${encodeURIComponent(it.titulo || '')}')" class="py-2.5 flex items-center justify-between hover:bg-midnight-hover px-2 rounded-lg transition-colors gap-3 cursor-pointer group"` : `class="py-2.5 flex items-center justify-between px-2 rounded-lg transition-colors gap-3"`;

              return `
                <div ${clickAttr}>
                  <div class="flex items-center gap-2.5 text-slate-200 min-w-0 flex-1">
                    <span class="material-symbols-outlined text-blue-400 group-hover:text-cyan-300 text-lg shrink-0">${iconName}</span>
                    <span class="truncate group-hover:text-blue-300 transition-colors font-medium">${it.titulo || it.nombre || "Clase / Documento"}</span>
                  </div>
                  <div class="flex items-center gap-2 shrink-0">
                    ${estado ? `<span class="text-[10px] px-2 py-0.5 rounded border font-mono font-semibold ${badgeColor}">${estado}</span>` : ""}
                    ${it.url ? `
                      <span class="p-1 text-slate-400 group-hover:text-blue-300 rounded transition-colors" title="Ver detalle">
                        <span class="material-symbols-outlined text-base">visibility</span>
                      </span>
                    ` : ""}
                  </div>
                </div>
              `;
            }).join("")}
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<div class="p-4 text-rose-400 text-xs text-center">Error al obtener el programa de la materia: ${err.toString()}</div>`;
  }
}

export function toggleUnidad(id) {
  const el = document.getElementById(id);
  const arrow = document.getElementById(id + "-arrow");
  if (el) {
    const isHidden = el.classList.contains("hidden");
    if (isHidden) {
      el.classList.remove("hidden");
      if (arrow) arrow.classList.add("rotate-90");
    } else {
      el.classList.add("hidden");
      if (arrow) arrow.classList.remove("rotate-90");
    }
  }
}

export async function verDetalleItem(encodedUrl, encodedTitulo) {
  const url = decodeURIComponent(encodedUrl);
  const titulo = decodeURIComponent(encodedTitulo);
  const modalEl = document.getElementById("modal-detalle");
  const titEl = document.getElementById("modal-tit");
  const bodyEl = document.getElementById("modal-body");

  if (titEl) titEl.innerText = titulo || "Detalle de Actividad";
  if (bodyEl) {
    bodyEl.innerHTML = `<div class="p-8 text-center text-slate-400"><span class="material-symbols-outlined animate-spin text-2xl">sync</span><p class="mt-2">Cargando contenido oficial...</p></div>`;
  }
  if (modalEl) modalEl.classList.remove("hidden");

  try {
    const res = await bridge.getActividadDetalle(url);
    if (res && res.ok && res.data) {
      const d = res.data;
      if (bodyEl) {
        bodyEl.innerHTML = `
          <div class="p-3 bg-midnight-base rounded-xl border border-midnight-border space-y-1">
            <div class="flex items-center justify-between">
              <span class="text-[11px] text-blue-400 font-bold uppercase">${d.estado || "Actividad"}</span>
              <span class="text-[10px] text-slate-400 font-mono">${d.fechas || ""}</span>
            </div>
            <h4 class="text-sm font-bold text-white">${d.titulo || titulo}</h4>
          </div>
          <div class="text-xs leading-relaxed text-slate-200 pt-2 space-y-2 max-h-[50vh] overflow-y-auto">
            ${d.cuerpo || "<p class='italic text-slate-400'>Sin consigna descriptiva adicional.</p>"}
          </div>
          ${d.adjuntos && d.adjuntos.length > 0 ? `
            <div class="pt-3 border-t border-midnight-border/60">
              <span class="text-[11px] font-bold text-slate-300 block mb-2">Archivos Adjuntos:</span>
              <div class="flex flex-wrap gap-2">
                ${d.adjuntos.map(a => `
                  <a href="${a.url}" target="_blank" class="px-2.5 py-1.5 bg-midnight-base hover:bg-midnight-hover border border-midnight-border rounded-lg text-[11px] text-blue-400 hover:text-blue-300 flex items-center gap-1">
                    <span class="material-symbols-outlined text-sm">download</span>
                    <span class="truncate max-w-[200px]">${a.nombre}</span>
                  </a>
                `).join("")}
              </div>
            </div>
          ` : ""}
        `;
      }
    } else {
      if (bodyEl) bodyEl.innerHTML = `<div class="p-4 text-center text-slate-400">No se pudo obtener el detalle de la actividad seleccionada.</div>`;
    }
  } catch (err) {
    if (bodyEl) bodyEl.innerHTML = `<div class="p-4 text-center text-rose-400">Error: ${err.toString()}</div>`;
  }
}

// Subtab 2: Mensajes del Curso
async function cargarSubtabMensajes(cursoId) {
  const container = document.getElementById("curso-mensajes-container");
  if (!container) return;
  container.innerHTML = `<div class="p-8 text-center text-slate-400 text-xs"><span class="material-symbols-outlined animate-spin text-xl mr-2 align-middle">sync</span>Consultando mensajes...</div>`;

  try {
    const res = await bridge.getMensajes(cursoId, "Inbox");
    const msgs = res?.data || [];
    appState.mensajesCache[cursoId] = msgs;

    if (msgs.length === 0) {
      container.innerHTML = `<div class="p-8 text-center text-slate-400 text-xs">Bandeja de entrada vacía en esta materia.</div>`;
      return;
    }

    container.innerHTML = msgs.slice(0, 10).map(m => `
      <div class="p-3 bg-midnight-base/80 border border-midnight-border/80 rounded-xl flex items-center justify-between hover:border-blue-400/40 transition-colors">
        <div class="flex items-center gap-3 min-w-0">
          <span class="material-symbols-outlined text-blue-400 text-xl shrink-0">mail</span>
          <div class="min-w-0">
            <h5 class="text-xs font-bold text-white truncate">${m.de || m.remitente || "Docente"}</h5>
            <p class="text-xs text-slate-300 truncate">${m.asunto || "Sin asunto"}</p>
          </div>
        </div>
        <span class="text-[10px] text-slate-400 font-mono shrink-0 ml-2">${m.fecha || ""}</span>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<div class="p-4 text-rose-400 text-xs text-center">Error al cargar mensajes: ${err.toString()}</div>`;
  }
}

// Subtab 3: Calificaciones oficiales del Curso
async function cargarSubtabCalificaciones(cursoId) {
  const container = document.getElementById("curso-calificaciones-container");
  if (!container) return;
  container.innerHTML = `<div class="col-span-full p-8 text-center text-slate-400 text-xs"><span class="material-symbols-outlined animate-spin text-xl mr-2 align-middle">sync</span>Cargando calificaciones oficiales...</div>`;

  try {
    const res = await bridge.getCalificaciones(cursoId);
    const califs = res?.data || [];
    appState.calificacionesCache[cursoId] = califs;

    if (califs.length === 0) {
      container.innerHTML = `
        <div class="col-span-full p-8 text-center text-slate-400 text-xs">
          Aún no se registran notas volcadas en el libro oficial de esta materia.
        </div>
      `;
      return;
    }

    container.innerHTML = califs.map(c => {
      const hasNota = c.nota && c.nota !== "—" && c.nota !== "-";
      const badgeClass = hasNota ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40" : "bg-slate-700/40 text-slate-300 border-slate-600";
      return `
        <div class="p-4 bg-midnight-base/80 border border-midnight-border rounded-xl space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-bold text-blue-400 uppercase">${c.categoria || "Evaluación"}</span>
            <span class="text-xs font-bold px-2 py-0.5 rounded border ${badgeClass}">Nota: ${c.nota || "—"}</span>
          </div>
          <h5 class="text-xs font-bold text-white">${c.nombre || "Evaluación oficial"}</h5>
          ${c.observaciones ? `<p class="text-[11px] text-slate-400 italic">${c.observaciones}</p>` : ""}
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<div class="col-span-full p-4 text-rose-400 text-xs text-center">Error al cargar calificaciones: ${err.toString()}</div>`;
  }
}

// Subtab 4: Contactos de Cursada
async function cargarSubtabContactos(cursoId) {
  const container = document.getElementById("curso-contactos-container");
  const countEl = document.getElementById("curso-contactos-count");
  if (!container) return;
  container.innerHTML = `<div class="col-span-full p-8 text-center text-slate-400 text-xs"><span class="material-symbols-outlined animate-spin text-xl mr-2 align-middle">sync</span>Obteniendo directorio de docentes y alumnos...</div>`;

  try {
    const res = await bridge.getContactos(cursoId);
    const data = res?.data || { docentes: [], alumnos: [] };
    appState.contactosCache[cursoId] = data;

    const docentes = data.docentes || [];
    const alumnos = data.alumnos || [];
    const total = docentes.length + alumnos.length;

    if (countEl) countEl.innerText = `${total} Miembros Registrados`;

    if (total === 0) {
      container.innerHTML = `<div class="col-span-full p-8 text-center text-slate-400 text-xs">No hay contactos disponibles para esta materia.</div>`;
      return;
    }

    const todos = [
      ...docentes.map(d => ({ ...d, esDocente: true })),
      ...alumnos.map(a => ({ ...a, esDocente: false }))
    ];

    container.innerHTML = todos.map((p, pIdx) => {
      const iniciales = (p.nombre || "Usuario").split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase();
      const badgeClass = p.esDocente ? "text-blue-400 bg-blue-500/10 border-blue-500/20" : "text-slate-400 bg-slate-800 border-slate-700";
      const fotoUrl = p.foto_url || p.avatar || "";
      const esDefault = fotoUrl.includes("comunes/thumb") || fotoUrl.includes("default") || fotoUrl.includes("spacer") || fotoUrl.includes("blank");
      const tieneFotoReal = fotoUrl && fotoUrl.length > 10 && !esDefault;

      return `
        <div onclick="window.appBridgeUI.verContactoFicha('${p.id || pIdx}', '${cursoId}')" class="p-3 bg-midnight-base/80 border border-midnight-border rounded-xl flex items-center gap-3 hover:border-blue-500/40 cursor-pointer transition-all">
          <div class="w-10 h-10 rounded-full ${p.esDocente ? 'bg-blue-600/30 border-blue-400/40 text-blue-300' : 'bg-slate-700/40 border-slate-600 text-slate-300'} border flex items-center justify-center font-bold text-xs shrink-0 overflow-hidden">
            ${tieneFotoReal ? `<img src="${fotoUrl}" alt="${p.nombre}" class="w-full h-full object-cover" onerror="this.classList.add('hidden'); if(this.nextElementSibling) this.nextElementSibling.classList.remove('hidden');"/><span class="hidden">${iniciales}</span>` : `<span>${iniciales}</span>`}
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-white truncate">${p.nombre}</span>
              <span class="text-[9px] px-1.5 py-0.2 rounded border font-semibold ${badgeClass}">
                ${p.rol || (p.esDocente ? "Docente" : "Estudiante")}
              </span>
            </div>
            <div class="text-[10px] text-slate-400 truncate mt-0.5">${p.email && p.email !== 'No especificado' ? p.email : 'Ver ficha de contacto'}</div>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<div class="col-span-full p-4 text-rose-400 text-xs text-center">Error al cargar contactos: ${err.toString()}</div>`;
  }
}

// Navegación entre secciones
export function showSection(secId) {
  document.querySelectorAll(".content-section").forEach(sec => sec.classList.add("hidden"));
  const target = document.getElementById(`sec-${secId}`);
  if (target) target.classList.remove("hidden");

  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.classList.remove("bg-gradient-to-r", "from-blue-600", "to-blue-500", "text-white", "shadow-lg", "shadow-blue-600/30", "border-blue-400/40");
    btn.classList.add("text-slate-300");
  });
  const activeBtn = document.getElementById(`btn-nav-${secId}`);
  if (activeBtn) {
    activeBtn.classList.add("bg-gradient-to-r", "from-blue-600", "to-blue-500", "text-white", "shadow-lg", "shadow-blue-600/30", "border-blue-400/40");
    activeBtn.classList.remove("text-slate-300");
  }

  const titles = {
    materias: "Mis Materias",
    pendientes: "Pendientes",
    novedades: "Novedades",
    ia: "Asistente IA",
    estadisticas: "Estadísticas",
    ajustes: "Ajustes",
    "curso-detail": "Detalle de Asignatura"
  };
  const topTitle = document.getElementById("top-title");
  if (topTitle) topTitle.innerText = titles[secId] || "Campus Virtual";
}

export function volverAMaterias() {
  showSection("materias");
}

export function irAMateriaDesdePendiente(cursoId, actUrl, actTitulo = "") {
  if (actUrl) {
    verDetalleItem(actUrl, actTitulo || "Detalle de Pendiente");
  } else if (cursoId) {
    abrirCursoDetalle(cursoId);
  } else {
    showSection("materias");
  }
}

export function switchCursoTab(tabId) {
  document.querySelectorAll(".subtab-content").forEach(c => c.classList.add("hidden"));
  document.querySelectorAll(".subtab-btn").forEach(b => {
    b.classList.remove("bg-blue-600", "text-white");
    b.classList.add("text-slate-400");
  });

  const tabContent = document.getElementById(`subtab-${tabId}`);
  if (tabContent) tabContent.classList.remove("hidden");

  const btn = document.getElementById(`tab-btn-${tabId}`);
  if (btn) {
    btn.classList.add("bg-blue-600", "text-white");
    btn.classList.remove("text-slate-400");
  }
}

// Modales
export function verNovedadDetalle(idx) {
  const n = appState.novedades[idx] || {};
  const titEl = document.getElementById("modal-tit");
  const bodyEl = document.getElementById("modal-body");
  const modalEl = document.getElementById("modal-detalle");

  if (titEl) titEl.innerText = n.nombre_item || n.titulo || (n.clase ? 'Nuevo ' + n.clase : "Comunicado Oficial");
  if (bodyEl) {
    const linkBoton = n.curso_id ? `<button onclick="closeModal(); abrirCursoDetalle('${n.curso_id}')" class="w-full mt-3 py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg text-xs flex items-center justify-center gap-2 transition-all"><span class="material-symbols-outlined text-[16px]">menu_book</span><span>Ir a la materia (${n.nombre_curso || 'Ver'})</span></button>` : '';

    bodyEl.innerHTML = `
      <div class="p-3 bg-midnight-base rounded-xl border border-midnight-border space-y-1">
        <span class="text-[11px] text-blue-400 font-bold block">${n.nombre_curso || "Aula Virtual"}</span>
        <span class="text-[10px] text-slate-400 font-mono">Publicado: ${n.fecha || "Reciente"} ${n.remitente ? '&bull; Por: ' + n.remitente : ''}</span>
      </div>
      <div class="text-xs leading-relaxed text-slate-200 pt-2 whitespace-pre-wrap">${n.resumen || n.cuerpo || (n.cant ? `Tienes ${n.cant} aviso(s)/mensaje(s) pendientes de lectura.` : "Sin descripción adicional.")}</div>
      ${linkBoton}
    `;
  }
  if (modalEl) modalEl.classList.remove("hidden");
}

export async function verContactoFicha(usuarioId, cursoId) {
  const titEl = document.getElementById("modal-tit");
  const bodyEl = document.getElementById("modal-body");
  const modalEl = document.getElementById("modal-detalle");

  if (titEl) titEl.innerText = "Ficha de Miembro Institucional";
  if (bodyEl) bodyEl.innerHTML = `<div class="p-6 text-center text-slate-400 text-xs"><span class="material-symbols-outlined animate-spin text-lg mr-2">sync</span>Cargando perfil...</div>`;
  if (modalEl) modalEl.classList.remove("hidden");

  try {
    const res = await bridge.getPerfil(cursoId || "", usuarioId);
    const p = res?.data || {};

    if (bodyEl) {
      bodyEl.innerHTML = `
        <div class="flex items-center gap-4 p-4 bg-midnight-base rounded-xl border border-midnight-border">
          <div class="w-16 h-16 rounded-full bg-blue-600/30 border border-blue-400/40 text-blue-300 flex items-center justify-center font-bold text-lg overflow-hidden shrink-0">
            ${p.foto_url ? `<img src="${p.foto_url}" class="w-full h-full object-cover" onerror="this.remove()"/>` : `<span>${(p.nombre || "U")[0]}</span>`}
          </div>
          <div class="space-y-1">
            <h4 class="text-sm font-bold text-white">${p.nombre || p.usuario || "Miembro del Campus"}</h4>
            <span class="text-xs text-blue-400 block">${p.rol || "Integrante Cátedra"}</span>
            <span class="text-[11px] text-slate-400 font-mono block">${p.email || "Correo privado en aula virtual"}</span>
          </div>
        </div>
        <div class="space-y-2 pt-2 text-xs text-slate-300">
          ${p.telefono ? `<p><strong>Teléfono:</strong> ${p.telefono}</p>` : ''}
          ${p.biografia ? `<p><strong>Biografía:</strong> ${p.biografia}</p>` : '<p class="text-slate-400 italic">Sin biografía pública registrada.</p>'}
        </div>
      `;
    }
  } catch (err) {
    if (bodyEl) bodyEl.innerHTML = `<div class="p-4 text-rose-400 text-xs text-center">No se pudo cargar la información detallada del usuario.</div>`;
  }
}

export async function abrirModalRedactarMensaje() {
  const titEl = document.getElementById("modal-tit");
  const bodyEl = document.getElementById("modal-body");
  const modalEl = document.getElementById("modal-detalle");

  const curso = appState.cursoActivo;
  const cursoId = curso ? curso.id : "";

  if (titEl) titEl.innerText = "Redactar Mensaje Interno";
  if (bodyEl) {
    bodyEl.innerHTML = `<div class="p-6 text-center text-slate-400 text-xs"><span class="material-symbols-outlined animate-spin text-lg mr-2">sync</span>Cargando destinatarios del curso...</div>`;
  }
  if (modalEl) modalEl.classList.remove("hidden");

  let contactosOpts = `<option value="">-- Seleccionar destinatario --</option>`;
  try {
    const res = await bridge.getContactos(cursoId);
    const data = res?.data || {};
    const docentes = data.docentes || [];
    const alumnos = data.alumnos || [];

    if (docentes.length > 0) {
      contactosOpts += `<optgroup label="Docentes">` + docentes.map(d => `<option value="${d.id || d.nombre}">${d.nombre} (${d.rol || 'Docente'})</option>`).join("") + `</optgroup>`;
    }
    if (alumnos.length > 0) {
      contactosOpts += `<optgroup label="Compañeros de Cursada">` + alumnos.map(a => `<option value="${a.id || a.nombre}">${a.nombre}</option>`).join("") + `</optgroup>`;
    }
  } catch (e) {
    console.warn("No se pudieron cargar contactos para el selector:", e);
  }

  if (bodyEl) {
    bodyEl.innerHTML = `
      <form id="form-env-msg" onsubmit="window.appBridgeUI.enviarMensajeHandler(event, '${cursoId}')" class="space-y-3">
        <div>
          <label class="block text-[11px] font-semibold text-slate-400 mb-1">Destinatario</label>
          <select id="msg-destinatario" required class="w-full bg-midnight-input border border-midnight-border text-xs text-white p-2.5 rounded-lg focus:outline-none focus:border-blue-500">
            ${contactosOpts}
          </select>
        </div>
        <div>
          <label class="block text-[11px] font-semibold text-slate-400 mb-1">Asunto</label>
          <input type="text" id="msg-asunto" required class="w-full bg-midnight-input border border-midnight-border text-xs text-white p-2.5 rounded-lg focus:outline-none focus:border-blue-500" placeholder="Asunto de la consulta..."/>
        </div>
        <div>
          <label class="block text-[11px] font-semibold text-slate-400 mb-1">Cuerpo del Mensaje</label>
          <textarea id="msg-cuerpo" rows="4" required class="w-full bg-midnight-input border border-midnight-border text-xs text-white p-2.5 rounded-lg focus:outline-none focus:border-blue-500" placeholder="Escribí aquí el contenido..."></textarea>
        </div>
        <div>
          <label class="block text-[11px] font-semibold text-slate-400 mb-1">Archivo Adjunto (Opcional)</label>
          <div class="flex items-center gap-2">
            <input type="file" id="msg-adjunto" class="w-full text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-600/30 file:text-blue-300 hover:file:bg-blue-600/50 cursor-pointer"/>
          </div>
        </div>
        <div id="msg-env-status" class="text-xs hidden"></div>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" onclick="closeModal()" class="px-3 py-1.5 bg-midnight-base hover:bg-midnight-hover border border-midnight-border text-slate-300 rounded-lg text-xs font-semibold">Cancelar</button>
          <button type="submit" id="btn-env-msg-submit" class="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold shadow-md shadow-blue-600/30 flex items-center gap-1.5 transition-all">
            <span class="material-symbols-outlined text-[15px]">send</span>
            <span>Enviar Mensaje</span>
          </button>
        </div>
      </form>
    `;
  }
  if (modalEl) modalEl.classList.remove("hidden");
}

export async function enviarMensajeHandler(event, cursoId) {
  event.preventDefault();
  const statusEl = document.getElementById("msg-env-status");
  const btnSubmit = document.getElementById("btn-env-msg-submit");

  const dest = document.getElementById("msg-destinatario").value.trim();
  const asunto = document.getElementById("msg-asunto").value.trim();
  const cuerpo = document.getElementById("msg-cuerpo").value.trim();
  const adjInput = document.getElementById("msg-adjunto");
  const archivoAdjunto = (adjInput && adjInput.files && adjInput.files[0]) ? (adjInput.files[0].path || adjInput.files[0].name) : "";

  if (!dest || !asunto || !cuerpo) return;

  if (btnSubmit) { btnSubmit.disabled = true; btnSubmit.innerHTML = `<span class="material-symbols-outlined animate-spin text-[15px]">sync</span><span>Enviando...</span>`; }
  if (statusEl) { statusEl.className = "text-xs text-blue-400"; statusEl.innerText = "Enviando mensaje al servidor..."; statusEl.classList.remove("hidden"); }

  try {
    const res = await bridge.enviarMensaje(cursoId, dest, asunto, cuerpo, archivoAdjunto);
    if (res && res.ok) {
      if (statusEl) { statusEl.className = "text-xs text-emerald-400 font-semibold"; statusEl.innerText = "¡Mensaje enviado con éxito!"; }
      setTimeout(() => {
        closeModal();
        cargarSubtabMensajes(cursoId);
      }, 1200);
    } else {
      if (statusEl) { statusEl.className = "text-xs text-rose-400"; statusEl.innerText = res?.error || "No se pudo enviar el mensaje."; }
      if (btnSubmit) { btnSubmit.disabled = false; btnSubmit.innerHTML = `<span class="material-symbols-outlined text-[15px]">send</span><span>Reintentar</span>`; }
    }
  } catch (err) {
    if (statusEl) { statusEl.className = "text-xs text-rose-400"; statusEl.innerText = "Error de red: " + err.toString(); }
    if (btnSubmit) { btnSubmit.disabled = false; btnSubmit.innerHTML = `<span class="material-symbols-outlined text-[15px]">send</span><span>Reintentar</span>`; }
  }
}

export function closeModal() {
  const modalEl = document.getElementById("modal-detalle");
  if (modalEl) modalEl.classList.add("hidden");
}

// Chat Asistente IA
async function handleIASubmit(e) {
  e.preventDefault();
  const input = document.getElementById("ia-input");
  if (!input) return;
  const q = input.value.trim();
  if (!q) return;
  input.value = "";
  await sendIAMsg(q);
}

export async function quickIA(txt) {
  await sendIAMsg(txt);
}

export async function sendIAMsg(q) {
  const logs = document.getElementById("ia-chat-logs");
  if (!logs) return;

  logs.innerHTML += `
    <div class="flex gap-3 items-start justify-end">
      <div class="bg-blue-600 p-3 rounded-2xl text-xs text-white max-w-xl shadow-md">${q}</div>
    </div>
  `;
  logs.scrollTop = logs.scrollHeight;

  const thinkingId = "ia-thinking-" + Date.now();
  logs.innerHTML += `
    <div id="${thinkingId}" class="flex gap-3 items-start">
      <div class="w-8 h-8 rounded-full bg-purple-600/30 border border-purple-400/40 text-purple-300 flex items-center justify-center shrink-0">
        <span class="material-symbols-outlined text-[18px]">smart_toy</span>
      </div>
      <div class="bg-midnight-base border border-midnight-border p-3 rounded-2xl text-xs text-slate-300 max-w-xl leading-relaxed shadow-md flex items-center gap-2">
        <span class="material-symbols-outlined text-sm animate-spin text-purple-400">sync</span>
        <span>Consultando al Asistente del Campus...</span>
      </div>
    </div>
  `;
  logs.scrollTop = logs.scrollHeight;

  try {
    const res = await bridge.askIA(q);
    const thinkingEl = document.getElementById(thinkingId);
    if (thinkingEl) thinkingEl.remove();

    const respText = res?.data?.respuesta || res?.respuesta || res?.data || "No pude procesar tu consulta en este momento.";

    logs.innerHTML += `
      <div class="flex gap-3 items-start">
        <div class="w-8 h-8 rounded-full bg-purple-600/30 border border-purple-400/40 text-purple-300 flex items-center justify-center shrink-0">
          <span class="material-symbols-outlined text-[18px]">smart_toy</span>
        </div>
        <div class="bg-midnight-base border border-midnight-border p-3.5 rounded-2xl text-xs text-slate-200 max-w-xl leading-relaxed shadow-md">
          ${respText}
        </div>
      </div>
    `;
    logs.scrollTop = logs.scrollHeight;
  } catch (err) {
    const thinkingEl = document.getElementById(thinkingId);
    if (thinkingEl) thinkingEl.remove();
    logs.innerHTML += `
      <div class="flex gap-3 items-start">
        <div class="w-8 h-8 rounded-full bg-rose-600/30 border border-rose-400/40 text-rose-300 flex items-center justify-center shrink-0">
          <span class="material-symbols-outlined text-[18px]">error</span>
        </div>
        <div class="bg-midnight-base border border-rose-900/40 p-3.5 rounded-2xl text-xs text-rose-300 max-w-xl">
          Error en la consulta: ${err.toString()}
        </div>
      </div>
    `;
    logs.scrollTop = logs.scrollHeight;
  }
}

// Botones 7 y 8
export async function actualizarDatos() {
  await cargarTodoElCampus(true);
}

export async function logout() {
  if (confirm("¿Estás seguro de que deseas cerrar la sesión en el Campus Virtual?")) {
    try {
      await bridge.logout();
    } catch (e) {
      console.warn("Logout error:", e);
    }
    appState.usuario = null;
    appState.cursos = [];
    appState.pendientes = [];
    appState.novedades = [];

    // Ocultar completamente la UI principal y reiniciar formulario
    const appMain = document.getElementById("app-main");
    if (appMain) {
      appMain.classList.add("hidden");
      appMain.classList.remove("flex");
    }

    const autoLoginCheck = document.getElementById("login-autologin");
    if (autoLoginCheck) autoLoginCheck.checked = false;

    const passInp = document.getElementById("login-pass");
    if (passInp) passInp.value = "";

    document.getElementById("view-login").classList.remove("hidden");
  }
}

function mostrarIndicadorCarga(cargando) {
  const syncBtn = document.getElementById("btn-action-actualizar");
  if (syncBtn) {
    if (cargando) {
      syncBtn.classList.add("opacity-60", "pointer-events-none");
      syncBtn.querySelector("span:last-child").innerText = "Sincronizando...";
    } else {
      syncBtn.classList.remove("opacity-60", "pointer-events-none");
      syncBtn.querySelector("span:last-child").innerText = "Actualizar";
    }
  }
}

// Exponer en window para el markup (ES Module no expone al scope global por defecto)
window.appBridgeUI = {
  showSection,
  abrirCursoDetalle,
  volverAMaterias,
  irAMateriaDesdePendiente,
  switchCursoTab,
  toggleUnidad,
  verDetalleItem,
  verNovedadDetalle,
  verContactoFicha,
  abrirModalRedactarMensaje,
  enviarMensajeHandler,
  closeModal,
  actualizarDatos,
  logout,
  quickIA
};

// Exponer cada función individualmente en window para que los onclick del HTML funcionen
window.showSection = showSection;
window.actualizarDatos = actualizarDatos;
window.logout = logout;
window.volverAMaterias = volverAMaterias;
window.switchCursoTab = switchCursoTab;
window.closeModal = closeModal;
window.abrirCursoDetalle = abrirCursoDetalle;
window.irAMateriaDesdePendiente = irAMateriaDesdePendiente;
window.toggleUnidad = toggleUnidad;
window.verDetalleItem = verDetalleItem;
window.verNovedadDetalle = verNovedadDetalle;
window.verContactoFicha = verContactoFicha;
window.abrirModalRedactarMensaje = abrirModalRedactarMensaje;
window.enviarMensajeHandler = enviarMensajeHandler;
window.quickIA = quickIA;
