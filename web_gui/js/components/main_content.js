import { state } from "../state.js";
import { bridge } from "../bridge.js";

export class MainContent {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.channelTitle = document.getElementById("channel-title");
    this.channelIcon = document.getElementById("channel-icon");

    // Estado interno para mensajería y noticias
    this.currentBandeja = "Inbox";
    this.selectedMensaje = null;
    this.noticiasQuery = "";

    state.subscribe(async (event, data) => {
      if (event === "channel_selected" || event === "curso_selected") {
        this.selectedMensaje = null;
        await this.render();
      }
    });
  }

  async render() {
    const ch = state.selectedChannel;
    this.channelTitle.innerText = ch;

    // Actualizar icono de cabecera
    const icons = {
      novedades: "ph-broadcast",
      contactos: "ph-address-book",
      actividades: "ph-clipboard-text",
      calificaciones: "ph-chart-bar",
      sitio: "ph-newspaper",
      mensajes: "ph-envelope",
      ia: "ph-sparkle"
    };
    if (this.channelIcon) {
      this.channelIcon.className = `ph-bold ${icons[ch] || "ph-hash"} text-discord-textMuted text-lg`;
    }

    this.container.innerHTML = `
      <div class="flex items-center justify-center h-48 text-discord-textMuted text-sm">
        <i class="ph-bold ph-spinner animate-spin text-2xl mr-2"></i>
        <span>Cargando contenido de #${ch}...</span>
      </div>
    `;

    try {
      switch (ch) {
        case "novedades":
          await this._renderNovedades();
          break;
        case "contactos":
          await this._renderContactos();
          break;
        case "actividades":
          await this._renderActividades();
          break;
        case "calificaciones":
          await this._renderCalificaciones();
          break;
        case "sitio":
          await this._renderSitio();
          break;
        case "mensajes":
          await this._renderMensajes();
          break;
        case "ia":
          this._renderIA();
          break;
        default:
          this.container.innerHTML = `
            <div class="p-8 text-center text-discord-textMuted">
              <i class="ph-bold ph-folder-open text-4xl mb-2"></i>
              <h3 class="text-base font-bold text-discord-textHeader">Sección #${ch}</h3>
              <p class="text-xs mt-1">Conectando servicio con el canal del aula...</p>
            </div>
          `;
      }
    } catch (err) {
      this.container.innerHTML = `
        <div class="p-6 bg-red-950/30 border border-red-800/40 rounded-xl text-red-300 text-xs">
          <div class="font-bold mb-1 flex items-center gap-1.5 text-sm">
            <i class="ph-bold ph-warning-circle text-base"></i> Error al cargar canal
          </div>
          <div>${err.message || err}</div>
        </div>
      `;
    }
  }

  // ================= 1. #NOVEDADES =================
  async _renderNovedades() {
    const res = await bridge.getCursos();
    const novedades = res?.data?.novedades || [];

    if (novedades.length === 0) {
      this.container.innerHTML = `<div class="p-8 text-center text-discord-textMuted text-sm">No hay novedades registradas recientemente.</div>`;
      return;
    }

    this.container.innerHTML = `
      <div class="space-y-3">
        ${novedades.map(n => `
          <div class="p-4 bg-discord-channellist border border-discord-border rounded-xl hover:border-discord-accent/40 transition-colors">
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-xs font-bold text-discord-accent">${n.nombre_curso || n.materia || "Aviso General"}</span>
              <span class="text-[11px] text-discord-textMuted">${n.fecha || ""}</span>
            </div>
            <h4 class="text-sm font-bold text-discord-textHeader">${n.nombre_item || n.titulo || (n.clase ? 'Nuevo ' + n.clase : "Sin título")}</h4>
            <p class="text-xs text-discord-textNormal mt-1 leading-relaxed">${n.resumen || (n.cant ? `${n.cant} mensaje(s) / actualización recibida.` : "")}</p>
          </div>
        `).join("")}
      </div>
    `;
  }

  // ================= 2. #CONTACTOS-AULA =================
  async _renderContactos() {
    const cursoId = state.selectedCurso?.id;
    if (!cursoId) {
      this.container.innerHTML = `<div class="p-8 text-center text-discord-textMuted text-sm">Selecciona una materia para ver sus contactos.</div>`;
      return;
    }

    const res = await bridge.getContactos(cursoId);
    const data = res?.data || { docentes: [], alumnos: [] };
    state.setContactos(data);

    const total = (data.docentes?.length || 0) + (data.alumnos?.length || 0);

    this.container.innerHTML = `
      <div class="space-y-4">
        <div class="flex items-center justify-between pb-2 border-b border-discord-border">
          <h3 class="text-sm font-bold text-discord-textHeader uppercase tracking-wider">Directorio del Aula</h3>
          <span class="text-xs text-discord-textMuted">${total} Contactos</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          ${[...(data.docentes || []), ...(data.alumnos || [])].map(p => `
            <div class="p-3 bg-discord-channellist border border-discord-border rounded-xl flex items-center gap-3">
              <img src="${p.foto_url || 'https://ies5tello-juj.infd.edu.ar/aula/skins/redinfod/img/comunes/thumb_40x45.jpg'}" class="w-10 h-10 rounded-full object-cover shrink-0">
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-bold text-discord-textHeader truncate">${p.nombre}</span>
                  <span class="text-[10px] px-1.5 py-0.5 rounded ${p.rol === 'Docente' ? 'bg-discord-accent text-white' : 'bg-discord-serverbar text-discord-textMuted'}">${p.rol}</span>
                </div>
                <div class="text-[11px] text-discord-textMuted truncate">${p.email !== 'No especificado' ? p.email : 'Perfil privado'}</div>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  // ================= 3. #ACTIVIDADES-TAREAS =================
  async _renderActividades() {
    const cursoId = state.selectedCurso?.id;
    if (!cursoId) {
      this.container.innerHTML = `<div class="p-8 text-center text-discord-textMuted text-sm">Selecciona una materia para explorar sus clases.</div>`;
      return;
    }

    const res = await bridge.getPrograma(cursoId);
    const unidades = res?.data || [];

    if (unidades.length === 0) {
      this.container.innerHTML = `<div class="p-8 text-center text-discord-textMuted text-sm">No se encontraron unidades o actividades en esta materia.</div>`;
      return;
    }

    this.container.innerHTML = `
      <div class="space-y-4">
        ${unidades.map(u => `
          <div class="border border-discord-border bg-discord-channellist rounded-xl overflow-hidden">
            <div class="bg-discord-serverbar px-4 py-2.5 font-bold text-xs text-discord-textHeader flex items-center justify-between">
              <span>${u.nombre || "Unidad"}</span>
              <span class="text-[10px] text-discord-textMuted">${u.items?.length || 0} Ítems</span>
            </div>
            <div class="p-2 divide-y divide-discord-border/50">
              ${(u.items || []).map(it => `
                <div class="py-2 px-2 flex items-center justify-between hover:bg-discord-hoverItem rounded-lg transition-colors">
                  <div class="flex items-center gap-2.5 min-w-0">
                    <i class="ph-bold ph-file-text text-discord-accent text-lg"></i>
                    <span class="text-xs text-discord-textNormal truncate">${it.titulo || it.nombre || "Elemento"}</span>
                  </div>
                  <span class="text-[10px] px-2 py-0.5 rounded bg-discord-serverbar text-discord-textMuted uppercase">${it.tipo || "Clase"}</span>
                </div>
              `).join("")}
            </div>
          </div>
        `).join("")}
      </div>
    `;
  }

  // ================= 4. #CALIFICACIONES =================
  async _renderCalificaciones() {
    const cursoId = state.selectedCurso?.id;
    if (!cursoId) {
      this.container.innerHTML = `<div class="p-8 text-center text-discord-textMuted text-sm">Selecciona una materia para consultar tus calificaciones.</div>`;
      return;
    }

    const res = await bridge.getCalificaciones(cursoId);
    const califs = res?.data || [];

    if (!califs || califs.length === 0) {
      this.container.innerHTML = `
        <div class="p-12 text-center text-discord-textMuted flex flex-col items-center justify-center">
          <div class="w-16 h-16 rounded-full bg-discord-serverbar flex items-center justify-center text-3xl mb-3 text-discord-textMuted">
            <i class="ph-bold ph-check-circle"></i>
          </div>
          <h3 class="text-base font-bold text-discord-textHeader">Sin calificaciones registradas</h3>
          <p class="text-xs mt-1 max-w-sm">Aún no se han cargado notas o evaluaciones oficiales en el libro de calificaciones de esta materia.</p>
        </div>
      `;
      return;
    }

    this.container.innerHTML = `
      <div class="space-y-4">
        <div class="flex items-center justify-between pb-2 border-b border-discord-border">
          <div>
            <h3 class="text-sm font-bold text-discord-textHeader uppercase tracking-wider">Libro de Calificaciones</h3>
            <p class="text-[11px] text-discord-textMuted mt-0.5">${state.selectedCurso?.nombre || "Materia"}</p>
          </div>
          <span class="text-xs px-2.5 py-1 rounded bg-discord-accent/20 text-discord-accent font-bold">${califs.length} Evaluaciones</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          ${califs.map(c => {
            const hasNota = c.nota && c.nota !== "—" && c.nota !== "-";
            const notaBadgeClass = hasNota
              ? "bg-discord-green/20 text-discord-green border border-discord-green/30 font-bold"
              : "bg-discord-serverbar text-discord-textMuted border border-discord-border";

            return `
              <div class="p-4 bg-discord-channellist border border-discord-border rounded-xl flex flex-col justify-between hover:border-discord-accent/50 transition-colors">
                <div>
                  <div class="flex items-start justify-between gap-2 mb-2">
                    <span class="text-[10px] font-bold uppercase tracking-wider text-discord-accent px-1.5 py-0.5 rounded bg-discord-accent/10">
                      ${c.categoria || "Evaluación"}
                    </span>
                    <span class="text-xs px-2.5 py-1 rounded-lg ${notaBadgeClass}">
                      Nota: ${c.nota || "—"}
                    </span>
                  </div>
                  <h4 class="text-sm font-bold text-discord-textHeader mb-1 line-clamp-2">${c.nombre || "Sin nombre"}</h4>
                  ${c.docente ? `<div class="text-[11px] text-discord-textMuted flex items-center gap-1.5"><i class="ph-bold ph-chalkboard-teacher"></i> ${c.docente}</div>` : ""}
                  ${c.fecha ? `<div class="text-[11px] text-discord-textMuted flex items-center gap-1.5 mt-0.5"><i class="ph-bold ph-calendar"></i> ${c.fecha}</div>` : ""}
                  ${c.peso ? `<div class="text-[11px] text-discord-textMuted flex items-center gap-1.5 mt-0.5"><i class="ph-bold ph-scales"></i> Peso: ${c.peso}</div>` : ""}
                </div>

                ${c.observaciones ? `
                  <div class="mt-3 pt-2.5 border-t border-discord-border text-xs text-discord-textNormal bg-discord-serverbar/50 p-2.5 rounded-lg">
                    <span class="text-[10px] font-bold uppercase text-discord-textMuted block mb-0.5">Observaciones:</span>
                    <p class="italic text-[11px] leading-relaxed">${c.observaciones}</p>
                  </div>
                ` : ""}
              </div>
            `;
          }).join("")}
        </div>
      </div>
    `;
  }

  // ================= 5. #NOTICIAS-INSTITUTO =================
  async _renderSitio() {
    this.container.innerHTML = `
      <div class="space-y-4">
        <!-- Buscador y Encabezado -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-discord-border">
          <div>
            <h3 class="text-sm font-bold text-discord-textHeader uppercase tracking-wider">Sitio Público Institucional</h3>
            <p class="text-[11px] text-discord-textMuted mt-0.5">Noticias, circulares y resoluciones del IES N°5</p>
          </div>
          <div class="flex items-center gap-2">
            <div class="relative w-full sm:w-64">
              <i class="ph-bold ph-magnifying-glass absolute left-3 top-2.5 text-discord-textMuted text-xs"></i>
              <input type="text" id="sitio-search-input" value="${this.noticiasQuery}" placeholder="Buscar circulares, padrón..."
                class="w-full pl-8 pr-3 py-1.5 bg-discord-channellist text-discord-textHeader rounded-lg border border-discord-border focus:outline-none focus:border-discord-accent text-xs">
            </div>
            <button id="btn-sitio-search" class="px-3 py-1.5 bg-discord-accent hover:bg-discord-accentHover text-white font-bold rounded-lg text-xs transition-colors">
              Buscar
            </button>
            <button id="btn-sitio-refresh" title="Recargar del sitio" class="p-1.5 bg-discord-channellist hover:bg-discord-hoverItem rounded-lg text-discord-textMuted hover:text-white transition-colors">
              <i class="ph-bold ph-arrows-clockwise text-sm"></i>
            </button>
          </div>
        </div>

        <div id="sitio-results-container">
          <div class="flex items-center justify-center h-32 text-discord-textMuted text-xs">
            <i class="ph-bold ph-spinner animate-spin text-xl mr-2"></i> Consultando portal institucional...
          </div>
        </div>
      </div>
    `;

    const searchInput = document.getElementById("sitio-search-input");
    const btnSearch = document.getElementById("btn-sitio-search");
    const btnRefresh = document.getElementById("btn-sitio-refresh");

    const doSearchOrLoad = async (force = false) => {
      const resultsBox = document.getElementById("sitio-results-container");
      if (!resultsBox) return;

      resultsBox.innerHTML = `
        <div class="flex items-center justify-center h-32 text-discord-textMuted text-xs">
          <i class="ph-bold ph-spinner animate-spin text-xl mr-2"></i> Cargando...
        </div>
      `;

      const q = searchInput.value.trim();
      this.noticiasQuery = q;

      let items = [];
      if (q) {
        const res = await bridge.buscarSitio(q, 20);
        items = res?.data || [];
      } else {
        const res = await bridge.getSitioNoticias(force);
        const dictRecursos = res?.data?.recursos || {};
        items = Object.values(dictRecursos);
      }

      if (items.length === 0) {
        resultsBox.innerHTML = `
          <div class="p-12 text-center text-discord-textMuted">
            <i class="ph-bold ph-magnifying-glass text-3xl mb-2"></i>
            <p class="text-xs">No se encontraron noticias ni resoluciones que coincidan con la búsqueda.</p>
          </div>
        `;
        return;
      }

      resultsBox.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          ${items.map(item => {
            const isPdf = (item.url && item.url.toLowerCase().endsWith(".pdf")) || item.tipo === "pdf";
            const isDoc = item.url && (item.url.endsWith(".docx") || item.url.endsWith(".doc"));
            const iconClass = isPdf ? "ph-file-pdf text-red-400" : (isDoc ? "ph-file-doc text-blue-400" : "ph-newspaper text-discord-accent");

            return `
              <div class="p-4 bg-discord-channellist border border-discord-border rounded-xl flex flex-col justify-between hover:border-discord-accent/40 transition-colors">
                <div>
                  <div class="flex items-center gap-2 mb-2">
                    <i class="ph-bold ${iconClass} text-lg shrink-0"></i>
                    <span class="text-[10px] font-bold uppercase tracking-wider text-discord-textMuted">
                      ${isPdf ? "Documento PDF" : (isDoc ? "Documento Word" : "Página Institucional")}
                    </span>
                  </div>
                  <h4 class="text-xs font-bold text-discord-textHeader mb-1.5 line-clamp-2">${item.titulo || "Documento Institucional"}</h4>
                  <p class="text-[11px] text-discord-textNormal line-clamp-3 leading-relaxed mb-3">
                    ${item.texto_preview || item.resumen || "Documento oficial publicado en el portal de Educación Superior N° 5."}
                  </p>
                </div>
                <div class="pt-2 border-t border-discord-border flex items-center justify-between">
                  <span class="text-[10px] text-discord-textMuted truncate max-w-[200px]">${item.fecha_extraccion ? item.fecha_extraccion.split("T")[0] : ""}</span>
                  <a href="${item.url}" target="_blank" class="px-2.5 py-1 bg-discord-serverbar hover:bg-discord-accent text-discord-textNormal hover:text-white rounded text-[11px] font-bold flex items-center gap-1 transition-colors">
                    <span>Abrir</span>
                    <i class="ph-bold ph-arrow-square-out text-xs"></i>
                  </a>
                </div>
              </div>
            `;
          }).join("")}
        </div>
      `;
    };

    btnSearch.onclick = () => doSearchOrLoad(false);
    btnRefresh.onclick = () => doSearchOrLoad(true);
    searchInput.onkeydown = (e) => { if (e.key === "Enter") doSearchOrLoad(false); };

    await doSearchOrLoad(false);
  }

  // ================= 6. #CORREO-INTERNO =================
  async _renderMensajes() {
    const cursoId = state.selectedCurso?.id;
    if (!cursoId) {
      this.container.innerHTML = `<div class="p-8 text-center text-discord-textMuted text-sm">Selecciona una materia para acceder al correo interno.</div>`;
      return;
    }

    this.container.innerHTML = `
      <div class="flex flex-col h-full space-y-3">
        <!-- Barra de herramientas: Carpetas y Botón Redactar -->
        <div class="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-discord-border">
          <div class="flex items-center gap-1.5 bg-discord-serverbar p-1 rounded-xl">
            <button id="tab-inbox" class="px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${this.currentBandeja === 'Inbox' ? 'bg-discord-accent text-white' : 'text-discord-textMuted hover:text-discord-textNormal'}">
              <i class="ph-bold ph-tray mr-1"></i> Recibidos
            </button>
            <button id="tab-outbox" class="px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${this.currentBandeja === 'Outbox' ? 'bg-discord-accent text-white' : 'text-discord-textMuted hover:text-discord-textNormal'}">
              <i class="ph-bold ph-paper-plane-tilt mr-1"></i> Enviados
            </button>
            <button id="tab-trash" class="px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${this.currentBandeja === 'Trash' ? 'bg-discord-accent text-white' : 'text-discord-textMuted hover:text-discord-textNormal'}">
              <i class="ph-bold ph-trash mr-1"></i> Papelera
            </button>
          </div>

          <div class="flex items-center gap-2">
            ${this.currentBandeja === 'Trash' ? `
              <button id="btn-vaciar-papelera" class="px-3 py-1.5 bg-red-900/30 hover:bg-red-800/50 text-red-300 border border-red-800/50 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors">
                <i class="ph-bold ph-trash"></i> Vaciar Papelera
              </button>
            ` : ""}
            <button id="btn-redactar-msg" class="px-3.5 py-1.5 bg-discord-accent hover:bg-discord-accentHover text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-md shadow-discord-accent/20 transition-colors">
              <i class="ph-bold ph-pencil-simple text-sm"></i> Redactar
            </button>
          </div>
        </div>

        <!-- Contenedor dinámico (Lista o Detalle o Redacción) -->
        <div id="mensajes-view-area" class="flex-1 overflow-y-auto">
          <div class="flex items-center justify-center h-32 text-discord-textMuted text-xs">
            <i class="ph-bold ph-spinner animate-spin text-xl mr-2"></i> Cargando bandeja ${this.currentBandeja}...
          </div>
        </div>
      </div>
    `;

    // Eventos de tabs
    document.getElementById("tab-inbox").onclick = () => { this.currentBandeja = "Inbox"; this._renderMensajes(); };
    document.getElementById("tab-outbox").onclick = () => { this.currentBandeja = "Outbox"; this._renderMensajes(); };
    document.getElementById("tab-trash").onclick = () => { this.currentBandeja = "Trash"; this._renderMensajes(); };

    const btnVaciar = document.getElementById("btn-vaciar-papelera");
    if (btnVaciar) {
      btnVaciar.onclick = async () => {
        if (confirm("¿Estás seguro de que deseas vaciar por completo la papelera? Esta acción no se puede deshacer.")) {
          const res = await bridge.vaciarPapelera(cursoId);
          alert(res.ok ? "Papelera vaciada correctamente." : (res.error || "No se pudo vaciar la papelera."));
          await this._renderMensajes();
        }
      };
    }

    document.getElementById("btn-redactar-msg").onclick = () => this._mostrarFormularioRedaccion();

    // Cargar lista de mensajes
    await this._cargarListaMensajes();
  }

  async _cargarListaMensajes() {
    const cursoId = state.selectedCurso?.id;
    const viewArea = document.getElementById("mensajes-view-area");
    if (!viewArea) return;

    const res = await bridge.getMensajes(cursoId, this.currentBandeja);
    const mensajes = res?.data || [];

    if (mensajes.length === 0) {
      viewArea.innerHTML = `
        <div class="p-12 text-center text-discord-textMuted flex flex-col items-center">
          <i class="ph-bold ph-tray text-3xl mb-2"></i>
          <p class="text-xs">No hay mensajes en la carpeta ${this.currentBandeja}.</p>
        </div>
      `;
      return;
    }

    viewArea.innerHTML = `
      <div class="space-y-2">
        ${mensajes.map(m => `
          <div data-id="${m.id}" data-link="${m.link || ''}" class="mensaje-item p-3 bg-discord-channellist border border-discord-border hover:border-discord-accent/50 rounded-xl cursor-pointer flex items-center justify-between gap-3 transition-colors">
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-8 h-8 rounded-full bg-discord-serverbar text-discord-accent flex items-center justify-center shrink-0">
                <i class="ph-bold ph-envelope-simple text-sm"></i>
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-bold text-discord-textHeader truncate">${m.remitente || "Remitente"}</span>
                </div>
                <div class="text-xs text-discord-textNormal font-medium truncate">${m.asunto || "Sin Asunto"}</div>
              </div>
            </div>
            <div class="flex items-center gap-3 shrink-0">
              <span class="text-[11px] text-discord-textMuted">${m.fecha || ""}</span>
              ${this.currentBandeja !== 'Trash' ? `
                <button data-action="eliminar" data-id="${m.id}" title="Mover a papelera" class="p-1.5 hover:bg-discord-serverbar text-discord-textMuted hover:text-red-400 rounded transition-colors">
                  <i class="ph-bold ph-trash text-sm"></i>
                </button>
              ` : ""}
            </div>
          </div>
        `).join("")}
      </div>
    `;

    // Event listeners para abrir detalle o eliminar
    viewArea.querySelectorAll(".mensaje-item").forEach(item => {
      item.onclick = async (e) => {
        if (e.target.closest("button[data-action='eliminar']")) return;
        const msgId = item.dataset.id;
        const msgLink = item.dataset.link;
        await this._mostrarDetalleMensaje(msgLink || msgId);
      };
    });

    viewArea.querySelectorAll("button[data-action='eliminar']").forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const msgId = btn.dataset.id;
        if (confirm("¿Deseas mover este mensaje a la papelera?")) {
          const res = await bridge.eliminarMensaje(cursoId, msgId);
          alert(res.ok ? "Mensaje movido a la papelera." : (res.error || "No se pudo eliminar el mensaje."));
          await this._cargarListaMensajes();
        }
      };
    });
  }

  async _mostrarDetalleMensaje(linkOId) {
    const cursoId = state.selectedCurso?.id;
    const viewArea = document.getElementById("mensajes-view-area");
    if (!viewArea) return;

    viewArea.innerHTML = `
      <div class="flex items-center justify-center h-32 text-discord-textMuted text-xs">
        <i class="ph-bold ph-spinner animate-spin text-xl mr-2"></i> Obteniendo detalle del mensaje...
      </div>
    `;

    const res = await bridge.getMensajeDetalle(linkOId, cursoId);
    const msg = res?.data;

    if (!msg || !res.ok) {
      viewArea.innerHTML = `
        <div class="p-6 bg-red-950/30 border border-red-800/40 rounded-xl text-red-300 text-xs">
          <p class="font-bold mb-1">No se pudo cargar el mensaje</p>
          <p>${res?.error || "Error desconocido"}</p>
          <button id="btn-back-msg" class="mt-3 px-3 py-1 bg-discord-serverbar text-white rounded text-xs font-bold">Volver</button>
        </div>
      `;
      document.getElementById("btn-back-msg").onclick = () => this._cargarListaMensajes();
      return;
    }

    viewArea.innerHTML = `
      <div class="p-5 bg-discord-channellist border border-discord-border rounded-xl space-y-4">
        <!-- Cabecera de lectura -->
        <div class="flex items-center justify-between pb-3 border-b border-discord-border">
          <button id="btn-back-msg" class="px-3 py-1.5 bg-discord-serverbar hover:bg-discord-hoverItem text-discord-textNormal rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors">
            <i class="ph-bold ph-arrow-left"></i> Volver a ${this.currentBandeja}
          </button>
          <div class="flex items-center gap-2">
            <button id="btn-responder-msg" class="px-3 py-1.5 bg-discord-accent hover:bg-discord-accentHover text-white rounded-lg text-xs font-bold flex items-center gap-1 transition-colors">
              <i class="ph-bold ph-arrow-bend-up-left"></i> Responder
            </button>
            <button id="btn-reenviar-msg" class="px-3 py-1.5 bg-discord-serverbar hover:bg-discord-hoverItem text-discord-textNormal rounded-lg text-xs font-bold flex items-center gap-1 transition-colors">
              <i class="ph-bold ph-arrow-bend-up-right"></i> Reenviar
            </button>
            ${this.currentBandeja !== 'Trash' ? `
              <button id="btn-eliminar-msg" class="px-3 py-1.5 bg-red-950/30 hover:bg-red-900/50 text-red-300 border border-red-800/40 rounded-lg text-xs font-bold flex items-center gap-1 transition-colors">
                <i class="ph-bold ph-trash"></i> Eliminar
              </button>
            ` : ""}
          </div>
        </div>

        <!-- Metadatos -->
        <div class="space-y-1">
          <h3 class="text-base font-bold text-discord-textHeader">${msg.asunto || "Sin Asunto"}</h3>
          <div class="flex items-center justify-between text-xs text-discord-textMuted pt-1">
            <span><strong>De:</strong> ${msg.remitente || "Remitente"} ${msg.para ? `| <strong>Para:</strong> ${msg.para}` : ""}</span>
            <span>${msg.fecha || ""}</span>
          </div>
        </div>

        <!-- Adjuntos -->
        ${(msg.adjuntos && msg.adjuntos.length > 0) ? `
          <div class="p-3 bg-discord-serverbar rounded-lg flex flex-wrap gap-2 items-center">
            <span class="text-[11px] font-bold text-discord-textMuted flex items-center gap-1">
              <i class="ph-bold ph-paperclip"></i> Adjuntos:
            </span>
            ${msg.adjuntos.map(a => `
              <a href="${a.url}" target="_blank" class="px-2.5 py-1 bg-discord-channellist hover:bg-discord-activeItem rounded text-xs text-discord-accent font-medium flex items-center gap-1 border border-discord-border">
                <i class="ph-bold ph-file-arrow-down"></i> ${a.nombre || "Descargar"}
              </a>
            `).join("")}
          </div>
        ` : ""}

        <!-- Cuerpo del mensaje -->
        <div class="p-4 bg-discord-maincontent rounded-xl text-xs text-discord-textNormal leading-relaxed border border-discord-border whitespace-pre-wrap font-sans">
          ${msg.cuerpo || "(Mensaje sin contenido de texto)"}
        </div>
      </div>
    `;

    document.getElementById("btn-back-msg").onclick = () => this._cargarListaMensajes();

    const btnResp = document.getElementById("btn-responder-msg");
    if (btnResp) {
      btnResp.onclick = () => {
        this._mostrarFormularioRespuesta(msg);
      };
    }

    const btnReenv = document.getElementById("btn-reenviar-msg");
    if (btnReenv) {
      btnReenv.onclick = () => {
        this._mostrarFormularioReenvio(msg);
      };
    }

    const btnElim = document.getElementById("btn-eliminar-msg");
    if (btnElim) {
      btnElim.onclick = async () => {
        if (confirm("¿Deseas mover este mensaje a la papelera?")) {
          const res = await bridge.eliminarMensaje(cursoId, msg.id);
          alert(res.ok ? "Mensaje movido a la papelera." : (res.error || "No se pudo eliminar el mensaje."));
          await this._cargarListaMensajes();
        }
      };
    }
  }

  _mostrarFormularioRedaccion() {
    const cursoId = state.selectedCurso?.id;
    const viewArea = document.getElementById("mensajes-view-area");
    if (!viewArea) return;

    const contactos = [...(state.contactos.docentes || []), ...(state.contactos.alumnos || [])];

    viewArea.innerHTML = `
      <div class="p-5 bg-discord-channellist border border-discord-border rounded-xl space-y-4">
        <div class="flex items-center justify-between pb-2 border-b border-discord-border">
          <h3 class="text-sm font-bold text-discord-textHeader">Nuevo Mensaje de Correo Interno</h3>
          <button id="btn-cancelar-compose" class="px-2.5 py-1 text-xs text-discord-textMuted hover:text-white">Cancelar</button>
        </div>

        <form id="form-compose-msg" class="space-y-3">
          <div>
            <label class="block text-[11px] font-bold text-discord-textMuted uppercase mb-1">Destinatario (Docente o Compañero)</label>
            <select id="compose-destinatario" required class="w-full px-3 py-2 bg-discord-serverbar text-discord-textHeader rounded-lg border border-discord-border focus:outline-none focus:border-discord-accent text-xs">
              <option value="">Selecciona un destinatario...</option>
              ${contactos.map(c => `
                <option value="${c.id || c.dni || c.nombre}">${c.nombre} (${c.rol})</option>
              `).join("")}
            </select>
          </div>

          <div>
            <label class="block text-[11px] font-bold text-discord-textMuted uppercase mb-1">Asunto</label>
            <input type="text" id="compose-asunto" required placeholder="Asunto del correo"
              class="w-full px-3 py-2 bg-discord-serverbar text-discord-textHeader rounded-lg border border-discord-border focus:outline-none focus:border-discord-accent text-xs">
          </div>

          <div>
            <label class="block text-[11px] font-bold text-discord-textMuted uppercase mb-1">Cuerpo del Mensaje</label>
            <textarea id="compose-cuerpo" required rows="6" placeholder="Escribe tu mensaje aquí..."
              class="w-full px-3 py-2 bg-discord-serverbar text-discord-textHeader rounded-lg border border-discord-border focus:outline-none focus:border-discord-accent text-xs resize-none"></textarea>
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button type="submit" class="px-4 py-2 bg-discord-accent hover:bg-discord-accentHover text-white text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 shadow-md shadow-discord-accent/20">
              <i class="ph-bold ph-paper-plane-tilt"></i> Enviar Mensaje
            </button>
          </div>
        </form>
      </div>
    `;

    document.getElementById("btn-cancelar-compose").onclick = () => this._cargarListaMensajes();
    document.getElementById("form-compose-msg").onsubmit = async (e) => {
      e.preventDefault();
      const dest = document.getElementById("compose-destinatario").value;
      const asunto = document.getElementById("compose-asunto").value;
      const cuerpo = document.getElementById("compose-cuerpo").value;

      const res = await bridge.enviarMensaje(cursoId, dest, asunto, cuerpo);
      if (res.ok) {
        alert("¡Mensaje enviado con éxito!");
        await this._cargarListaMensajes();
      } else {
        alert("Error al enviar: " + (res.error || "Fallo en la comunicación"));
      }
    };
  }

  _mostrarFormularioRespuesta(msg) {
    const cursoId = state.selectedCurso?.id;
    const viewArea = document.getElementById("mensajes-view-area");
    if (!viewArea) return;

    viewArea.innerHTML = `
      <div class="p-5 bg-discord-channellist border border-discord-border rounded-xl space-y-4">
        <div class="flex items-center justify-between pb-2 border-b border-discord-border">
          <h3 class="text-sm font-bold text-discord-textHeader">Responder a: ${msg.remitente}</h3>
          <button id="btn-cancelar-resp" class="px-2.5 py-1 text-xs text-discord-textMuted hover:text-white">Cancelar</button>
        </div>

        <form id="form-resp-msg" class="space-y-3">
          <div>
            <label class="block text-[11px] font-bold text-discord-textMuted uppercase mb-1">Asunto</label>
            <input type="text" id="resp-asunto" value="Re: ${msg.asunto}" required
              class="w-full px-3 py-2 bg-discord-serverbar text-discord-textHeader rounded-lg border border-discord-border focus:outline-none focus:border-discord-accent text-xs">
          </div>

          <div>
            <label class="block text-[11px] font-bold text-discord-textMuted uppercase mb-1">Respuesta</label>
            <textarea id="resp-cuerpo" required rows="6" placeholder="Escribe tu respuesta..."
              class="w-full px-3 py-2 bg-discord-serverbar text-discord-textHeader rounded-lg border border-discord-border focus:outline-none focus:border-discord-accent text-xs resize-none"></textarea>
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button type="submit" class="px-4 py-2 bg-discord-accent hover:bg-discord-accentHover text-white text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 shadow-md shadow-discord-accent/20">
              <i class="ph-bold ph-paper-plane-tilt"></i> Enviar Respuesta
            </button>
          </div>
        </form>
      </div>
    `;

    document.getElementById("btn-cancelar-resp").onclick = () => this._mostrarDetalleMensaje(msg.id);
    document.getElementById("form-resp-msg").onsubmit = async (e) => {
      e.preventDefault();
      const asunto = document.getElementById("resp-asunto").value;
      const cuerpo = document.getElementById("resp-cuerpo").value;

      const res = await bridge.responderMensaje(cursoId, msg.id, msg.destinatario_id || "", asunto, cuerpo);
      if (res.ok) {
        alert("¡Respuesta enviada con éxito!");
        await this._cargarListaMensajes();
      } else {
        alert("Error al responder: " + (res.error || "Fallo en la comunicación"));
      }
    };
  }

  _mostrarFormularioReenvio(msg) {
    const cursoId = state.selectedCurso?.id;
    const viewArea = document.getElementById("mensajes-view-area");
    if (!viewArea) return;

    const contactos = [...(state.contactos.docentes || []), ...(state.contactos.alumnos || [])];

    viewArea.innerHTML = `
      <div class="p-5 bg-discord-channellist border border-discord-border rounded-xl space-y-4">
        <div class="flex items-center justify-between pb-2 border-b border-discord-border">
          <h3 class="text-sm font-bold text-discord-textHeader">Reenviar Mensaje: ${msg.asunto}</h3>
          <button id="btn-cancelar-reenv" class="px-2.5 py-1 text-xs text-discord-textMuted hover:text-white">Cancelar</button>
        </div>

        <form id="form-reenv-msg" class="space-y-3">
          <div>
            <label class="block text-[11px] font-bold text-discord-textMuted uppercase mb-1">Destinatario</label>
            <select id="reenv-destinatario" required class="w-full px-3 py-2 bg-discord-serverbar text-discord-textHeader rounded-lg border border-discord-border focus:outline-none focus:border-discord-accent text-xs">
              <option value="">Selecciona destinatario...</option>
              ${contactos.map(c => `
                <option value="${c.id || c.dni || c.nombre}">${c.nombre} (${c.rol})</option>
              `).join("")}
            </select>
          </div>

          <div>
            <label class="block text-[11px] font-bold text-discord-textMuted uppercase mb-1">Asunto</label>
            <input type="text" id="reenv-asunto" value="Fwd: ${msg.asunto}" required
              class="w-full px-3 py-2 bg-discord-serverbar text-discord-textHeader rounded-lg border border-discord-border focus:outline-none focus:border-discord-accent text-xs">
          </div>

          <div>
            <label class="block text-[11px] font-bold text-discord-textMuted uppercase mb-1">Nota adicional (opcional)</label>
            <textarea id="reenv-nota" rows="4" placeholder="Agrega un comentario al reenvío..."
              class="w-full px-3 py-2 bg-discord-serverbar text-discord-textHeader rounded-lg border border-discord-border focus:outline-none focus:border-discord-accent text-xs resize-none"></textarea>
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button type="submit" class="px-4 py-2 bg-discord-accent hover:bg-discord-accentHover text-white text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 shadow-md shadow-discord-accent/20">
              <i class="ph-bold ph-paper-plane-tilt"></i> Reenviar Mensaje
            </button>
          </div>
        </form>
      </div>
    `;

    document.getElementById("btn-cancelar-reenv").onclick = () => this._mostrarDetalleMensaje(msg.id);
    document.getElementById("form-reenv-msg").onsubmit = async (e) => {
      e.preventDefault();
      const dest = document.getElementById("reenv-destinatario").value;
      const asunto = document.getElementById("reenv-asunto").value;
      const nota = document.getElementById("reenv-nota").value;

      const res = await bridge.reenviarMensaje(cursoId, msg.id, dest, asunto, nota);
      if (res.ok) {
        alert("¡Mensaje reenviado con éxito!");
        await this._cargarListaMensajes();
      } else {
        alert("Error al reenviar: " + (res.error || "Fallo en la comunicación"));
      }
    };
  }

  // ================= 7. #ASISTENTE-IA =================
  _renderIA() {
    this.container.innerHTML = `
      <div class="flex flex-col h-full max-w-3xl mx-auto">
        <div id="ia-chat-logs" class="flex-1 overflow-y-auto space-y-3 p-2">
          <div class="flex gap-3 items-start">
            <div class="w-8 h-8 rounded-full bg-discord-accent flex items-center justify-center text-white shrink-0">
              <i class="ph-bold ph-sparkle"></i>
            </div>
            <div class="bg-discord-channellist p-3 rounded-2xl text-xs text-discord-textNormal border border-discord-border max-w-xl">
              ¡Hola! Soy tu Asistente Académico del Campus Tello. Puedes consultarme dudas sobre tus materias, tareas o fechas.
            </div>
          </div>
        </div>

        <div class="pt-3 border-t border-discord-border flex gap-2">
          <input type="text" id="ia-input" placeholder="Pregúntale algo al Asistente IA..."
            class="flex-1 bg-discord-channellist text-discord-textHeader px-4 py-2.5 rounded-xl border border-discord-border focus:outline-none focus:border-discord-accent text-xs">
          <button id="btn-ia-send" class="px-4 py-2.5 bg-discord-accent hover:bg-discord-accentHover text-white rounded-xl text-xs font-bold transition-colors">
            Enviar
          </button>
        </div>
      </div>
    `;

    const input = document.getElementById("ia-input");
    const btn = document.getElementById("btn-ia-send");
    const logs = document.getElementById("ia-chat-logs");

    const sendMsg = async () => {
      const q = input.value.trim();
      if (!q) return;
      input.value = "";

      logs.innerHTML += `
        <div class="flex gap-3 items-start justify-end">
          <div class="bg-discord-accent p-3 rounded-2xl text-xs text-white max-w-xl">${q}</div>
        </div>
      `;
      logs.scrollTop = logs.scrollHeight;

      const res = await bridge.askIA(q);
      const respTxt = res?.data?.respuesta || res?.error || "No se pudo obtener respuesta de la IA.";

      logs.innerHTML += `
        <div class="flex gap-3 items-start">
          <div class="w-8 h-8 rounded-full bg-discord-accent flex items-center justify-center text-white shrink-0">
            <i class="ph-bold ph-sparkle"></i>
          </div>
          <div class="bg-discord-channellist p-3 rounded-2xl text-xs text-discord-textNormal border border-discord-border max-w-xl">${respTxt}</div>
        </div>
      `;
      logs.scrollTop = logs.scrollHeight;
    };

    btn.onclick = sendMsg;
    input.onkeydown = (e) => { if (e.key === "Enter") sendMsg(); };
  }
}
