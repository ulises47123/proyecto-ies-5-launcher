"""
ui/main_view.py — Vista principal post-login:
Sidebar de navegación con Salir accesible + Secciones (Mis Materias, Novedades, Asistente IA, Estadísticas, Ajustes).
Precarga en segundo plano, soporte de temas, filtrado de años académicos y apertura de novedades y contenidos.
Adaptado 100% para Windows con CustomTkinter.
"""
import threading
import webbrowser
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from ui.widgets import (make_label, make_btn, make_card, make_separator,
                        make_badge, make_header, clear_frame)
from ui.curso_detail import CursoDetailView
from ui.theme import (tema_actual, abrir_dialogo_tema, registrar_listener_tema,
                      desregistrar_listener_tema, cambiar_tema_predefinido, TEMAS_PREDEFINIDOS)
from backend.session import CampusSession
from backend.escritorio import get_escritorio, fmt_fecha, es_reciente
from backend.contactos import get_estadisticas, get_contactos
from backend import contactos as cont_mod
from backend import programa as prog_mod
from backend import mensajes as msg_mod
from ia.engine import IAEngine
from config import (cargar_api, guardar_api, cargar_config, guardar_config,
                    set_autoinicio_windows, cargar_cache, guardar_cache)

TIPOS_NOV = {
    "email":     ("📧", "Correo"),
    "prg_texto": ("📄", "Texto/Contenido"),
    "unidad":    ("📦", "Nueva Unidad"),
    "nota":      ("🎓", "Calificación"),
    "actividad": ("✏️", "Actividad"),
    "foro":      ("💬", "Foro"),
}


class MainView(ctk.CTkFrame):
    """Vista principal del campus."""

    def __init__(self, parent, sess: CampusSession, on_logout):
        t = tema_actual()
        super().__init__(parent, fg_color=t["bg"])
        self.parent = parent
        self.sess = sess
        self.on_logout = on_logout
        self.config = cargar_config()
        self.cache_data = cargar_cache()
        self.ia = IAEngine(sess)
        self.cursos = []
        self.novedades = []
        self._current_page_name = "materias"

        self._build()
        registrar_listener_tema(self._on_tema_update)
        
        # Carga inicial (lee de caché primero para respuesta instantánea)
        self._load_from_cache_if_available()
        self._load_datos()

    def destroy(self):
        desregistrar_listener_tema(self._on_tema_update)
        super().destroy()

    def _on_tema_update(self, t):
        self.configure(fg_color=t["bg"])
        self._refresh_ui()

    def _refresh_ui(self):
        for w in self.winfo_children():
            w.destroy()
        self._build()
        if self.cursos:
            self._show_cursos(self.cursos)
            self._show_novedades(self.novedades)
            self._show_estadisticas_locales()
        self._ir_a(self._current_page_name)

    # ══════════════════════════════════════════════════════════
    # CONSTRUCCIÓN DE LA INTERFAZ
    # ══════════════════════════════════════════════════════════
    def _build(self):
        t = tema_actual()

        # Layout horizontal principal: Sidebar izquierda + Contenido derecha
        self._build_sidebar()

        # Contenedor dinámico de páginas
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(side="right", fill="both", expand=True)

        # Páginas
        self._page_materias = self._build_materias_page()
        self._page_novedades = self._build_novedades_page()
        self._page_ia = self._build_ia_page()
        self._page_estadisticas = self._build_estadisticas_page()
        self._page_ajustes = self._build_ajustes_page()
        self._page_curso_detail = None

        self._ir_a("materias")

    # ── SIDEBAR ───────────────────────────────────────────────
    def _build_sidebar(self):
        t = tema_actual()
        self.sb = ctk.CTkFrame(self, width=220, fg_color=t["sidebar"], corner_radius=0, border_width=1, border_color=t["border"])
        self.sb.pack(side="left", fill="y")
        self.sb.pack_propagate(False)

        # Encabezado Sidebar
        hdr = ctk.CTkFrame(self.sb, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(24, 10))

        import os
        from PIL import Image
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Escudo-I.E.S.-N-5.png")
        if os.path.exists(icon_path):
            try:
                logo_sb_img = ctk.CTkImage(light_image=Image.open(icon_path), dark_image=Image.open(icon_path), size=(44, 44))
                lbl_sb_logo = ctk.CTkLabel(hdr, image=logo_sb_img, text="")
                lbl_sb_logo.pack(anchor="center", pady=(4, 6))
            except Exception:
                pass

        lbl_logo = make_label(hdr, "IES N°5 Tello", tipo="titulo", anchor="center")
        lbl_logo.pack(fill="x")

        lbl_sub = make_label(hdr, "Campus Virtual Oficial", tipo="subtitulo", anchor="center")
        lbl_sub.pack(fill="x", pady=(1, 0))

        # Nombre del alumno dinámico
        from backend.user import get_current_user
        user_info = get_current_user(self.sess)
        nom = user_info.get("nombre") or self.sess.nombre or self.sess.usuario or "Estudiante"
        self.lbl_nombre = make_label(hdr, f"👤 {nom}", tipo="blanco", wrap=185)
        self.lbl_nombre.pack(anchor="w", pady=(8, 0))

        sep1 = make_separator(self.sb)
        sep1.pack(fill="x", padx=16, pady=(8, 8))

        # Navegación principal
        lbl_sec = make_label(self.sb, "SECCIONES", tipo="seccion")
        lbl_sec.pack(anchor="w", padx=16, pady=(0, 4))

        self.nav_btns = {}
        nav_items = [
            ("materias",     "📚  Mis Materias"),
            ("novedades",    "🔔  Novedades"),
            ("ia",           "🤖  Asistente IA"),
            ("estadisticas", "📊  Estadísticas"),
            ("ajustes",      "⚙️  Ajustes"),
        ]

        for key, text in nav_items:
            btn = make_btn(
                self.sb, text,
                command=lambda k=key: self._ir_a(k),
                tipo="nav", width=188, height=34, anchor="w"
            )
            btn.pack(padx=16, pady=2)
            self.nav_btns[key] = btn

        sep2 = make_separator(self.sb)
        sep2.pack(fill="x", padx=16, pady=(8, 8))

        # Acciones: Actualizar y Salir justo debajo (Requerimiento 1.3)
        btn_ref = make_btn(
            self.sb, "🔄  Actualizar",
            command=self._refresh,
            tipo="nav", width=188, height=34, anchor="w"
        )
        btn_ref.pack(padx=16, pady=2)

        btn_out = make_btn(
            self.sb, "⏏  Cerrar sesión",
            command=self.on_logout,
            tipo="danger", width=188, height=34
        )
        btn_out.pack(padx=16, pady=(2, 6))

        # Espaciador vertical
        spacer = ctk.CTkFrame(self.sb, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # Estado inferior
        self.lbl_estado = make_label(self.sb, "⏳ Conectando...", tipo="subtitulo", anchor="center")
        self.lbl_estado.pack(fill="x", padx=16, pady=(0, 12))

    def _ir_a(self, key: str):
        self._current_page_name = key
        t = tema_actual()

        # Actualizar estilo activo en botones del menú
        for k, b in self.nav_btns.items():
            if k == key:
                b.configure(fg_color=t["accent"], hover_color=t["accent_hover"], text_color=t["btn_text"])
            else:
                b.configure(fg_color="transparent", hover_color=t["card"], text_color=t["text"])

        # Ocultar todas las páginas
        self._page_materias.pack_forget()
        self._page_novedades.pack_forget()
        self._page_ia.pack_forget()
        self._page_estadisticas.pack_forget()
        self._page_ajustes.pack_forget()
        if self._page_curso_detail:
            self._page_curso_detail.pack_forget()

        # Mostrar página seleccionada
        if key == "materias":
            self._page_materias.pack(fill="both", expand=True)
        elif key == "novedades":
            self._page_novedades.pack(fill="both", expand=True)
        elif key == "ia":
            self._page_ia.pack(fill="both", expand=True)
        elif key == "estadisticas":
            self._page_estadisticas.pack(fill="both", expand=True)
        elif key == "ajustes":
            self._page_ajustes.pack(fill="both", expand=True)

    # ── PÁGINA MATERIAS ────────────────────────────────────────
    def _build_materias_page(self):
        t = tema_actual()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        # Barra superior con Header y Selector de Paginación (Requerimiento 1.1)
        top_h = ctk.CTkFrame(frame, fg_color="transparent")
        top_h.pack(fill="x", padx=20, pady=(16, 6))

        left_h = ctk.CTkFrame(top_h, fg_color="transparent")
        left_h.pack(side="left", fill="x", expand=True)

        lbl_tit = make_label(left_h, "Mis Materias", tipo="titulo")
        lbl_tit.pack(anchor="w")

        lbl_sub = make_label(left_h, "Accede a los programas, contenido y calificaciones", tipo="subtitulo")
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Selector de Mostrar por página (6, 24, 48, 120 - Por defecto 120)
        right_h = ctk.CTkFrame(top_h, fg_color="transparent")
        right_h.pack(side="right")

        lbl_pag = make_label(right_h, "Mostrar:", tipo="subtitulo")
        lbl_pag.pack(side="left", padx=(0, 6))

        self.combo_pag = ctk.CTkOptionMenu(
            right_h,
            values=["6", "24", "48", "120 (Todas)"],
            fg_color=t["accent"],
            button_color=t["accent_hover"],
            text_color=t["btn_text"],
            width=110,
            height=32,
            command=self._on_cambio_paginacion
        )
        self.combo_pag.set("120 (Todas)")
        self.combo_pag.pack(side="left")

        sep = make_separator(frame)
        sep.pack(fill="x", padx=20, pady=(6, 10))

        self.scroll_cursos = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.scroll_cursos.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        lbl_sp = make_label(self.scroll_cursos, "⏳ Cargando materias del campus...", tipo="subtitulo")
        lbl_sp.pack(pady=20)
        return frame

    def _on_cambio_paginacion(self, valor):
        cant = 120
        if "6" in valor and "120" not in valor: cant = 6
        elif "24" in valor: cant = 24
        elif "48" in valor: cant = 48
        elif "120" in valor: cant = 120
        self._load_datos(page_size=cant)

    def _show_cursos(self, cursos):
        t = tema_actual()
        clear_frame(self.scroll_cursos)

        mostrar_anteriores = self.config.get("mostrar_materias_anteriores", False)

        # Filtrar materias por ciclo lectivo más reciente a menos que esté activada la opción
        if not mostrar_anteriores:
            anios = [c.get("anio") for c in cursos if c.get("anio")]
            max_anio = max(anios) if anios else None
            if max_anio:
                cursos_visibles = [c for c in cursos if c.get("anio") == max_anio or str(max_anio) in c.get("nombre", "")]
            else:
                cursos_visibles = cursos
            if not cursos_visibles:  # Fallback
                cursos_visibles = cursos
        else:
            cursos_visibles = cursos

        if not cursos_visibles:
            lbl = make_label(self.scroll_cursos, "ℹ No se encontraron materias inscriptas para el ciclo lectivo actual.", tipo="subtitulo")
            lbl.pack(pady=20)
            return

        for c in cursos_visibles:
            card = make_card(self.scroll_cursos, fg_color=t["card"], corner_radius=10, border_color=t["border"])
            card.pack(fill="x", pady=6, padx=2)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=16, pady=14)

            # Barra de color distintiva de la materia
            color_c = c.get("color", t["accent"])
            bar = ctk.CTkFrame(inner, width=5, height=45, fg_color=color_c, corner_radius=2)
            bar.pack(side="left", padx=(0, 12))

            # Información
            info = ctk.CTkFrame(inner, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True)

            lbl_nom = make_label(info, c["nombre"], tipo="blanco", wrap=520)
            lbl_nom.pack(anchor="w")

            meta = []
            if c.get("ultimo_acceso"):
                meta.append(f"Último acceso: {fmt_fecha(c['ultimo_acceso'])}")
            if c.get("items_obl"):
                meta.append(f"Ítems obligatorios: {c['items_obl']}")
            if meta:
                lbl_meta = make_label(info, "   •   ".join(meta), tipo="subtitulo")
                lbl_meta.pack(anchor="w", pady=(3, 0))

            # Avance si está disponible
            av = c.get("avance")
            if av is not None:
                av_row = ctk.CTkFrame(info, fg_color="transparent")
                av_row.pack(anchor="w", fill="x", pady=(6, 0))

                pb = ctk.CTkProgressBar(
                    av_row, width=160, height=8,
                    progress_color=t["success"],
                    fg_color=t["item_bg"]
                )
                pb.set(min(av / 100.0, 1.0))
                pb.pack(side="left", padx=(0, 8))

                lbl_av = make_label(av_row, f"{av}% completado", tipo="subtitulo")
                lbl_av.pack(side="left")

            # Botón Entrar
            btn_entrar = make_btn(
                inner, "Entrar →",
                command=lambda curso=c: self._abrir_curso(curso),
                tipo="primary", width=95, height=34
            )
            btn_entrar.pack(side="right", padx=(10, 0))

    def _abrir_curso(self, curso: dict):
        if self._page_curso_detail:
            self._page_curso_detail.destroy()

        # Obtener cache detallado si existe para carga instantánea (Requerimiento 3.3)
        cached_mat = self.cache_data.get("materias_detalle", {}).get(str(curso["id"]), {})

        self._page_curso_detail = CursoDetailView(
            self.main_container,
            self.sess,
            curso,
            on_back=self._volver_a_materias,
            cached_data=cached_mat
        )
        self._ir_a("none")
        self._page_curso_detail.pack(fill="both", expand=True)

    def _volver_a_materias(self):
        if self._page_curso_detail:
            self._page_curso_detail.pack_forget()
        self._ir_a("materias")

    # ── PÁGINA NOVEDADES ───────────────────────────────────────
    def _build_novedades_page(self):
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        make_header(frame, "Novedades del Campus", "Notificaciones de actividades, mensajes y avisos ordenados por fecha.")

        self.scroll_novs = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.scroll_novs.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        lbl_sp = make_label(self.scroll_novs, "⏳ Cargando novedades...", tipo="subtitulo")
        lbl_sp.pack(pady=20)
        return frame

    def _show_novedades(self, novedades):
        t = tema_actual()
        clear_frame(self.scroll_novs)

        if not novedades:
            lbl = make_label(self.scroll_novs, "✅ No hay novedades registradas en el campus.", tipo="subtitulo")
            lbl.pack(pady=20)
            return

        # Requerimiento 6: Ordenar novedades de más reciente a más antigua
        novs_ordenadas = sorted(novedades, key=lambda x: str(x.get("fecha", "")), reverse=True)

        for n in novs_ordenadas:
            reciente = es_reciente(n.get("fecha", ""), 7)
            edad = fmt_fecha(n.get("fecha", ""))
            icon, tipo_txt = TIPOS_NOV.get(n.get("clase"), ("🔔", n.get("clase", "Aviso")))

            card = make_card(
                self.scroll_novs,
                fg_color=t["card"],
                corner_radius=10,
                border_color=t["accent"] if reciente else t["border"]
            )
            card.pack(fill="x", pady=5, padx=2)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=16, pady=12)

            # Barra lateral de estado
            bar_color = t["accent"] if reciente else t["border"]
            bar = ctk.CTkFrame(inner, width=4, height=40, fg_color=bar_color, corner_radius=2)
            bar.pack(side="left", padx=(0, 12))

            body = ctk.CTkFrame(inner, fg_color="transparent")
            body.pack(side="left", fill="x", expand=True)

            # Fila superior (tipo + badge de antigüedad)
            top_r = ctk.CTkFrame(body, fg_color="transparent")
            top_r.pack(fill="x")

            lbl_t = make_label(top_r, f"{icon}  {tipo_txt.upper()}", tipo="seccion")
            lbl_t.pack(side="left")

            badge_txt = "🔴 Reciente" if reciente else "🔘 Anterior"
            badge_bg = t["accent"] if reciente else t["item_bg"]
            badge_tc = "#ffffff" if reciente else t["muted"]
            badge = make_badge(top_r, badge_txt, bg_color=badge_bg, text_color=badge_tc)
            badge.pack(side="right")

            # Título del ítem en negrita destacada (Requerimiento 6)
            nombre_item = n.get("nombre_item") or n.get("nombre_unidad") or tipo_txt
            if nombre_item:
                lbl_it = ctk.CTkLabel(
                    body, text=nombre_item,
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=t["text"],
                    wraplength=480, justify="left"
                )
                lbl_it.pack(anchor="w", pady=(3, 0))

            # Curso y fecha relativa
            bot_r = ctk.CTkFrame(body, fg_color="transparent")
            bot_r.pack(fill="x", pady=(4, 0))

            curso = n.get("nombre_curso") or ""
            if curso:
                lbl_c = make_label(bot_r, f"📍 {curso}", tipo="subtitulo", wrap=380)
                lbl_c.pack(side="left")

            lbl_e = make_label(bot_r, f"📅 {edad}", tipo="subtitulo")
            lbl_e.pack(side="right")

            # Botón para abrir la novedad y ver su contenido completo (Requerimiento 6)
            btn_ver = make_btn(
                inner, "Ver novedad →",
                command=lambda nov=n: self._abrir_novedad_completa(nov),
                tipo="primary", width=105, height=30
            )
            btn_ver.pack(side="right", padx=(10, 0))

    def _abrir_novedad_completa(self, n: dict):
        """Abre un modal para ver el contenido completo de la novedad."""
        t = tema_actual()
        top = ctk.CTkToplevel(self)
        top.title("Detalle de Novedad")
        top.geometry("620x500")
        top.transient(self)
        top.grab_set()

        hdr = ctk.CTkFrame(top, fg_color=t["sidebar"], corner_radius=0)
        hdr.pack(fill="x")

        tit = n.get("nombre_item") or n.get("nombre_unidad") or "Novedad del Campus"
        lbl_t = ctk.CTkLabel(
            hdr, text=tit,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=t["text"],
            wraplength=560, justify="left"
        )
        lbl_t.pack(padx=20, pady=(16, 4), anchor="w")

        lbl_s = make_label(hdr, f"Materia: {n.get('nombre_curso', '')}  |  Fecha: {fmt_fecha(n.get('fecha', ''))}", tipo="subtitulo")
        lbl_s.pack(padx=20, pady=(0, 14), anchor="w")

        content = ctk.CTkScrollableFrame(top, fg_color=t["bg"])
        content.pack(fill="both", expand=True, padx=16, pady=12)

        lbl_carg = make_label(content, "⏳ Cargando contenido del campus...", tipo="subtitulo")
        lbl_carg.pack(pady=30)

        def run():
            link = n.get("link", "")
            full_url = self.sess.url(link) if link and not link.startswith("http") else link
            resultado = {
                "remitente": "",
                "fecha": fmt_fecha(n.get("fecha", "")),
                "cuerpo": "",
                "adjuntos": [],
                "links": []
            }
            if "webmail.cgi" in link or n.get("clase") == "email":
                data = msg_mod.get_detalle_mensaje(self.sess, link, n.get("id_curso", ""))
                resultado["remitente"] = data.get("remitente", "")
                resultado["fecha"] = data.get("fecha") or resultado["fecha"]
                resultado["cuerpo"] = data.get("cuerpo", "")
                resultado["adjuntos"] = data.get("adjuntos", [])
            elif full_url:
                cuerpo_dict = prog_mod.get_contenido_texto(self.sess, full_url)
                if isinstance(cuerpo_dict, dict):
                    resultado["cuerpo"] = cuerpo_dict.get("texto", "")
                    resultado["links"] = cuerpo_dict.get("links", [])
                else:
                    resultado["cuerpo"] = str(cuerpo_dict)
            else:
                resultado["cuerpo"] = f"Tipo: {n.get('clase')}\nÍtem: {tit}\nCurso: {n.get('nombre_curso')}"

            self.after(0, self._render_modal_novedad, content, resultado, top)

        threading.Thread(target=run, daemon=True).start()

    def _render_modal_novedad(self, parent, data: dict, top_win):
        t = tema_actual()
        clear_frame(parent)

        # Si hay remitente y fecha, mostrar cabecera
        if data.get("remitente") or data.get("fecha"):
            card_info = make_card(parent, fg_color=t["item_bg"], corner_radius=8, border_color=t["border"])
            card_info.pack(fill="x", pady=(0, 8))
            box_i = ctk.CTkFrame(card_info, fg_color="transparent")
            box_i.pack(fill="x", padx=14, pady=10)

            if data.get("remitente"):
                lbl_rem = make_label(box_i, f"👤 De: {data['remitente']}", tipo="seccion", wrap=540)
                lbl_rem.pack(anchor="w")
            if data.get("fecha"):
                lbl_f = make_label(box_i, f"📅 Fecha: {data['fecha']}", tipo="subtitulo")
                lbl_f.pack(anchor="w", pady=(2, 0))

        # Cuerpo del mensaje / contenido
        card_c = make_card(parent, fg_color=t["card"], corner_radius=8, border_color=t["border"])
        card_c.pack(fill="both", expand=True, padx=2, pady=4)

        cuerpo_txt = data.get("cuerpo", "") or "(Sin contenido en el mensaje)"
        lbl = make_label(card_c, cuerpo_txt, tipo="blanco", wrap=540)
        lbl.pack(padx=16, pady=16, anchor="w")

        # Adjuntos
        for adj in data.get("adjuntos", []):
            btn_adj = make_btn(
                card_c, f"📥 {adj['nombre']}",
                command=lambda u=adj['url']: webbrowser.open(u),
                tipo="primary", height=32
            )
            btn_adj.pack(fill="x", padx=16, pady=(0, 8))

        # Enlaces
        for lk in data.get("links", []):
            btn_l = make_btn(
                card_c, f"🔗 {lk['texto']}",
                command=lambda u=lk['url']: webbrowser.open(u),
                tipo="flat", height=30
            )
            btn_l.pack(fill="x", padx=16, pady=(0, 6))

        bot = ctk.CTkFrame(top_win, fg_color="transparent")
        bot.pack(fill="x", padx=16, pady=(0, 12))
        btn_c = make_btn(bot, "Cerrar", command=top_win.destroy, tipo="primary", height=34)
        btn_c.pack(fill="x")

    # ── PÁGINA IA ─────────────────────────────────────────────
    def _build_ia_page(self):
        t = tema_actual()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")

        # Header
        hdr_frame = ctk.CTkFrame(frame, fg_color="transparent")
        hdr_frame.pack(fill="x", padx=20, pady=(16, 6))

        left = ctk.CTkFrame(hdr_frame, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        lbl_t = make_label(left, "🤖 Asistente Virtual del Campus", tipo="titulo")
        lbl_t.pack(anchor="w")

        self.lbl_api_estado = make_label(left, "Modo local inteligente", tipo="subtitulo")
        self.lbl_api_estado.pack(anchor="w", pady=(2, 0))

        sep = make_separator(frame)
        sep.pack(fill="x", padx=20, pady=(4, 10))

        # Historial de Chat (Ocupa el espacio central)
        self.chat_scroll = ctk.CTkScrollableFrame(frame, fg_color=t["bg"])
        self.chat_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self._ia_msg("¡Hola! Soy tu asistente del campus IES N°5 Tello.\n\n"
                     "Podés consultarme sobre tus materias actuales, novedades, progreso o actividades.")

        # Requerimiento 8.1: Botones de sugerencia en la parte inferior, justo arriba del input
        chips_frame = ctk.CTkFrame(frame, fg_color="transparent")
        chips_frame.pack(fill="x", padx=20, pady=(0, 8))

        preguntas_rapidas = [
            "¿Qué materias tengo?",
            "Novedades recientes",
            "¿Cuál es mi progreso?",
            "Actividades pendientes",
            "Actividades entregadas"
        ]
        for prg in preguntas_rapidas:
            btn_chip = make_btn(
                chips_frame, prg,
                command=lambda p=prg: self._ia_quick_send(p),
                tipo="flat", height=28
            )
            btn_chip.pack(side="left", padx=3)

        # Input inferior
        input_box = ctk.CTkFrame(frame, fg_color="transparent")
        input_box.pack(fill="x", padx=20, pady=(0, 16))

        self.ia_entry = ctk.CTkEntry(
            input_box,
            placeholder_text="Escribí tu pregunta aquí y presioná Enter...",
            height=40,
            corner_radius=8,
            fg_color=t["input_bg"],
            border_color=t["border"],
            text_color=t["text"],
            placeholder_text_color=t["muted"],
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.ia_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.ia_entry.bind("<Return>", lambda _: self._ia_send())

        self.btn_send = make_btn(
            input_box, "Enviar",
            command=self._ia_send,
            tipo="primary", width=90, height=40
        )
        self.btn_send.pack(side="right")

        # Cargar estado de API (verificar que no sea vacía)
        provider, key = cargar_api()
        if key and len(key.strip()) > 10:
            self.ia.api_key = key.strip()
            self.ia.api_prov = provider
            self.lbl_api_estado.configure(text=f"API Externa: {provider.upper()} Activa ✅")
        else:
            self.ia.api_key = ""
            self.lbl_api_estado.configure(text="Modo local inteligente")

        return frame

    def _ia_quick_send(self, txt):
        self.ia_entry.delete(0, "end")
        self.ia_entry.insert(0, txt)
        self._ia_send()

    def _ia_msg(self, txt):
        t = tema_actual()
        bubble = make_card(self.chat_scroll, fg_color=t["card"], corner_radius=12, border_color=t["border"])
        bubble.pack(fill="x", pady=6, padx=(0, 60), anchor="w")

        # CTkTextbox seleccionable
        txt_box = ctk.CTkTextbox(
            bubble,
            fg_color="transparent",
            text_color=t["text"],
            wrap="word",
            activate_scrollbars=False,
            border_width=0,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        txt_box.insert("1.0", txt)
        txt_box.configure(state="disabled")
        txt_box.pack(fill="x", padx=14, pady=(12, 4), anchor="w")

        btn_copy = make_btn(
            bubble, "📋 Copiar",
            command=lambda: self._copiar_texto_chat(txt),
            tipo="flat", width=65, height=22
        )
        btn_copy.pack(padx=14, pady=(0, 8), anchor="e")
        self._scroll_chat_to_bottom()

    def _copiar_texto_chat(self, txt):
        try:
            self.clipboard_clear()
            self.clipboard_append(txt)
            # Notificación visual estilizada con el tema actual
            self._mostrar_toast("Texto copiado al portapapeles ✅")
        except Exception:
            pass

    def _mostrar_toast(self, mensaje: str):
        t = tema_actual()
        toast = ctk.CTkToplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(fg_color=t["card"])

        # Posicionar centrado sobre la ventana
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 130
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 25
        toast.geometry(f"260x50+{x}+{y}")

        card = make_card(toast, fg_color=t["sidebar"], corner_radius=8, border_color=t["accent"], border_width=1)
        card.pack(fill="both", expand=True, padx=2, pady=2)
        lbl = make_label(card, mensaje, tipo="blanco", anchor="center")
        lbl.pack(expand=True)

        toast.after(1400, toast.destroy)

    def _user_msg(self, txt):
        t = tema_actual()
        bubble = make_card(self.chat_scroll, fg_color=t["accent"], corner_radius=12, border_color=t["accent_hover"])
        bubble.pack(fill="x", pady=6, padx=(60, 0), anchor="e")

        lbl = make_label(bubble, txt, tipo="blanco", wrap=540)
        lbl.configure(text_color=t["btn_text"])
        lbl.pack(padx=16, pady=12, anchor="e")
        self._scroll_chat_to_bottom()

    def _scroll_chat_to_bottom(self):
        """Desplaza automáticamente el scroll al final del chat."""
        try:
            self.chat_scroll.after(10, lambda: self.chat_scroll._parent_canvas.yview_moveto(1.0))
        except Exception:
            pass

    def _ia_send(self):
        txt = self.ia_entry.get().strip()
        if not txt:
            return

        self.ia_entry.delete(0, "end")
        self.ia_entry.configure(state="disabled")
        self.btn_send.configure(state="disabled")
        self._user_msg(txt)

        # Animación de tres puntos escribiendo...
        t = tema_actual()
        self._thinking_bubble = make_card(self.chat_scroll, fg_color=t["card"], corner_radius=12, border_color=t["border"])
        self._thinking_bubble.pack(fill="x", pady=6, padx=(0, 60), anchor="w")
        self._lbl_think = make_label(self._thinking_bubble, "⏳ Asistente escribiendo .", tipo="subtitulo")
        self._lbl_think.pack(padx=16, pady=12, anchor="w")
        self._anim_step = 0
        self._anim_running = True
        self._animar_thinking()
        self._scroll_chat_to_bottom()

        def run():
            resp = self.ia.responder(txt)
            self.after(0, self._on_ia_resp, resp)

        threading.Thread(target=run, daemon=True).start()

    def _animar_thinking(self):
        if not hasattr(self, "_anim_running") or not self._anim_running:
            return
        dots = "." * ((self._anim_step % 3) + 1)
        if hasattr(self, "_lbl_think") and self._lbl_think.winfo_exists():
            self._lbl_think.configure(text=f"⏳ Asistente escribiendo {dots}")
            self._anim_step += 1
            self.after(400, self._animar_thinking)

    def _on_ia_resp(self, resp):
        self._anim_running = False
        if hasattr(self, "_thinking_bubble") and self._thinking_bubble:
            try:
                self._thinking_bubble.destroy()
            except Exception:
                pass
            self._thinking_bubble = None

        self.ia_entry.configure(state="normal")
        self.btn_send.configure(state="normal")
        self.ia_entry.focus()
        self._ia_msg(resp)

    # ── PÁGINA ESTADÍSTICAS ────────────────────────────────────
    def _build_estadisticas_page(self):
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        make_header(frame, "Estadísticas y Rendimiento", "Progreso en las materias del ciclo lectivo actual.")

        self.scroll_stats = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.scroll_stats.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        lbl_sp = make_label(self.scroll_stats, "⏳ Calculando estadísticas...", tipo="subtitulo")
        lbl_sp.pack(pady=20)
        return frame

    def _show_estadisticas_locales(self):
        t = tema_actual()
        clear_frame(self.scroll_stats)

        # Mostrar materias del ciclo lectivo más reciente que tengan avance > 0
        anios = [c.get("anio") for c in self.cursos if c.get("anio")]
        max_anio = max(anios) if anios else None

        if max_anio:
            cursos_con_avance = [
                c for c in self.cursos
                if (c.get("anio") == max_anio or str(max_anio) in c.get("nombre", "")) and c.get("avance") is not None and c.get("avance") > 0
            ]
            if not cursos_con_avance:
                cursos_con_avance = [c for c in self.cursos if c.get("anio") == max_anio or str(max_anio) in c.get("nombre", "")]
        else:
            cursos_con_avance = [c for c in self.cursos if c.get("avance") is not None and c.get("avance") > 0]
            if not cursos_con_avance:
                cursos_con_avance = self.cursos

        lbl_hdr = make_label(self.scroll_stats, "AVANCE POR ASIGNATURA (AÑO ACTUAL)", tipo="seccion")
        lbl_hdr.pack(anchor="w", padx=4, pady=(4, 10))

        if not cursos_con_avance:
            lbl_v = make_label(self.scroll_stats, "ℹ No se registra avance aún en las materias del ciclo actual.", tipo="subtitulo")
            lbl_v.pack(pady=20)
            return

        for c in cursos_con_avance:
            row = make_card(self.scroll_stats, fg_color=t["item_bg"], corner_radius=8, border_color=t["border"])
            row.pack(fill="x", pady=4, padx=2)

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=12)

            left = ctk.CTkFrame(inner, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True)

            lbl_nom = make_label(left, c["nombre"], tipo="blanco", wrap=450)
            lbl_nom.pack(anchor="w")

            ua = c.get("ultimo_acceso")
            if ua:
                lbl_ua = make_label(left, f"Último acceso: {fmt_fecha(ua)}", tipo="subtitulo")
                lbl_ua.pack(anchor="w", pady=(2, 0))

            av = c.get("avance") or 0
            right = ctk.CTkFrame(inner, fg_color="transparent")
            right.pack(side="right", padx=10)

            pb = ctk.CTkProgressBar(right, width=160, height=10, progress_color=t["success"], fg_color=t["card"])
            pb.set(min(av / 100.0, 1.0))
            pb.pack(side="left", padx=(0, 10))

            lbl_av = make_label(right, f"{av}%", tipo="titulo_sm")
            lbl_av.pack(side="right")

    # ── PÁGINA AJUSTES (Requerimiento 1.2) ─────────────────────
    def _build_ajustes_page(self):
        t = tema_actual()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        make_header(frame, "Ajustes y Configuración", "Personalizá el tema, intervalos de actualización e inicio del sistema.")

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # 1. Selector de Tema
        card_tema = make_card(scroll, fg_color=t["card"], corner_radius=10, border_color=t["border"])
        card_tema.pack(fill="x", pady=6)

        inner_t = ctk.CTkFrame(card_tema, fg_color="transparent")
        inner_t.pack(fill="x", padx=16, pady=14)

        lbl_t_h = make_label(inner_t, "🎨 APARIENCIA Y TEMAS", tipo="seccion")
        lbl_t_h.pack(anchor="w", pady=(0, 8))

        temas_nombres = list(TEMAS_PREDEFINIDOS.keys())
        combo_tema = ctk.CTkOptionMenu(
            inner_t,
            values=temas_nombres,
            fg_color=t["accent"],
            button_color=t["accent_hover"],
            text_color=t["btn_text"],
            height=36
        )
        combo_tema.set(self.config.get("tema", temas_nombres[0]))
        combo_tema.pack(fill="x", pady=(0, 10))

        def on_theme_change(choice):
            cambiar_tema_predefinido(choice)
            self.config["tema"] = choice
            guardar_config(self.config)

        combo_tema.configure(command=on_theme_change)

        btn_cust = make_btn(
            inner_t, "Personalizar Colores Individuales...",
            command=lambda: abrir_dialogo_tema(self.parent, self._refresh_ui),
            tipo="flat", height=32
        )
        btn_cust.pack(fill="x")

        # 2. Intervalo de actualización
        card_inter = make_card(scroll, fg_color=t["card"], corner_radius=10, border_color=t["border"])
        card_inter.pack(fill="x", pady=6)

        inner_i = ctk.CTkFrame(card_inter, fg_color="transparent")
        inner_i.pack(fill="x", padx=16, pady=14)

        lbl_i_h = make_label(inner_i, "⏱️ ACTUALIZACIÓN AUTOMÁTICA", tipo="seccion")
        lbl_i_h.pack(anchor="w", pady=(0, 8))

        lbl_i_desc = make_label(inner_i, "Intervalo para sincronizar novedades y mensajes en segundo plano:", tipo="subtitulo")
        lbl_i_desc.pack(anchor="w", pady=(0, 6))

        inter_map = {
            "Cada 5 minutos": 5,
            "Cada 10 minutos (Recomendado)": 10,
            "Cada 30 minutos": 30,
            "Cada 1 hora": 60,
            "Desactivado (Solo manual)": 0
        }
        combo_inter = ctk.CTkOptionMenu(
            inner_i,
            values=list(inter_map.keys()),
            fg_color=t["accent"],
            button_color=t["accent_hover"],
            text_color=t["btn_text"],
            height=36
        )
        curr_min = self.config.get("intervalo_actualizacion", 10)
        for k, v in inter_map.items():
            if v == curr_min:
                combo_inter.set(k)
                break
        combo_inter.pack(fill="x", pady=(0, 6))

        def on_inter_change(choice):
            self.config["intervalo_actualizacion"] = inter_map[choice]
            guardar_config(self.config)

        combo_inter.configure(command=on_inter_change)

        # 3. Opciones de Materias y Sistema
        card_opts = make_card(scroll, fg_color=t["card"], corner_radius=10, border_color=t["border"])
        card_opts.pack(fill="x", pady=6)

        inner_o = ctk.CTkFrame(card_opts, fg_color="transparent")
        inner_o.pack(fill="x", padx=16, pady=14)

        lbl_o_h = make_label(inner_o, "⚙️ PREFERENCIAS DEL SISTEMA", tipo="seccion")
        lbl_o_h.pack(anchor="w", pady=(0, 8))

        chk_ant = ctk.CTkCheckBox(
            inner_o,
            text="Mostrar materias de años anteriores en el listado",
            text_color=t["text"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        if self.config.get("mostrar_materias_anteriores", False):
            chk_ant.select()
        chk_ant.pack(anchor="w", pady=4)

        chk_sys = ctk.CTkCheckBox(
            inner_o,
            text="Iniciar automáticamente con Windows",
            text_color=t["text"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        if self.config.get("iniciar_con_sistema", False):
            chk_sys.select()
        chk_sys.pack(anchor="w", pady=4)

        def guardar_preferencias():
            self.config["mostrar_materias_anteriores"] = (chk_ant.get() == 1)
            self.config["iniciar_con_sistema"] = (chk_sys.get() == 1)
            guardar_config(self.config)
            set_autoinicio_windows(chk_sys.get() == 1)
            self._show_cursos(self.cursos)
            messagebox.showinfo("Ajustes Guardados", "Preferencias guardadas correctamente.")

        btn_g_opts = make_btn(inner_o, "Guardar Preferencias", command=guardar_preferencias, tipo="primary", height=34)
        btn_g_opts.pack(fill="x", pady=(12, 0))

        # 4. Credenciales de Facebook Institucional (Fase 5)
        from config import guardar_fb_creds, cargar_fb_creds, borrar_fb_creds
        card_fb = make_card(scroll, fg_color=t["card"], corner_radius=10, border_color=t["border"])
        card_fb.pack(fill="x", pady=6)

        inner_fb = ctk.CTkFrame(card_fb, fg_color="transparent")
        inner_fb.pack(fill="x", padx=16, pady=14)

        lbl_fb_h = make_label(inner_fb, "🌐 CREDENCIALES DE FACEBOOK INSTITUCIONAL", tipo="seccion")
        lbl_fb_h.pack(anchor="w", pady=(0, 4))

        lbl_fb_desc = make_label(
            inner_fb,
            "Permite al asistente IA y al scraper acceder a las publicaciones y comunicados de Facebook.\n"
            "Las credenciales se almacenan de forma segura y cifrada con DPAPI de Windows.",
            tipo="subtitulo",
            wrap=550
        )
        lbl_fb_desc.pack(anchor="w", pady=(0, 8))

        fb_u_saved, fb_p_saved = cargar_fb_creds()

        lbl_fbu = make_label(inner_fb, "Usuario o Correo de Facebook:", tipo="subtitulo")
        lbl_fbu.pack(anchor="w", pady=(2, 2))

        entry_fb_user = ctk.CTkEntry(
            inner_fb,
            placeholder_text="correo@ejemplo.com o número de teléfono",
            fg_color=t["input_bg"],
            border_color=t["border"],
            text_color=t["text"],
            height=34
        )
        if fb_u_saved:
            entry_fb_user.insert(0, fb_u_saved)
        entry_fb_user.pack(fill="x", pady=(0, 6))

        lbl_fbp = make_label(inner_fb, "Contraseña de Facebook:", tipo="subtitulo")
        lbl_fbp.pack(anchor="w", pady=(2, 2))

        entry_fb_pass = ctk.CTkEntry(
            inner_fb,
            placeholder_text="Contraseña",
            show="•",
            fg_color=t["input_bg"],
            border_color=t["border"],
            text_color=t["text"],
            height=34
        )
        if fb_p_saved:
            entry_fb_pass.insert(0, fb_p_saved)
        entry_fb_pass.pack(fill="x", pady=(0, 10))

        row_fb_btns = ctk.CTkFrame(inner_fb, fg_color="transparent")
        row_fb_btns.pack(fill="x")

        def guardar_fb():
            u = entry_fb_user.get().strip()
            p = entry_fb_pass.get().strip()
            if u and p:
                guardar_fb_creds(u, p)
                messagebox.showinfo("Facebook", "Credenciales de Facebook guardadas de forma segura (DPAPI).")
            else:
                messagebox.showwarning("Facebook", "Por favor ingresa usuario y contraseña de Facebook.")

        def olvidar_fb():
            borrar_fb_creds()
            entry_fb_user.delete(0, "end")
            entry_fb_pass.delete(0, "end")
            messagebox.showinfo("Facebook", "Credenciales de Facebook eliminadas.")

        btn_g_fb = make_btn(row_fb_btns, "Guardar credenciales de Facebook", command=guardar_fb, tipo="primary", height=34)
        btn_g_fb.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_o_fb = make_btn(row_fb_btns, "Olvidar credenciales", command=olvidar_fb, tipo="danger", height=34)
        btn_o_fb.pack(side="right", fill="x", expand=True, padx=(6, 0))

        # 5. Clave de API del Asistente IA (Fase 6)
        from config import guardar_api_key, cargar_api_key, borrar_api_key
        card_api = make_card(scroll, fg_color=t["card"], corner_radius=10, border_color=t["border"])
        card_api.pack(fill="x", pady=6)

        inner_api = ctk.CTkFrame(card_api, fg_color="transparent")
        inner_api.pack(fill="x", padx=16, pady=14)

        lbl_api_h = make_label(inner_api, "🤖 CLAVE DE API DEL ASISTENTE IA", tipo="seccion")
        lbl_api_h.pack(anchor="w", pady=(0, 4))

        lbl_api_desc = make_label(
            inner_api,
            "Permite activar el modo avanzado de IA externa (Google Gemini / OpenAI) para responder consultas complejas.\n"
            "La clave se almacena de forma segura y cifrada con DPAPI de Windows.",
            tipo="subtitulo",
            wrap=550
        )
        lbl_api_desc.pack(anchor="w", pady=(0, 8))

        api_key_actual = cargar_api_key()
        estado_texto = "Clave configurada: Sí (Activa)" if api_key_actual else "Clave configurada: No (Modo local)"
        lbl_api_status = make_label(
            inner_api,
            estado_texto,
            tipo="subtitulo"
        )
        lbl_api_status.configure(text_color=t["success"] if api_key_actual else t["muted"])
        lbl_api_status.pack(anchor="w", pady=(0, 6))

        lbl_k = make_label(inner_api, "Clave de API:", tipo="subtitulo")
        lbl_k.pack(anchor="w", pady=(2, 2))

        entry_api_key = ctk.CTkEntry(
            inner_api,
            placeholder_text="Ingresa tu clave de API (ej. AIzaSy... o sk-...)",
            show="*",
            fg_color=t["input_bg"],
            border_color=t["border"],
            text_color=t["text"],
            height=34
        )
        if api_key_actual:
            entry_api_key.insert(0, api_key_actual)
        entry_api_key.pack(fill="x", pady=(0, 10))

        row_api_btns = ctk.CTkFrame(inner_api, fg_color="transparent")
        row_api_btns.pack(fill="x")

        def guardar_clave_api():
            k = entry_api_key.get().strip()
            if k:
                guardar_api_key(k)
                if hasattr(self, 'ia') and self.ia:
                    prov = "openai" if k.startswith("sk-") else "gemini"
                    self.ia.set_api(prov, k)
                lbl_api_status.configure(text="Clave configurada: Sí (Activa)", text_color=t["success"])
                messagebox.showinfo("Clave de API", "Clave de API guardada y cifrada correctamente (DPAPI).")
            else:
                messagebox.showwarning("Clave de API", "Por favor ingresa una clave de API válida.")

        def eliminar_clave_api():
            borrar_api_key()
            entry_api_key.delete(0, "end")
            if hasattr(self, 'ia') and self.ia:
                self.ia.api_key = None
            lbl_api_status.configure(text="Clave configurada: No (Modo local)", text_color=t["muted"])
            messagebox.showinfo("Clave de API", "Clave de API eliminada. El asistente continuará en modo local.")

        btn_g_api = make_btn(row_api_btns, "Guardar clave", command=guardar_clave_api, tipo="primary", height=34)
        btn_g_api.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_e_api = make_btn(row_api_btns, "Eliminar clave", command=eliminar_clave_api, tipo="danger", height=34)
        btn_e_api.pack(side="right", fill="x", expand=True, padx=(6, 0))

        return frame

    # ══════════════════════════════════════════════════════════
    # CARGA Y PRECARGA ASÍNCRONA DE DATOS (Requerimiento 3.3)
    # ══════════════════════════════════════════════════════════
    def _load_from_cache_if_available(self):
        if self.cache_data and self.cache_data.get("cursos"):
            self.cursos = self.cache_data.get("cursos", [])
            self.novedades = self.cache_data.get("novedades", [])
            nombre = self.cache_data.get("nombre", "")
            if nombre:
                self.lbl_nombre.configure(text=f"👤 {nombre}")
            self._show_cursos(self.cursos)
            self._show_novedades(self.novedades)
            self._show_estadisticas_locales()

    def _load_datos(self, page_size: int = 120):
        def run():
            try:
                cursos, novedades, nombre = get_escritorio(self.sess, page_size=page_size)
                self.cursos = cursos
                self.novedades = novedades
                
                # Actualizar IA
                self.ia.actualizar_datos(cursos, novedades, self.cache_data)
                
                # Precarga en segundo plano de materias 2026 (Requerimiento 3.3)
                self._precargar_materias_background(cursos)

                # Scraping de fuentes externas en segundo plano (Fase 5)
                self._sincronizar_fuentes_externas_background()

                self.after(0, self._on_datos_ok, cursos, novedades, nombre)
            except Exception as e:
                self.after(0, self.lbl_estado.configure, {"text": f"❌ {str(e)[:25]}"})

        threading.Thread(target=run, daemon=True).start()

    def _sincronizar_fuentes_externas_background(self):
        """Ejecuta en segundo plano el scraping del sitio público institucional y Facebook con OCR."""
        def run_externo():
            try:
                from backend.sitio_informativo import SitioInformativoScraper
                scraper_sitio = SitioInformativoScraper()
                scraper_sitio.scrape_completo(max_articulos=15)
            except Exception:
                pass

            try:
                from backend.facebook_scraper import FacebookScraper
                scraper_fb = FacebookScraper()
                scraper_fb.autenticar()
                scraper_fb.scrape_publicaciones(max_posts=10)
            except Exception:
                pass

        threading.Thread(target=run_externo, daemon=True).start()

    def _precargar_materias_background(self, cursos: list):
        """Descarga en segundo plano programas y docentes de las materias del ciclo activo y guarda en cache_materias.json."""
        anios = [c.get("anio") for c in cursos if c.get("anio")]
        max_anio = max(anios) if anios else None
        if max_anio:
            materias_activas = [c for c in cursos if c.get("anio") == max_anio or str(max_anio) in c.get("nombre", "")]
        else:
            materias_activas = cursos[:4]

        if not materias_activas:
            materias_activas = cursos[:4]

        detalle_dict = self.cache_data.get("materias_detalle", {})

        for c in materias_activas:
            cid = str(c.get("id"))
            try:
                # Obtener programa
                prog = prog_mod.get_programa(self.sess, cid)
                # Obtener contactos para sacar nombre del docente
                conts = cont_mod.get_contactos(self.sess, cid, obtener_detalles_completos=False)
                docentes = conts.get("docentes", [])
                doc_nombre = docentes[0].get("nombre", "") if docentes else ""

                c["docente"] = doc_nombre

                detalle_dict[cid] = {
                    "id": cid,
                    "nombre": c.get("nombre"),
                    "docente": doc_nombre,
                    "programa": prog
                }
            except Exception:
                pass

        self.cache_data = {
            "nombre": self.sess.nombre,
            "cursos": cursos,
            "novedades": self.novedades,
            "materias_detalle": detalle_dict
        }
        guardar_cache(self.cache_data)
        self.ia.actualizar_datos(cursos, self.novedades, self.cache_data)

    def _verificar_y_notificar_novedades(self, novedades: list):
        """Monitorea novedades reales no vistas y lanza notificaciones del sistema según Requerimiento 1."""
        from config import cargar_estado_notifs, guardar_estado_notifs
        try:
            from plyer import notification
        except ImportError:
            notification = None

        if not notification or not self.config.get("notificaciones_activas", True):
            return

        estado = cargar_estado_notifs()
        vistos = set(estado.get("vistos", []))

        novs_no_vistas = []
        for n in novedades:
            nid = str(n.get("link") or f"{n.get('clase')}_{n.get('fecha')}_{n.get('id_curso')}")
            if nid not in vistos and es_reciente(n.get("fecha", ""), 7):
                novs_no_vistas.append((nid, n))

        # Notificar solo novedades reales nuevas
        for nid, n in novs_no_vistas[:3]:
            tipo_label = TIPOS_NOV.get(n.get("clase"), ("🔔", "Novedad"))[1]
            curso_nom = n.get("nombre_curso", "Campus Virtual")
            item_nom = n.get("nombre_item") or n.get("nombre_unidad") or tipo_label
            
            titulo_notif = f"IES N°5 - {tipo_label} en {curso_nom[:28]}"
            msg_notif = f"{item_nom} ({fmt_fecha(n.get('fecha', ''))})"

            try:
                # Duración de 2 minutos (120 segundos) según Requerimiento 1
                notification.notify(
                    title=titulo_notif,
                    message=msg_notif,
                    app_name="Campus Virtual IES N°5",
                    timeout=120
                )
                vistos.add(nid)
            except Exception:
                pass

        estado["vistos"] = list(vistos)
        guardar_estado_notifs(estado)

    def _on_datos_ok(self, cursos, novedades, nombre):
        self.lbl_estado.configure(text="✅ Actualizado")
        nom = nombre or self.sess.usuario
        self.lbl_nombre.configure(text=f"👤 {nom}")
        self._show_cursos(cursos)
        self._show_novedades(novedades)
        self._show_estadisticas_locales()
        self._verificar_y_notificar_novedades(novedades)

    def _refresh(self):
        self.lbl_estado.configure(text="⏳ Actualizando...")
        clear_frame(self.scroll_cursos)
        lbl1 = make_label(self.scroll_cursos, "⏳ Actualizando materias...", tipo="subtitulo")
        lbl1.pack(pady=20)

        clear_frame(self.scroll_novs)
        lbl2 = make_label(self.scroll_novs, "⏳ Actualizando novedades...", tipo="subtitulo")
        lbl2.pack(pady=20)

        self._load_datos()


