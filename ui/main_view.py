"""
ui/main_view.py — Vista principal post-login:
Sidebar de navegación con Salir accesible + Secciones (Mis Materias, Novedades, Asistente IA, Estadísticas, Ajustes).
Precarga en segundo plano, soporte de temas, filtrado de años académicos y apertura de novedades y contenidos.
Adaptado 100% para Windows con CustomTkinter.
"""
import re
import os
import io
import threading
import webbrowser
from PIL import Image
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
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
                    set_autoinicio_windows, cargar_cache, guardar_cache,
                    formatear_hora_str)

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

        self._build(initial_page="materias")
        registrar_listener_tema(self._on_tema_update)
        
        # Carga inicial diferida no bloqueante
        self.after(30, self._load_from_cache_if_available)
        self.after(80, self._load_datos)

    def destroy(self):
        desregistrar_listener_tema(self._on_tema_update)
        super().destroy()

    def _on_tema_update(self, t):
        if not self.winfo_exists():
            return
        self.configure(fg_color=t["bg"])
        # Diferir reconstrucción para permitir que el selector cierre su desplegable
        # y termine su callback sin congelar el hilo principal
        self.after(30, self._refresh_ui)

    def _refresh_ui(self):
        curr_page = self._current_page_name
        current_curso = None
        current_act = None
        if self._page_curso_detail and hasattr(self._page_curso_detail, "curso"):
            current_curso = self._page_curso_detail.curso
            current_act = getattr(self._page_curso_detail, "actividad_inicial", None)

        for w in self.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        if current_curso:
            self._build(initial_page="materias")
            self._abrir_curso(current_curso, actividad_inicial=current_act)
        else:
            self._build(initial_page=curr_page)

    # ══════════════════════════════════════════════════════════
    # CONSTRUCCIÓN DE LA INTERFAZ
    # ══════════════════════════════════════════════════════════
    def _build(self, initial_page: str = "materias"):
        t = tema_actual()

        # Layout horizontal principal: Sidebar izquierda + Contenido derecha
        self._build_sidebar()

        # Contenedor dinámico de páginas
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(side="right", fill="both", expand=True)

        # Páginas con inicialización bajo demanda (Lazy Loading) para eliminar
        # por completo cualquier congelamiento o aviso '(No responde)' de Windows.
        self._page_materias = None
        self._page_pendientes = None
        self._page_novedades = None
        self._page_ia = None
        self._page_estadisticas = None
        self._page_ajustes = None
        self._page_curso_detail = None

        self._ir_a(initial_page)

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

        # Nombre del alumno dinámico y acceso a Perfil y Preferencias
        from backend.user import get_current_user
        user_info = get_current_user(self.sess, force_network=False)
        nom = user_info.get("nombre") or self.sess.nombre or self.sess.usuario or "Estudiante"

        user_card = ctk.CTkFrame(hdr, fg_color=t["item_bg"], corner_radius=8, cursor="hand2")
        user_card.pack(fill="x", pady=(10, 0))

        uc_inner = ctk.CTkFrame(user_card, fg_color="transparent")
        uc_inner.pack(fill="x", padx=8, pady=6)

        self.user_av_box = ctk.CTkFrame(uc_inner, width=28, height=28, fg_color=t["card"], corner_radius=14)
        self.user_av_box.pack(side="left", padx=(0, 8))
        self.user_av_box.pack_propagate(False)

        self.lbl_user_icon = make_label(self.user_av_box, "👤", tipo="blanco", anchor="center")
        self.lbl_user_icon.pack(expand=True)

        uc_text = ctk.CTkFrame(uc_inner, fg_color="transparent")
        uc_text.pack(side="left", fill="x", expand=True)

        self.lbl_nombre = make_label(uc_text, nom, tipo="blanco", wrap=120)
        self.lbl_nombre.pack(anchor="w")

        lbl_perf_sub = make_label(uc_text, "Perfil y Preferencias ⚙", tipo="subtitulo")
        lbl_perf_sub.pack(anchor="w")

        for w in (user_card, uc_inner, self.user_av_box, self.lbl_user_icon, uc_text, self.lbl_nombre, lbl_perf_sub):
            w.bind("<Button-1>", lambda e: self._abrir_modal_perfil())

        foto_url = user_info.get("foto_url")
        if foto_url:
            self._cargar_sidebar_avatar(foto_url)

        sep1 = make_separator(self.sb)
        sep1.pack(fill="x", padx=16, pady=(8, 8))

        # Navegación principal
        lbl_sec = make_label(self.sb, "SECCIONES", tipo="seccion")
        lbl_sec.pack(anchor="w", padx=16, pady=(0, 4))

        self.nav_btns = {}
        nav_items = [
            ("materias",     "📚  Mis Materias"),
            ("pendientes",   "📋  Pendientes"),
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

        # Ocultar todas las páginas existentes
        for p in [self._page_materias, self._page_pendientes, self._page_novedades, self._page_ia, self._page_estadisticas, self._page_ajustes, self._page_curso_detail]:
            if p:
                try:
                    p.pack_forget()
                except Exception:
                    pass

        # Mostrar página seleccionada (creación lazy / bajo demanda)
        if key == "materias":
            if self._page_materias is None:
                self._page_materias = self._build_materias_page()
                if self.cursos:
                    self._show_cursos(self.cursos)
            self._page_materias.pack(fill="both", expand=True)
        elif key == "pendientes":
            if self._page_pendientes is None:
                self._page_pendientes = self._build_pendientes_page()
            self._page_pendientes.pack(fill="both", expand=True)
            self._show_pendientes()
        elif key == "novedades":
            if self._page_novedades is None:
                self._page_novedades = self._build_novedades_page()
                if self.novedades:
                    self._show_novedades(self.novedades)
            self._page_novedades.pack(fill="both", expand=True)
        elif key == "ia":
            if self._page_ia is None:
                self._page_ia = self._build_ia_page()
                self._actualizar_chips_sugerencias()
            self._page_ia.pack(fill="both", expand=True)
            self._actualizar_vista_ia_activa()
        elif key == "estadisticas":
            if self._page_estadisticas is None:
                self._page_estadisticas = self._build_estadisticas_page()
                self._show_estadisticas_locales()
            self._page_estadisticas.pack(fill="both", expand=True)
        elif key == "ajustes":
            if self._page_ajustes is None:
                self._page_ajustes = self._build_ajustes_page()
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

    def _abrir_curso(self, curso: dict, actividad_inicial: dict = None):
        if self._page_curso_detail:
            try:
                self._page_curso_detail.destroy()
            except Exception:
                pass
            self._page_curso_detail = None

        self._ir_a("none")

        # Obtener cache detallado si existe para carga instantánea
        cached_mat = self.cache_data.get("materias_detalle", {}).get(str(curso["id"]), {})

        self._page_curso_detail = CursoDetailView(
            self.main_container,
            self.sess,
            curso,
            on_back=self._volver_a_materias,
            cached_data=cached_mat,
            actividad_inicial=actividad_inicial
        )
        self._page_curso_detail.pack(fill="both", expand=True)
        try:
            self._page_curso_detail.update_idletasks()
        except Exception:
            pass

    def _volver_a_materias(self):
        if self._page_curso_detail:
            self._page_curso_detail.pack_forget()
        self._ir_a("materias")

    def _abrir_curso_por_id(self, id_curso: str):
        if not id_curso:
            return
        for c in self.cursos:
            if str(c.get("id")) == str(id_curso):
                self._abrir_curso(c)
                return

    def _abrir_curso_con_actividad(self, id_curso, actividad: dict):
        if not id_curso:
            return
        curso_obj = None
        for c in self.cursos:
            if str(c.get("id")) == str(id_curso):
                curso_obj = c
                break
        if not curso_obj:
            curso_obj = {
                "id": str(id_curso),
                "nombre": actividad.get("curso", "Materia"),
                "color": tema_actual()["accent"]
            }
        self._abrir_curso(curso_obj, actividad_inicial=actividad)

    # ── PÁGINA PENDIENTES ──────────────────────────────────────
    def _build_pendientes_page(self):
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        # Header
        top_h = ctk.CTkFrame(frame, fg_color="transparent")
        top_h.pack(fill="x", padx=20, pady=(16, 6))

        left_h = ctk.CTkFrame(top_h, fg_color="transparent")
        left_h.pack(side="left", fill="x", expand=True)

        lbl_tit = make_label(left_h, "Actividades Pendientes", tipo="titulo")
        lbl_tit.pack(anchor="w")

        lbl_sub = make_label(left_h, "Listado de actividades vencidas y por entregar ordenadas por prioridad", tipo="subtitulo")
        lbl_sub.pack(anchor="w", pady=(2, 0))

        sep = make_separator(frame)
        sep.pack(fill="x", padx=20, pady=(6, 10))

        self.scroll_pendientes = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.scroll_pendientes.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        return frame

    def _render_card_actividad_en_pendientes(self, a: dict):
        t = tema_actual()
        por_vencer = a.get("por_vencer", False)
        vencida = a.get("vencida", False)

        b_color = "#ef4444" if (vencida or por_vencer) else t["accent"]
        card = make_card(
            self.scroll_pendientes,
            fg_color=t["card"],
            corner_radius=10,
            border_color=b_color
        )
        card.pack(fill="x", pady=5, padx=2)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        bar = ctk.CTkFrame(inner, width=4, height=44, fg_color=b_color, corner_radius=2)
        bar.pack(side="left", padx=(0, 12))

        body = ctk.CTkFrame(inner, fg_color="transparent")
        body.pack(side="left", fill="x", expand=True)

        top_r = ctk.CTkFrame(body, fg_color="transparent")
        top_r.pack(fill="x")

        lbl_tipo = make_label(top_r, f"✏️ ACTIVIDAD • {a.get('curso', '')}", tipo="seccion")
        lbl_tipo.pack(side="left")

        badge_txt = "⏰ PLAZO VENCIDO" if vencida else ("🔥 ¡POR VENCER!" if por_vencer else "⏳ PENDIENTE")
        badge_bg = "#ef4444" if (vencida or por_vencer) else t["accent"]
        badge = make_badge(top_r, badge_txt, bg_color=badge_bg, text_color="#ffffff")
        badge.pack(side="right")

        lbl_tit = ctk.CTkLabel(
            body, text=a.get("titulo", ""),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=t["text"],
            wraplength=480, justify="left"
        )
        lbl_tit.pack(anchor="w", pady=(3, 0))

        bot_r = ctk.CTkFrame(body, fg_color="transparent")
        bot_r.pack(fill="x", pady=(4, 0))

        fecha_fmt = formatear_hora_str(a.get("fecha", ""))
        lbl_plazo = make_label(bot_r, f"📅 {a.get('tiempo_restante_str', '')} • Límite: {fecha_fmt}", tipo="subtitulo")
        lbl_plazo.pack(side="left")

        btn_ir = make_btn(
            bot_r, "Ir a materia →",
            command=lambda act=a: self._abrir_curso_con_actividad(act.get("id_curso"), act),
            tipo="primary" if (vencida or por_vencer) else "flat",
            height=28, width=120
        )
        btn_ir.pack(side="right")

        # Clic en toda la tarjeta también abre la actividad en la materia
        for w in (card, inner, bar, body, top_r, bot_r, lbl_tipo, lbl_tit, lbl_plazo):
            w.bind("<Button-1>", lambda e, act=a: self._abrir_curso_con_actividad(act.get("id_curso"), act))

    def _show_pendientes(self):
        if not hasattr(self, "scroll_pendientes") or not self.scroll_pendientes or not self.scroll_pendientes.winfo_exists():
            return
        t = tema_actual()
        clear_frame(self.scroll_pendientes)

        from backend.actividades_tracker import generar_novedades_actividades_pendientes
        acts = generar_novedades_actividades_pendientes()

        if not acts:
            lbl = make_label(self.scroll_pendientes, "🎉 ¡Excelente! No tienes actividades pendientes ni adeudadas.", tipo="subtitulo")
            lbl.pack(pady=30)
            return

        # Orden estricto requerido por el usuario en agy.txt:
        # 1º Vencidas (vencida == True)
        # 2º Que debo (pendientes / por entregar)
        vencidas = [a for a in acts if a.get("vencida", False)]
        que_debo = [a for a in acts if not a.get("vencida", False)]

        # 1. Sección Vencidas
        if vencidas:
            hdr_v = ctk.CTkFrame(self.scroll_pendientes, fg_color="transparent")
            hdr_v.pack(fill="x", pady=(4, 6), padx=4)
            make_label(hdr_v, f"⏰ ACTIVIDADES VENCIDAS ({len(vencidas)})", tipo="seccion").pack(side="left")

            for a in vencidas:
                self._render_card_actividad_en_pendientes(a)

        # Separador visual si hay ambos grupos
        if vencidas and que_debo:
            sep = make_separator(self.scroll_pendientes)
            sep.pack(fill="x", padx=4, pady=(12, 10))

        # 2. Sección Que debo
        if que_debo:
            hdr_q = ctk.CTkFrame(self.scroll_pendientes, fg_color="transparent")
            hdr_q.pack(fill="x", pady=(4, 6), padx=4)
            make_label(hdr_q, f"📝 ACTIVIDADES PENDIENTES / QUE DEBO ({len(que_debo)})", tipo="seccion").pack(side="left")

            for a in que_debo:
                self._render_card_actividad_en_pendientes(a)

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
        self.novedades = novedades
        if not hasattr(self, "scroll_novs") or not self.scroll_novs or not self.scroll_novs.winfo_exists():
            return
        t = tema_actual()
        clear_frame(self.scroll_novs)

        if not novedades:
            lbl = make_label(self.scroll_novs, "✅ No hay novedades ni mensajes nuevos registrados en el campus.", tipo="subtitulo")
            lbl.pack(pady=20)
            return

        hdr_novs = ctk.CTkFrame(self.scroll_novs, fg_color="transparent")
        hdr_novs.pack(fill="x", pady=(0, 6), padx=4)
        make_label(hdr_novs, "🔔 NOVEDADES Y MENSAJES DEL CAMPUS", tipo="seccion").pack(side="left")

        # Requerimiento 6: Ordenar novedades de más reciente a más antigua
        novs_ordenadas = sorted(novedades, key=lambda x: str(x.get("fecha", "")), reverse=True)

        for n in novs_ordenadas:
            reciente = es_reciente(n.get("fecha", ""), 7)
            fecha_n = formatear_hora_str(n.get("fecha", ""))
            edad = fmt_fecha(fecha_n)
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
            nombre_item = n.get("nombre_item") or n.get("nombre_unidad") or (f"Correo de {n['remitente']}" if n.get("remitente") else tipo_txt)
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
            bandeja = n.get("bandeja", "")
            tag_b = " (Papelera)" if bandeja == "Trash" else (" (Enviados)" if bandeja == "Outbox" else "")
            if n.get("remitente"):
                info_curso = f"👤 {n['remitente']}  •  📍 {curso}{tag_b}" if curso else f"👤 {n['remitente']}{tag_b}"
            else:
                info_curso = f"📍 {curso}{tag_b}" if curso else ""

            if info_curso:
                lbl_c = make_label(bot_r, info_curso, tipo="subtitulo", wrap=380)
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
        top.geometry("640x540")
        top.transient(self)
        top.grab_set()

        hdr = ctk.CTkFrame(top, fg_color=t["sidebar"], corner_radius=0)
        hdr.pack(fill="x")

        tit = n.get("nombre_item") or n.get("nombre_unidad") or (f"Correo de {n['remitente']}" if n.get("remitente") else n.get("titulo", "Novedad del Campus"))
        lbl_t = ctk.CTkLabel(
            hdr, text=tit,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=t["text"],
            wraplength=580, justify="left"
        )
        lbl_t.pack(padx=20, pady=(16, 4), anchor="w")

        materia_info = n.get("nombre_curso") or n.get("curso", "")
        fecha_info = n.get("fecha", "")
        lbl_s = make_label(hdr, f"Materia: {materia_info}  |  Fecha: {fecha_info}", tipo="subtitulo")
        lbl_s.pack(padx=20, pady=(0, 14), anchor="w")

        content = ctk.CTkScrollableFrame(top, fg_color=t["bg"])
        content.pack(fill="both", expand=True, padx=16, pady=12)

        if n.get("es_actividad_adeudada"):
            resultado = {
                "asunto": tit,
                "remitente": materia_info,
                "fecha": fecha_info,
                "cuerpo": (
                    f"📌 Materia: {materia_info}\n\n"
                    f"📋 Estado: {n.get('tag_alerta', 'Pendiente')}\n"
                    f"⏱ Plazo restante: {n.get('tiempo_restante_str', 'Consultar aula')}\n"
                    f"📅 Fecha límite de entrega: {fecha_info}\n\n"
                    f"{n.get('texto', '')}\n\n"
                    "Recuerda ingresar al aula virtual de la materia para enviar tu resolución antes del cierre."
                ),
                "adjuntos": [],
                "links": [{"url": n.get("url", ""), "texto": "Abrir actividad en el campus"}] if n.get("url") else []
            }
            self._render_modal_novedad(content, resultado, top)
            return

        lbl_carg = make_label(content, "⏳ Cargando contenido del campus...", tipo="subtitulo")
        lbl_carg.pack(pady=30)

        def run():
            link = n.get("link", "")
            full_url = self.sess.url(link) if link and not link.startswith("http") else link
            resultado = {
                "asunto": n.get("nombre_item", ""),
                "remitente": n.get("remitente", ""),
                "fecha": fmt_fecha(n.get("fecha", "")),
                "cuerpo": "",
                "adjuntos": [],
                "links": []
            }
            if "webmail.cgi" in link or n.get("clase") == "email":
                data = msg_mod.get_detalle_mensaje(
                    self.sess, 
                    link, 
                    n.get("id_curso", ""),
                    fecha_novedad=n.get("fecha", ""),
                    asunto_novedad=n.get("nombre_item", "")
                )
                if data.get("asunto"):
                    resultado["asunto"] = data.get("asunto")
                if data.get("remitente"):
                    resultado["remitente"] = data.get("remitente")
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

            def update_ui():
                if resultado.get("asunto"):
                    lbl_t.configure(text=resultado["asunto"])
                self._render_modal_novedad(content, resultado, top)

            self.after(0, update_ui)

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
        txt_box = ctk.CTkTextbox(
            card_c,
            fg_color="transparent",
            text_color=t["text"],
            font=ctk.CTkFont(family="Segoe UI", size=13),
            wrap="word",
            activate_scrollbars=True
        )
        txt_box.pack(fill="both", expand=True, padx=12, pady=12)
        txt_box.insert("1.0", cuerpo_txt)
        txt_box.configure(state="disabled")

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

        lbl_t = make_label(left, "Asistente Virtual", tipo="titulo")
        lbl_t.pack(anchor="w")

        self.lbl_api_estado = make_label(left, "IA desactivada", tipo="subtitulo")
        self.lbl_api_estado.pack(anchor="w", pady=(2, 0))

        sep = make_separator(frame)
        sep.pack(fill="x", padx=20, pady=(4, 10))

        # Historial de Chat (Ocupa el espacio central)
        self.chat_scroll = ctk.CTkScrollableFrame(frame, fg_color=t["bg"])
        self.chat_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Solo mostrar saludo inicial si hay al menos una IA activa configurada
        if self._tiene_alguna_ia_activa():
            saludo = self.ia.get_saludo_inicial() if hasattr(self.ia, "get_saludo_inicial") else "¡Hola! Soy tu Asistente Virtual. ¿Cómo puedo ayudarte?"
            self._ia_msg(saludo, typewriter=False)

        # Botones de sugerencia en la parte inferior (desplazables horizontalmente para no salirse de la pantalla)
        self.chips_frame = ctk.CTkScrollableFrame(
            frame,
            fg_color="transparent",
            orientation="horizontal",
            height=46
        )
        self.chips_frame.pack(fill="x", padx=20, pady=(0, 6))
        self._actualizar_chips_sugerencias()

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

        # Cargar estado de API / Asistente
        self._actualizar_indicador_ia()

        return frame

    def _actualizar_indicador_ia(self):
        """Actualiza la etiqueta de estado de IA en la cabecera del chat según configuración y AGY."""
        if not hasattr(self, "lbl_api_estado") or not self.lbl_api_estado.winfo_exists():
            return
        t = tema_actual()
        import ia.agy_sidecar as agy_sidecar
        if self.config.get("usar_asistente_agy", False) and agy_sidecar.esta_instalado():
            self.lbl_api_estado.configure(text="Asistente Avanzado AGY (Modo Low) ✅", text_color=t["success"])
        elif self.ia.tiene_api_activa():
            self.lbl_api_estado.configure(text="IA Externa activa ✅", text_color=t["success"])
        elif self.config.get("bot_local_activo", True) and not self.config.get("solo_ia_api", False):
            self.lbl_api_estado.configure(text="Bot Local Offline ✅", text_color=t["muted"])
        else:
            self.lbl_api_estado.configure(text="Asistente desactivado", text_color=t["warning"])

    def _tiene_alguna_ia_activa(self) -> bool:
        """Determina si al menos una fuente de IA está activa (AGY, API externa o Bot local)."""
        import ia.agy_sidecar as agy_sidecar
        if self.config.get("usar_asistente_agy", False) and agy_sidecar.esta_instalado():
            return True
        if self.ia.tiene_api_activa():
            return True
        if self.config.get("bot_local_activo", True) and not self.config.get("solo_ia_api", False):
            return True
        return False

    def _actualizar_vista_ia_activa(self):
        """Muestra u oculta el aviso central cuando todas las funciones de IA están desactivadas."""
        self._actualizar_indicador_ia()
        t = tema_actual()
        activa = self._tiene_alguna_ia_activa()

        if hasattr(self, "_ia_desactivada_frame") and self._ia_desactivada_frame and self._ia_desactivada_frame.winfo_exists():
            self._ia_desactivada_frame.destroy()
            self._ia_desactivada_frame = None

        if activa:
            self.ia_entry.configure(state="normal", placeholder_text="Escribí tu pregunta aquí y presioná Enter...")
            self.btn_send.configure(state="normal")
            if hasattr(self, "chips_frame") and self.chips_frame.winfo_exists():
                self.chips_frame.pack(fill="x", padx=20, pady=(0, 6))
        else:
            self.ia_entry.configure(state="disabled", placeholder_text="⚠️ Asistente IA desactivado")
            self.btn_send.configure(state="disabled")
            if hasattr(self, "chips_frame") and self.chips_frame.winfo_exists():
                self.chips_frame.pack_forget()

            self._ia_desactivada_frame = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
            self._ia_desactivada_frame.pack(fill="both", expand=True, padx=20, pady=30)

            card_aviso = make_card(self._ia_desactivada_frame, fg_color=t["card"], corner_radius=12, border_color=t["border"])
            card_aviso.pack(anchor="center", padx=20, pady=10, fill="x")

            inner_aviso = ctk.CTkFrame(card_aviso, fg_color="transparent")
            inner_aviso.pack(padx=24, pady=24, fill="x")

            lbl_tit = make_label(inner_aviso, "Asistente Virtual Desactivado", tipo="titulo_sm", anchor="center")
            lbl_tit.pack(pady=(0, 8))

            lbl_desc = make_label(
                inner_aviso,
                "Actualmente todas las opciones de inteligencia artificial se encuentran deshabilitadas en tu configuración (API de Google Gemini, OpenAI, Asistente Local o AGY).\n\n"
                "Para poder realizar consultas y chatear con el asistente, por favor activa al menos una de las opciones disponibles en la sección de Ajustes.",
                tipo="subtitulo",
                anchor="center",
                wrap=520
            )
            lbl_desc.pack(pady=(0, 20))

            btn_ir_ajustes = make_btn(
                inner_aviso,
                "⚙️ Aceptar e ir a Ajustes",
                command=lambda: self._ir_a("ajustes"),
                tipo="primary",
                height=38,
                width=220
            )
            btn_ir_ajustes.pack(anchor="center")

    def _actualizar_chips_sugerencias(self):
        """Genera los botones rápidos de preguntas frecuentes de forma 100% dinámica usando las materias del alumno."""
        if not hasattr(self, "chips_frame") or not self.chips_frame.winfo_exists():
            return
        clear_frame(self.chips_frame)

        # Helper para acortar nombres largos de materias
        def _acortar(nom):
            limpio = re.sub(r'\(.*?\)', '', nom)
            limpio = re.sub(r'-\s*\d{4}', '', limpio)
            limpio = re.sub(r'\b20\d{2}\b', '', limpio)
            limpio = limpio.replace("Administración y Mantenimiento de", "")
            limpio = limpio.replace("Tec. en Soporte", "")
            limpio = limpio.strip()
            return limpio if limpio else nom[:15]

        # Sugerencias principales fijas
        sugerencias = [
            ("📅 ¿Qué día es hoy?", "¿Qué día es hoy?"),
            ("📋 ¿Debo alguna actividad?", "¿Debo alguna actividad o entrega pendiente?"),
            ("💬 Mensajes del chat", "¿Hay algún mensaje nuevo en el chat del aula?"),
            ("📊 Mis calificaciones", "Mis calificaciones"),
            ("👥 Mis compañeros", "¿Quiénes son mis compañeros de cursada?")
        ]

        # Sugerencias dinámicas según las materias reales del alumno
        cursos_activos = self.cursos if hasattr(self, "cursos") and self.cursos else []
        for c in cursos_activos[:4]:
            c_nom = c.get("nombre", "").strip()
            if c_nom:
                c_corto = _acortar(c_nom)
                sugerencias.append((f"👨‍🏫 Profesor de {c_corto}", f"¿Quién es el profesor de {c_nom}?"))
                sugerencias.append((f"📝 Parciales de {c_corto}", f"¿Cuándo son los parciales de {c_nom}?"))

        for label, prg in sugerencias:
            btn_chip = make_btn(
                self.chips_frame, label,
                command=lambda p=prg: self._ia_quick_send(p),
                tipo="flat", height=30
            )
            btn_chip.pack(side="left", padx=4, pady=2)

    def _ia_quick_send(self, pregunta: str):
        """Envía una consulta rápida al hacer clic en uno de los chips de sugerencia."""
        self.ia_entry.delete(0, "end")
        self.ia_entry.insert(0, pregunta)
        self._ia_send()

    def _forward_chat_scroll(self, event):
        """Redirige el scroll de la rueda del ratón desde las burbujas al contenedor del chat."""
        try:
            delta = -1 * int(event.delta / 120) if event.delta else 1
            self.chat_scroll._parent_canvas.yview_scroll(delta, "units")
        except Exception:
            pass

    def _ia_msg(self, txt: str, typewriter: bool = False):
        t = tema_actual()
        bubble = make_card(self.chat_scroll, fg_color=t["card"], corner_radius=10, border_color=t["border"])
        bubble.pack(fill="x", pady=4, padx=(0, 60), anchor="w")

        # Cálculo dinámico de altura para evitar espacios vacíos gigantes
        lines = txt.count("\n") + 1
        approx_lines = max(lines, int(len(txt) / 52) + 1)
        calc_height = max(34, min(450, approx_lines * 20 + 14))

        # CTkTextbox seleccionable con menú contextual de clic derecho
        txt_box = ctk.CTkTextbox(
            bubble,
            fg_color="transparent",
            text_color=t["text"],
            wrap="word",
            activate_scrollbars=False,
            border_width=0,
            height=calc_height,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        txt_box.pack(fill="x", padx=12, pady=8, anchor="w")

        # Bindeo de rueda del ratón sobre la burbuja y el texto para scroll fluido
        bubble.bind("<MouseWheel>", self._forward_chat_scroll)
        txt_box.bind("<MouseWheel>", self._forward_chat_scroll)
        try:
            if hasattr(txt_box, "_textbox"):
                txt_box._textbox.bind("<MouseWheel>", self._forward_chat_scroll)
        except Exception:
            pass

        # Menú contextual de clic derecho para copiar texto
        menu_ctx = tk.Menu(txt_box, tearoff=0)
        menu_ctx.add_command(label="Copiar selección", command=lambda: self._copiar_seleccion(txt_box))
        menu_ctx.add_command(label="Copiar todo el mensaje", command=lambda: self._copiar_texto_chat(txt))
        txt_box.bind("<Button-3>", lambda e: menu_ctx.tk_popup(e.x_root, e.y_root))

        if typewriter:
            txt_box.configure(state="normal")
            txt_box.delete("1.0", "end")
            
            def escribir_letra(idx=0):
                if idx < len(txt):
                    txt_box.insert("end", txt[idx])
                    self._scroll_chat_to_bottom()
                    self.after(8, lambda: escribir_letra(idx + 1))
                else:
                    txt_box.configure(state="disabled")
            escribir_letra()
        else:
            txt_box.insert("1.0", txt)
            txt_box.configure(state="disabled")
            self._scroll_chat_to_bottom()

    def _copiar_seleccion(self, txt_box):
        try:
            sel = txt_box.get(tk.SEL_FIRST, tk.SEL_LAST)
            if sel:
                self._copiar_texto_chat(sel)
        except Exception:
            pass

    def _copiar_texto_chat(self, txt):
        try:
            self.clipboard_clear()
            self.clipboard_append(txt)
            self._mostrar_toast("Texto copiado al portapapeles ✅")
        except Exception:
            pass

    def _mostrar_toast(self, mensaje: str):
        """Muestra una notificación emergente flotante no bloqueante que se desvanece suavemente."""
        t = tema_actual()
        try:
            # Banner en el status bar para evitar ventanas huérfanas
            self.lbl_estado.configure(text=mensaje)
            self.after(2500, lambda: self.lbl_estado.configure(text="✅ Actualizado"))
        except Exception:
            pass

    def _user_msg(self, txt):
        t = tema_actual()
        bubble = make_card(self.chat_scroll, fg_color=t["accent"], corner_radius=10, border_color=t["accent_hover"])
        bubble.pack(pady=4, padx=(80, 0), anchor="e")

        lbl = make_label(bubble, txt, tipo="blanco", wrap=540)
        lbl.configure(text_color=t["btn_text"])
        lbl.pack(padx=14, pady=8, anchor="e")

        # Scroll fluido también sobre los mensajes del usuario
        bubble.bind("<MouseWheel>", self._forward_chat_scroll)
        lbl.bind("<MouseWheel>", self._forward_chat_scroll)
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

        # Animación dinámica de pensando/escribiendo
        t = tema_actual()
        self._thinking_bubble = make_card(self.chat_scroll, fg_color=t["card"], corner_radius=10, border_color=t["border"])
        self._thinking_bubble.pack(fill="x", pady=4, padx=(0, 60), anchor="w")
        self._thinking_bubble.bind("<MouseWheel>", self._forward_chat_scroll)
        self._lbl_think = make_label(self._thinking_bubble, "⏳ Asistente escribiendo...", tipo="subtitulo")
        self._lbl_think.pack(padx=14, pady=8, anchor="w")
        self._lbl_think.bind("<MouseWheel>", self._forward_chat_scroll)
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
            self.after(300, self._animar_thinking)

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
        self._ia_msg(resp, typewriter=True)

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
        if not hasattr(self, "scroll_stats") or not self.scroll_stats or not self.scroll_stats.winfo_exists():
            return
        t = tema_actual()
        clear_frame(self.scroll_stats)

        # Mostrar todas las materias del ciclo lectivo más reciente (incluidas con avance 0%)
        anios = [c.get("anio") for c in self.cursos if c.get("anio")]
        max_anio = max(anios) if anios else None

        if max_anio:
            cursos_mostrar = [
                c for c in self.cursos
                if (c.get("anio") == max_anio or str(max_anio) in c.get("nombre", ""))
            ]
            if not cursos_mostrar:
                cursos_mostrar = self.cursos
        else:
            cursos_mostrar = self.cursos

        lbl_hdr = make_label(self.scroll_stats, "AVANCE POR ASIGNATURA (TODAS LAS MATERIAS)", tipo="seccion")
        lbl_hdr.pack(anchor="w", padx=4, pady=(4, 10))

        if not cursos_mostrar:
            lbl_v = make_label(self.scroll_stats, "ℹ No se registraron materias para mostrar estadísticas.", tipo="subtitulo")
            lbl_v.pack(pady=20)
            return

        for c in cursos_mostrar:
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

        lbl_hora = make_label(inner_o, "Formato de visualización de hora:", tipo="subtitulo")
        lbl_hora.pack(anchor="w", pady=(8, 2))

        formato_hora_map = {
            "Formato 12 horas (AM/PM) (Ej: 02:00 pm)": True,
            "Formato 24 horas (Ej: 14:00)": False
        }
        combo_hora = ctk.CTkOptionMenu(
            inner_o,
            values=list(formato_hora_map.keys()),
            fg_color=t["accent"],
            button_color=t["accent_hover"],
            text_color=t["btn_text"],
            height=34
        )
        usar_12h = self.config.get("formato_hora_12h", True)
        for k, v in formato_hora_map.items():
            if v == usar_12h:
                combo_hora.set(k)
                break
        combo_hora.pack(fill="x", pady=(0, 8))

        def on_hora_change(choice):
            self.config["formato_hora_12h"] = formato_hora_map[choice]
            guardar_config(self.config)
            if hasattr(self, "_page_pendientes") and self._page_pendientes:
                self._show_pendientes()
            if hasattr(self, "_page_novedades") and self._page_novedades:
                self._show_novedades(self.novedades)

        combo_hora.configure(command=on_hora_change)

        def guardar_preferencias():
            self.config["mostrar_materias_anteriores"] = (chk_ant.get() == 1)
            self.config["iniciar_con_sistema"] = (chk_sys.get() == 1)
            self.config["formato_hora_12h"] = formato_hora_map.get(combo_hora.get(), True)
            guardar_config(self.config)
            set_autoinicio_windows(chk_sys.get() == 1)
            self._show_cursos(self.cursos)
            if hasattr(self, "_page_pendientes") and self._page_pendientes:
                self._show_pendientes()
            if hasattr(self, "_page_novedades") and self._page_novedades:
                self._show_novedades(self.novedades)
            messagebox.showinfo("Ajustes Guardados", "Preferencias guardadas correctamente.")

        btn_g_opts = make_btn(inner_o, "Guardar Preferencias", command=guardar_preferencias, tipo="primary", height=34)
        btn_g_opts.pack(fill="x", pady=(12, 0))

        # 3.5. Recordatorio de Actividades Pendientes (Autologueo)
        card_acts = make_card(scroll, fg_color=t["card"], corner_radius=10, border_color=t["border"])
        card_acts.pack(fill="x", pady=6)

        inner_acts = ctk.CTkFrame(card_acts, fg_color="transparent")
        inner_acts.pack(fill="x", padx=16, pady=14)

        lbl_acts_h = make_label(inner_acts, "📋 RECORDATORIO DE ACTIVIDADES PENDIENTES", tipo="seccion")
        lbl_acts_h.pack(anchor="w", pady=(0, 6))

        lbl_acts_desc = make_label(
            inner_acts,
            "Monitorea de forma automática tus materias omitiendo las tareas entregadas para que no se te pase ninguna fecha.\n"
            "Solo funciona si está activado el autologueo (recordar sesión).",
            tipo="subtitulo",
            wrap=550
        )
        lbl_acts_desc.pack(anchor="w", pady=(0, 8))

        chk_monitoreo = ctk.CTkCheckBox(
            inner_acts,
            text="Activar monitoreo de actividades adeudadas",
            text_color=t["text"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        if self.config.get("monitorear_actividades_pendientes", True):
            chk_monitoreo.select()
        chk_monitoreo.pack(anchor="w", pady=4)

        lbl_rev_frec = make_label(inner_acts, "Frecuencia de revisión general de materias:", tipo="subtitulo")
        lbl_rev_frec.pack(anchor="w", pady=(6, 2))

        inter_dias_map = {
            "Cada 1 día (24 hs)": 1,
            "Cada 2 días (48 hs)": 2,
            "Cada 3 días": 3,
            "Cada 1 semana": 7
        }
        combo_dias = ctk.CTkOptionMenu(
            inner_acts,
            values=list(inter_dias_map.keys()),
            fg_color=t["accent"],
            button_color=t["accent_hover"],
            text_color=t["btn_text"],
            height=34
        )
        curr_dias = self.config.get("intervalo_revision_actividades_dias", 1)
        for k, v in inter_dias_map.items():
            if v == curr_dias:
                combo_dias.set(k)
                break
        combo_dias.pack(fill="x", pady=(0, 6))

        chk_insistir = ctk.CTkCheckBox(
            inner_acts,
            text="Recordar con mayor frecuencia si una actividad está por vencer (plazo <= 48 hs)",
            text_color=t["text"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        if self.config.get("recordatorio_frecuente_vencimiento", True):
            chk_insistir.select()
        chk_insistir.pack(anchor="w", pady=(6, 4))

        lbl_insist_frec = make_label(inner_acts, "Intervalo de recordatorio frecuente en la aplicación:", tipo="subtitulo")
        lbl_insist_frec.pack(anchor="w", pady=(4, 2))

        inter_hs_map = {
            "Cada 1 hora": 1,
            "Cada 2 horas": 2,
            "Cada 4 horas": 4
        }
        combo_hs = ctk.CTkOptionMenu(
            inner_acts,
            values=list(inter_hs_map.keys()),
            fg_color=t["accent"],
            button_color=t["accent_hover"],
            text_color=t["btn_text"],
            height=34
        )
        curr_hs = self.config.get("intervalo_recordatorio_horas", 2)
        for k, v in inter_hs_map.items():
            if v == curr_hs:
                combo_hs.set(k)
                break
        combo_hs.pack(fill="x", pady=(0, 10))

        def guardar_config_actividades():
            self.config["monitorear_actividades_pendientes"] = (chk_monitoreo.get() == 1)
            self.config["intervalo_revision_actividades_dias"] = inter_dias_map.get(combo_dias.get(), 1)
            self.config["recordatorio_frecuente_vencimiento"] = (chk_insistir.get() == 1)
            self.config["intervalo_recordatorio_horas"] = inter_hs_map.get(combo_hs.get(), 2)
            guardar_config(self.config)
            messagebox.showinfo("Ajustes de Actividades", "Configuración de recordatorios de actividades guardada.")
            if chk_monitoreo.get() == 1 and hasattr(self, "cursos") and self.cursos:
                self._escanear_actividades_background(self.cursos)

        btn_g_acts = make_btn(inner_acts, "Guardar Configuración de Actividades", command=guardar_config_actividades, tipo="primary", height=34)
        btn_g_acts.pack(fill="x", pady=(4, 0))

        # 4. Sección de Carga y Procesamiento de Archivos (Paso 2)
        card_upload = make_card(scroll, fg_color=t["card"], corner_radius=10, border_color=t["border"])
        card_upload.pack(fill="x", pady=6)

        inner_up = ctk.CTkFrame(card_upload, fg_color="transparent")
        inner_up.pack(fill="x", padx=16, pady=14)

        lbl_up_h = make_label(inner_up, "📂 CARGAR DATOS Y DOCUMENTOS (IA KNOWLEDGE BASE)", tipo="seccion")
        lbl_up_h.pack(anchor="w", pady=(0, 4))

        lbl_up_desc = make_label(
            inner_up,
            "Cargá planificaciones, programas o parciales en PDF, DOCX o Imágenes (OCR).\n"
            "El sistema procesará el texto y tablas para que el Asistente Virtual responda tus consultas al instante.",
            tipo="subtitulo",
            wrap=550
        )
        lbl_up_desc.pack(anchor="w", pady=(0, 8))

        lbl_mat_select = make_label(inner_up, "Materia asociada (opcional):", tipo="subtitulo")
        lbl_mat_select.pack(anchor="w", pady=(2, 2))

        entry_up_mat = ctk.CTkEntry(
            inner_up,
            placeholder_text="Ej. Redes, Programación, Práctica Profesional",
            fg_color=t["input_bg"],
            border_color=t["border"],
            text_color=t["text"],
            height=34
        )
        entry_up_mat.pack(fill="x", pady=(0, 10))

        lbl_up_status = make_label(inner_up, "Estado: Listo para procesar archivos.", tipo="subtitulo")
        lbl_up_status.pack(anchor="w", pady=(0, 8))

        def seleccionar_y_procesar_archivo():
            from tkinter import filedialog
            from backend.document_processor import DocumentProcessor
            tipos = [
                ("Archivos compatibles", "*.pdf;*.docx;*.doc;*.png;*.jpg;*.jpeg;*.txt"),
                ("Documentos PDF", "*.pdf"),
                ("Documentos Word", "*.docx;*.doc"),
                ("Imágenes", "*.png;*.jpg;*.jpeg;*.bmp"),
                ("Todos los archivos", "*.*")
            ]
            fpath = filedialog.askopenfilename(title="Seleccionar archivo para la base de conocimiento", filetypes=tipos)
            if not fpath:
                return

            mat = entry_up_mat.get().strip()
            lbl_up_status.configure(text=f"⏳ Procesando '{os.path.basename(fpath)}'...", text_color=t["accent"])
            
            def run_proc():
                try:
                    proc = DocumentProcessor()
                    doc_res = proc.process_file(fpath, materia=mat)
                    
                    # Persistencia en escritorio si autologin está desactivado
                    from config import generar_archivo_informacion_desktop, cargar_creds
                    u_s, _ = cargar_creds()
                    generar_archivo_informacion_desktop(usuario=u_s, auto_login=bool(u_s))

                    self.after(0, lambda: [
                        lbl_up_status.configure(
                            text=f"✅ Documento '{doc_res.get('titulo')}' procesado e indexado con éxito ({len(doc_res.get('indice', []))} secciones).",
                            text_color=t["success"]
                        ),
                        messagebox.showinfo("Cargar Datos", f"Se indexó '{os.path.basename(fpath)}' correctamente en la base de conocimiento.")
                    ])
                except Exception as ex:
                    self.after(0, lambda: [
                        lbl_up_status.configure(text=f"❌ Error al procesar: {ex}", text_color=t["warning"]),
                        messagebox.showerror("Error de Procesamiento", str(ex))
                    ])

            threading.Thread(target=run_proc, daemon=True).start()

        btn_upload = make_btn(inner_up, "Subir y Procesar Archivo 📤", command=seleccionar_y_procesar_archivo, tipo="primary", height=36)
        btn_upload.pack(fill="x")

        # 5. Claves de API del Asistente IA (Gemini y OpenAI)
        from config import (
            guardar_gemini_key, cargar_gemini_key, borrar_gemini_key,
            guardar_openai_key, cargar_openai_key, borrar_openai_key
        )
        card_api = make_card(scroll, fg_color=t["card"], corner_radius=10, border_color=t["border"])
        card_api.pack(fill="x", pady=6)

        inner_api = ctk.CTkFrame(card_api, fg_color="transparent")
        inner_api.pack(fill="x", padx=16, pady=14)

        lbl_api_h = make_label(inner_api, "🤖 CONFIGURACIÓN DE APIS DE IA (GEMINI / OPENAI)", tipo="seccion")
        lbl_api_h.pack(anchor="w", pady=(0, 4))

        lbl_api_desc = make_label(
            inner_api,
            "Permite activar el modo avanzado con doble API y fallback automático.\n"
            "Primaria: Google Gemini | Secundaria / Fallback: OpenAI (timeout 10s).\n"
            "Las claves se almacenan cifradas con Windows DPAPI.",
            tipo="subtitulo",
            wrap=550
        )
        lbl_api_desc.pack(anchor="w", pady=(0, 8))

        gemini_actual = cargar_gemini_key()
        openai_actual = cargar_openai_key()

        lbl_g = make_label(inner_api, "Clave API Gemini (Principal):", tipo="subtitulo")
        lbl_g.pack(anchor="w", pady=(2, 2))

        entry_gemini_key = ctk.CTkEntry(
            inner_api,
            placeholder_text="AIzaSy...",
            show="*",
            fg_color=t["input_bg"],
            border_color=t["border"],
            text_color=t["text"],
            height=34
        )
        if gemini_actual:
            entry_gemini_key.insert(0, gemini_actual)
        entry_gemini_key.pack(fill="x", pady=(0, 6))

        lbl_o = make_label(inner_api, "Clave API OpenAI (Secundaria / Fallback):", tipo="subtitulo")
        lbl_o.pack(anchor="w", pady=(2, 2))

        entry_openai_key = ctk.CTkEntry(
            inner_api,
            placeholder_text="sk-proj-...",
            show="*",
            fg_color=t["input_bg"],
            border_color=t["border"],
            text_color=t["text"],
            height=34
        )
        if openai_actual:
            entry_openai_key.insert(0, openai_actual)
        entry_openai_key.pack(fill="x", pady=(0, 10))

        def toggle_solo_ia():
            self.config["solo_ia_api"] = sw_solo_ia.get()
            guardar_config(self.config)
            if self.config["solo_ia_api"]:
                self._mostrar_toast("Modo 'Solo IA (API)' activado ✅")
            else:
                self._mostrar_toast("Modo con fallback a bot local activado")

        # Toggles para activar/desactivar APIs individuales y bot local
        lbl_toggles_title = make_label(inner_api, "Activar / Desactivar Servicios de IA:", tipo="subtitulo")
        lbl_toggles_title.pack(anchor="w", pady=(8, 4))

        def toggle_gemini():
            self.config["api_gemini_activa"] = sw_gemini.get()
            guardar_config(self.config)
            self._actualizar_indicador_ia()
            estado = "activada" if self.config["api_gemini_activa"] else "desactivada"
            self._mostrar_toast(f"API Gemini {estado}")

        sw_gemini = ctk.CTkSwitch(
            inner_api,
            text="Activar API Google Gemini",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            progress_color=t["accent"],
            command=toggle_gemini
        )
        if self.config.get("api_gemini_activa", True):
            sw_gemini.select()
        else:
            sw_gemini.deselect()
        sw_gemini.pack(anchor="w", pady=(2, 2))

        def toggle_openai():
            self.config["api_openai_activa"] = sw_openai.get()
            guardar_config(self.config)
            self._actualizar_indicador_ia()
            estado = "activada" if self.config["api_openai_activa"] else "desactivada"
            self._mostrar_toast(f"API OpenAI {estado}")

        sw_openai = ctk.CTkSwitch(
            inner_api,
            text="Activar API OpenAI (Fallback)",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            progress_color=t["accent"],
            command=toggle_openai
        )
        if self.config.get("api_openai_activa", True):
            sw_openai.select()
        else:
            sw_openai.deselect()
        sw_openai.pack(anchor="w", pady=(2, 2))

        def toggle_bot_local():
            self.config["bot_local_activo"] = sw_bot_local.get()
            self.config["solo_ia_api"] = not self.config["bot_local_activo"]
            guardar_config(self.config)
            self._actualizar_indicador_ia()
            estado = "activado" if self.config["bot_local_activo"] else "desactivado"
            self._mostrar_toast(f"Bot Local Offline {estado}")

        sw_bot_local = ctk.CTkSwitch(
            inner_api,
            text="Activar Bot Local (Offline)",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            progress_color=t["accent"],
            command=toggle_bot_local
        )
        if self.config.get("bot_local_activo", True) and not self.config.get("solo_ia_api", False):
            sw_bot_local.select()
        else:
            sw_bot_local.deselect()
        sw_bot_local.pack(anchor="w", pady=(2, 10))

        row_api_btns = ctk.CTkFrame(inner_api, fg_color="transparent")
        row_api_btns.pack(fill="x")

        def guardar_claves():
            g_k = entry_gemini_key.get().strip()
            o_k = entry_openai_key.get().strip()
            if g_k:
                guardar_gemini_key(g_k)
            if o_k:
                guardar_openai_key(o_k)
            self._actualizar_indicador_ia()
            messagebox.showinfo("Claves de API", "Claves de API guardadas correctamente (DPAPI).")

        def eliminar_claves():
            borrar_gemini_key()
            borrar_openai_key()
            entry_gemini_key.delete(0, "end")
            entry_openai_key.delete(0, "end")
            self._actualizar_indicador_ia()
            messagebox.showinfo("Claves de API", "Claves de API eliminadas.")

        btn_g_api = make_btn(row_api_btns, "Guardar claves", command=guardar_claves, tipo="primary", height=34)
        btn_g_api.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_e_api = make_btn(row_api_btns, "Eliminar claves", command=eliminar_claves, tipo="danger", height=34)
        btn_e_api.pack(side="right", fill="x", expand=True, padx=(6, 0))

        # 6. Bloque de Asistente Avanzado (AGY CLI)
        import ia.agy_sidecar as agy_sidecar
        card_agy = make_card(scroll, fg_color=t["card"], corner_radius=10, border_color=t["border"])
        card_agy.pack(fill="x", pady=6)

        inner_agy = ctk.CTkFrame(card_agy, fg_color="transparent")
        inner_agy.pack(fill="x", padx=16, pady=14)

        lbl_agy_h = make_label(inner_agy, "🚀 ASISTENTE AVANZADO INTELIGENTE (AGY)", tipo="seccion")
        lbl_agy_h.pack(anchor="w", pady=(0, 4))

        lbl_agy_desc = make_label(
            inner_agy,
            "Integración nativa con Google Antigravity CLI (AGY).\n"
            "Razonamiento avanzado de alta velocidad con bajo consumo de tokens (modo low).",
            tipo="subtitulo",
            wrap=550
        )
        lbl_agy_desc.pack(anchor="w", pady=(0, 6))

        # Checkbox principal: "¿Querés usar el Asistente Avanzado (AGY)?"
        chk_agy = ctk.CTkCheckBox(
            inner_agy,
            text="¿Querés usar el Asistente Avanzado (AGY)?",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            checkmark_color="#ffffff",
            fg_color=t["accent"],
            border_color=t["border"],
            command=lambda: toggle_agy()
        )
        if self.config.get("usar_asistente_agy", False):
            chk_agy.select()
        else:
            chk_agy.deselect()
        chk_agy.pack(anchor="w", pady=(4, 6))

        lbl_agy_estado = make_label(inner_agy, "Estado: Verificando...", tipo="subtitulo")
        lbl_agy_estado.pack(anchor="w", pady=(0, 8))

        def _refrescar_lbl_agy():
            try:
                if not lbl_agy_estado.winfo_exists():
                    return
                if not agy_sidecar.esta_instalado():
                    lbl_agy_estado.configure(text="Estado: ⚪ No instalado en este equipo", text_color=t["muted"])
                elif self.config.get("usar_asistente_agy", False):
                    lbl_agy_estado.configure(text="Estado: 🟢 Vinculado y activo (Modo Low Token)", text_color=t["success"])
                else:
                    lbl_agy_estado.configure(text="Estado: ⏳ Comprobando autorización...", text_color=t["muted"])
                    def _async_verif():
                        autenticado = agy_sidecar.esta_autenticado()
                        def _on_done():
                            try:
                                if not lbl_agy_estado.winfo_exists():
                                    return
                                if autenticado:
                                    lbl_agy_estado.configure(text="Estado: 🟢 Instalado y listo para vincular", text_color=t["success"])
                                else:
                                    lbl_agy_estado.configure(text="Estado: 🟡 Instalado - Requiere código de autorización", text_color=t["warning"])
                            except Exception:
                                pass
                        self.after(0, _on_done)
                    threading.Thread(target=_async_verif, daemon=True).start()
            except Exception:
                pass

        # Campo visible para ingresar y pegar el código de autorización de Google
        lbl_code_title = make_label(inner_agy, "🔑 Código de autorización de Google (desde el navegador):", tipo="subtitulo")
        lbl_code_title.pack(anchor="w", pady=(6, 2))

        entry_agy_code = ctk.CTkEntry(
            inner_agy,
            placeholder_text="Pegá aquí tu código (ej: 4/0ATsMZqCE...)",
            fg_color=t["input_bg"],
            border_color=t["border"],
            text_color=t["text"],
            height=34
        )
        codigo_guardado = self.config.get("codigo_autorizacion_agy", "")
        if not codigo_guardado:
            agy_cfg_data = agy_sidecar.cargar_configuracion_actual()
            if agy_cfg_data and agy_cfg_data.get("codigo_autorizacion"):
                codigo_guardado = agy_cfg_data.get("codigo_autorizacion")
        if codigo_guardado:
            entry_agy_code.insert(0, codigo_guardado)
        entry_agy_code.pack(fill="x", pady=(0, 6))

        row_code_actions = ctk.CTkFrame(inner_agy, fg_color="transparent")
        row_code_actions.pack(fill="x", pady=(0, 10))

        def vincular_codigo_agy():
            code = entry_agy_code.get().strip()
            if not code:
                messagebox.showwarning(
                    "Código Requerido",
                    "Por favor pegá el código de autorización que te proporcionó Google en el navegador.\n"
                    "Si aún no lo abriste, hacé clic en 'Abrir navegador'."
                )
                return

            # Guardar configuración actual en modo low con el código provisto
            agy_sidecar.guardar_configuracion_actual(
                modelo="gemini-3.8-flash-low",
                effort="low",
                codigo_autorizacion=code
            )
            self.config["usar_asistente_agy"] = True
            self.config["codigo_autorizacion_agy"] = code
            guardar_config(self.config)
            chk_agy.select()
            _refrescar_lbl_agy()
            self._actualizar_indicador_ia()
            messagebox.showinfo(
                "Asistente Avanzado",
                "¡Código de autorización registrado con éxito!\n\n"
                "El Asistente Avanzado (AGY) quedó activado en modo bajo consumo (low)."
            )

        def abrir_navegador_para_codigo():
            agy_sidecar.abrir_navegador_login()
            entry_agy_code.focus()
            self._mostrar_toast("Navegador abierto. Iniciá sesión, copiá el código y pegalo aquí.")

        btn_vincular = make_btn(
            row_code_actions,
            "✅ Vincular Código y Activar AGY",
            command=vincular_codigo_agy,
            tipo="primary",
            height=32
        )
        btn_vincular.pack(side="left", padx=(0, 6))

        btn_abrir_nav = make_btn(
            row_code_actions,
            "🌐 Abrir navegador",
            command=abrir_navegador_para_codigo,
            tipo="secondary",
            height=32
        )
        btn_abrir_nav.pack(side="left")

        def _iniciar_descarga_en_segundo_plano():
            win_prog = ctk.CTkToplevel(self)
            win_prog.title("Descargando Asistente Avanzado")
            win_prog.geometry("420x160")
            win_prog.resizable(False, False)
            win_prog.transient(self)
            win_prog.grab_set()

            fr_p = ctk.CTkFrame(win_prog, fg_color=t["card"])
            fr_p.pack(fill="both", expand=True, padx=16, pady=16)

            lbl_info = make_label(
                fr_p,
                "Descargando e instalando el Asistente Avanzado (AGY) en segundo plano...\nPor favor espere unos momentos.",
                tipo="subtitulo",
                wrap=380
            )
            lbl_info.pack(anchor="w", pady=(0, 12))

            pbar = ctk.CTkProgressBar(fr_p, mode="indeterminate", progress_color=t["accent"], height=12)
            pbar.pack(fill="x", pady=(0, 8))
            pbar.start()

            def on_completado(exito: bool, msg: str):
                def _ui_done():
                    try:
                        pbar.stop()
                        win_prog.destroy()
                    except Exception:
                        pass
                    _refrescar_lbl_agy()
                    if exito:
                        messagebox.showinfo(
                            "Asistente Avanzado Instalado",
                            "Cierre este programa para completar la configuración y vuelva a abrirlo."
                        )
                    else:
                        messagebox.showerror("Error de instalación", f"No se pudo completar la instalación: {msg}")
                self.after(0, _ui_done)

            agy_sidecar.instalar_en_segundo_plano(on_completado=on_completado)

        def toggle_agy():
            desea_usar = chk_agy.get()

            if not desea_usar:
                self.config["usar_asistente_agy"] = False
                guardar_config(self.config)
                _refrescar_lbl_agy()
                self._actualizar_indicador_ia()
                self._mostrar_toast("Asistente Avanzado (AGY) desactivado")
                return

            # 1. Verificar si está instalado
            if not agy_sidecar.esta_instalado():
                chk_agy.deselect()
                _iniciar_descarga_en_segundo_plano()
                return

            # 2. Si ya tiene código o está autenticado, activar modo low
            code_actual = entry_agy_code.get().strip() or self.config.get("codigo_autorizacion_agy", "")
            if not code_actual and not agy_sidecar.esta_autenticado():
                chk_agy.deselect()
                resp = messagebox.askokcancel(
                    "Inicio de Sesión Requerido",
                    "Por favor, para continuar, iniciá sesión en Google para obtener el código de autorización y pegalo en el campo de texto."
                )
                if resp:
                    abrir_navegador_para_codigo()
                return

            agy_sidecar.guardar_configuracion_actual(
                modelo="gemini-3.8-flash-low",
                effort="low",
                codigo_autorizacion=code_actual
            )
            self.config["usar_asistente_agy"] = True
            guardar_config(self.config)
            _refrescar_lbl_agy()
            self._actualizar_indicador_ia()
            self._mostrar_toast("Asistente Avanzado (AGY) activado en modo low ✅")

        row_agy_btns = ctk.CTkFrame(inner_agy, fg_color="transparent")
        row_agy_btns.pack(fill="x", pady=(4, 0))

        def desloguear_agy():
            agy_sidecar.borrar_sesion_agy()
            self.config["usar_asistente_agy"] = False
            self.config["codigo_autorizacion_agy"] = ""
            guardar_config(self.config)
            entry_agy_code.delete(0, "end")
            chk_agy.deselect()
            _refrescar_lbl_agy()
            self._actualizar_indicador_ia()
            messagebox.showinfo("Asistente Avanzado", "Sesión de AGY desvinculada correctamente.\nEl ejecutable sigue intacto en tu equipo.")

        def verificar_conexion_agy():
            lbl_agy_estado.configure(text="Estado: ⏳ Probando conexión...", text_color=t["muted"])
            def _verif_thread():
                autenticado = agy_sidecar.esta_autenticado()
                def _update_ui():
                    _refrescar_lbl_agy()
                    if autenticado:
                        self._mostrar_toast("Conexión con AGY exitosa ✅")
                    else:
                        self._mostrar_toast("AGY requiere vincular código de autorización")
                self.after(0, _update_ui)
            threading.Thread(target=_verif_thread, daemon=True).start()

        btn_verif = make_btn(row_agy_btns, "Verificar conexión", command=verificar_conexion_agy, tipo="flat", height=32)
        btn_verif.pack(side="left", padx=(0, 6))

        btn_logout_agy = make_btn(row_agy_btns, "Desvincular / Cerrar sesión", command=desloguear_agy, tipo="secondary", height=32)
        btn_logout_agy.pack(side="left")

        self.after(100, _refrescar_lbl_agy)
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
            if self._current_page_name == "materias" and self._page_materias and hasattr(self, "scroll_cursos") and self.scroll_cursos.winfo_exists():
                self._show_cursos(self.cursos)
            if self._page_pendientes and hasattr(self, "scroll_pendientes") and self.scroll_pendientes.winfo_exists():
                self._show_pendientes()
            if self._page_novedades and hasattr(self, "scroll_novs") and self.scroll_novs.winfo_exists():
                self._show_novedades(self.novedades)
            if self._page_estadisticas and hasattr(self, "scroll_stats") and self.scroll_stats.winfo_exists():
                self._show_estadisticas_locales()

    def _load_datos(self, page_size: int = 120):
        def run():
            try:
                cursos, novedades, nombre = get_escritorio(self.sess, page_size=page_size)
                
                # Enriquecer novedades de tipo email para que no sean estáticas ni genéricas
                try:
                    for n in novedades:
                        if n.get("clase") == "email" and n.get("id_curso"):
                            cid = str(n.get("id_curso"))
                            m = msg_mod.buscar_mensaje_por_novedad(
                                self.sess, cid,
                                fecha_novedad=n.get("fecha", ""),
                                asunto_novedad=n.get("nombre_item", "")
                            )
                            if m:
                                if m.get("asunto"):
                                    n["nombre_item"] = m.get("asunto")
                                if m.get("remitente"):
                                    n["remitente"] = m.get("remitente")
                                if m.get("link"):
                                    n["link"] = m.get("link")
                                if m.get("bandeja"):
                                    n["bandeja"] = m.get("bandeja")
                except Exception as ex:
                    logging.warning(f"Error al enriquecer novedades: {ex}")

                self.cursos = cursos
                self.novedades = novedades
                
                # Actualizar IA
                self.ia.actualizar_datos(cursos, novedades, self.cache_data)
                
                # Precarga en segundo plano de materias 2026 (Requerimiento 3.3)
                self._precargar_materias_background(cursos)

                # Monitoreo de actividades pendientes (si autologueo está activo)
                self._escanear_actividades_background(cursos)

                # Scraping de fuentes externas en segundo plano (Fase 5)
                self._sincronizar_fuentes_externas_background()

                try:
                    self.after(0, self._on_datos_ok, cursos, novedades, nombre)
                except Exception:
                    pass
            except Exception as e:
                try:
                    self.after(0, lambda: self.lbl_estado.configure(text=f"❌ {str(e)[:25]}"))
                except Exception:
                    pass

        threading.Thread(target=run, daemon=True).start()

    def _escanear_actividades_background(self, cursos: list):
        """Monitorea en segundo plano actividades adeudadas si el autologueo está activado."""
        def run_tracker():
            try:
                from backend.actividades_tracker import (
                    escanear_actividades_pendientes,
                    autologueo_esta_activo,
                    debe_mostrar_recordatorio_frecuente,
                    marcar_recordatorio_emitido
                )
                if not autologueo_esta_activo(self.config):
                    return
                # Escanear actividades pendientes y guardar registro persistente
                escanear_actividades_pendientes(self.sess, cursos, self.config)
                # Actualizar sección de pendientes en la UI con las actividades detectadas
                try:
                    self.after(0, self._show_pendientes)
                except Exception:
                    pass

                # Si corresponde recordatorio frecuente por actividad próxima a vencer, mostrar aviso en toast (NUNCA en notificación de sistema)
                if debe_mostrar_recordatorio_frecuente(self.config):
                    marcar_recordatorio_emitido()
                    try:
                        self.after(0, lambda: self._mostrar_toast("⚠️ Tienes actividades pendientes próximas a vencer. Revisa la sección de Pendientes."))
                    except Exception:
                        pass
            except Exception as e:
                logging.debug(f"Error en tracker de actividades background: {e}")

        threading.Thread(target=run_tracker, daemon=True).start()

    def _sincronizar_fuentes_externas_background(self):
        """Ejecuta en segundo plano el scraping del sitio público institucional."""
        def run_externo():
            try:
                from backend.sitio_informativo import SitioInformativoScraper
                scraper_sitio = SitioInformativoScraper()
                scraper_sitio.scrape_completo(max_articulos=15)
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
        self.lbl_nombre.configure(text=nom)
        if self._current_page_name == "materias" and self._page_materias and hasattr(self, "scroll_cursos") and self.scroll_cursos.winfo_exists():
            self._show_cursos(cursos)
        if self._page_pendientes and hasattr(self, "scroll_pendientes") and self.scroll_pendientes.winfo_exists():
            self._show_pendientes()
        if self._page_novedades and hasattr(self, "scroll_novs") and self.scroll_novs.winfo_exists():
            self._show_novedades(novedades)
        if self._page_estadisticas and hasattr(self, "scroll_stats") and self.scroll_stats.winfo_exists():
            self._show_estadisticas_locales()
        self._actualizar_chips_sugerencias()
        self._verificar_y_notificar_novedades(novedades)

    def _refresh(self):
        self.lbl_estado.configure(text="⏳ Actualizando...")
        if hasattr(self, "scroll_cursos") and self.scroll_cursos.winfo_exists():
            clear_frame(self.scroll_cursos)
            lbl1 = make_label(self.scroll_cursos, "⏳ Actualizando materias...", tipo="subtitulo")
            lbl1.pack(pady=20)

        if hasattr(self, "scroll_pendientes") and self.scroll_pendientes.winfo_exists():
            clear_frame(self.scroll_pendientes)
            lblp = make_label(self.scroll_pendientes, "⏳ Actualizando pendientes...", tipo="subtitulo")
            lblp.pack(pady=20)

        if hasattr(self, "scroll_novs") and self.scroll_novs.winfo_exists():
            clear_frame(self.scroll_novs)
            lbl2 = make_label(self.scroll_novs, "⏳ Actualizando novedades...", tipo="subtitulo")
            lbl2.pack(pady=20)

        self._load_datos()

    def _actualizar_sidebar_avatar(self, ruta_o_url: str = None, eliminar: bool = False):
        """Actualiza el avatar del sidebar de forma segura en el hilo principal."""
        if eliminar or not ruta_o_url:
            def _clear():
                try:
                    self.lbl_user_icon.configure(image=None, text="👤")
                    if hasattr(self.lbl_user_icon, "_label"):
                        self.lbl_user_icon._label.configure(image="")
                    self.lbl_user_icon.image = None
                except Exception:
                    pass
            self.after(0, _clear)
            return

        clean_path = ruta_o_url.replace("file://", "").strip()
        if os.path.exists(clean_path):
            def _apply_local():
                try:
                    img = Image.open(clean_path).convert("RGBA")
                    img = img.resize((28, 28), Image.LANCZOS)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(28, 28))
                    self.lbl_user_icon.configure(image=ctk_img, text="")
                    self.lbl_user_icon.image = ctk_img
                except Exception:
                    pass
            self.after(0, _apply_local)
            return

        self._cargar_sidebar_avatar(ruta_o_url)

    def _cargar_sidebar_avatar(self, url: str):
        if not url or not url.startswith("http"):
            return
        def _fetch():
            try:
                import hashlib
                from config import CONFIG_DIR
                avatars_dir = os.path.join(CONFIG_DIR, "avatars")
                os.makedirs(avatars_dir, exist_ok=True)
                clean_url = url.split("?")[0]
                h = hashlib.md5(clean_url.encode("utf-8")).hexdigest()
                cached_file = os.path.join(avatars_dir, f"sb_{h}.png")
                if not os.path.exists(cached_file):
                    r = self.sess.get(url, timeout=8)
                    if r.status_code == 200 and len(r.content) > 100:
                        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
                        img = img.resize((28, 28), Image.LANCZOS)
                        img.save(cached_file, "PNG")
                if os.path.exists(cached_file):
                    def _update():
                        try:
                            pil_img = Image.open(cached_file).convert("RGBA")
                            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(28, 28))
                            self.lbl_user_icon.configure(image=ctk_img, text="")
                            self.lbl_user_icon.image = ctk_img
                        except Exception:
                            pass
                    self.after(0, _update)
            except Exception:
                pass
        threading.Thread(target=_fetch, daemon=True).start()

    def _abrir_modal_perfil(self):
        """Abre la ventana modal interactiva de Perfil y Preferencias del estudiante."""
        from backend.user import get_perfil_personal, guardar_perfil_personal
        t = tema_actual()
        win = ctk.CTkToplevel(self)
        win.title("Perfil y Preferencias")
        win.geometry("600x650")
        win.transient(self)
        win.grab_set()

        hdr = ctk.CTkFrame(win, fg_color=t["sidebar"], corner_radius=0)
        hdr.pack(fill="x")
        make_label(hdr, "⚙ Perfil y Preferencias", tipo="titulo_sm").pack(padx=20, pady=(14, 2), anchor="w")
        make_label(hdr, "Visualiza y edita tus datos personales, foto de perfil y contraseña", tipo="subtitulo").pack(padx=20, pady=(0, 12), anchor="w")

        content = ctk.CTkScrollableFrame(win, fg_color=t["bg"])
        content.pack(fill="both", expand=True, padx=16, pady=10)

        lbl_carg = make_label(content, "⏳ Cargando información de perfil del campus...", tipo="subtitulo")
        lbl_carg.pack(pady=30)

        def _render_perfil(perfil):
            clear_frame(content)

            foto_state = {
                "nueva_ruta": None,
                "eliminar": False,
                "original_url": perfil.get("foto_url", "")
            }

            # ── 1. FOTO DE PERFIL ─────────────────────────────────────
            card_foto = make_card(content, fg_color=t["card"], corner_radius=8, border_color=t["border"])
            card_foto.pack(fill="x", pady=(0, 8), padx=2)

            f_inner = ctk.CTkFrame(card_foto, fg_color="transparent")
            f_inner.pack(fill="x", padx=14, pady=12)

            av_size = (64, 64)
            av_box = ctk.CTkFrame(f_inner, width=av_size[0], height=av_size[1], fg_color=t["item_bg"], corner_radius=32)
            av_box.pack(side="left", padx=(0, 16))
            av_box.pack_propagate(False)

            lbl_av_img = make_label(av_box, "👤", tipo="titulo", anchor="center")
            lbl_av_img.pack(expand=True)

            def _mostrar_avatar_desde_bytes(img_bytes=None, file_path=None):
                try:
                    if file_path:
                        img = Image.open(file_path).convert("RGBA")
                    elif img_bytes:
                        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
                    else:
                        lbl_av_img.configure(image=None, text="👤")
                        if hasattr(lbl_av_img, "_label"):
                            try:
                                lbl_av_img._label.configure(image="")
                            except Exception:
                                pass
                        lbl_av_img.image = None
                        win._avatar_ref = None
                        return
                    img = img.resize(av_size, Image.LANCZOS)
                    ctk_i = ctk.CTkImage(light_image=img, dark_image=img, size=av_size)
                    lbl_av_img.configure(image=ctk_i, text="")
                    lbl_av_img.image = ctk_i
                    win._avatar_ref = ctk_i
                except Exception:
                    lbl_av_img.configure(image=None, text="👤")
                    if hasattr(lbl_av_img, "_label"):
                        try:
                            lbl_av_img._label.configure(image="")
                        except Exception:
                            pass
                    lbl_av_img.image = None
                    win._avatar_ref = None

            orig_url = perfil.get("foto_url", "")
            if orig_url and orig_url.startswith("http"):
                def _fetch_orig():
                    try:
                        r = self.sess.get(orig_url, timeout=8)
                        if r.status_code == 200 and len(r.content) > 100:
                            if not foto_state["nueva_ruta"] and not foto_state["eliminar"]:
                                win.after(0, lambda: _mostrar_avatar_desde_bytes(img_bytes=r.content))
                    except Exception:
                        pass
                threading.Thread(target=_fetch_orig, daemon=True).start()

            f_btns = ctk.CTkFrame(f_inner, fg_color="transparent")
            f_btns.pack(side="left", fill="x", expand=True)

            make_label(f_btns, "Foto de Perfil", tipo="blanco").pack(anchor="w")
            lbl_foto_info = make_label(f_btns, "Formatos permitidos: JPG, PNG", tipo="subtitulo")
            lbl_foto_info.pack(anchor="w", pady=(1, 6))

            row_act_foto = ctk.CTkFrame(f_btns, fg_color="transparent")
            row_act_foto.pack(anchor="w")

            def _seleccionar_foto():
                ruta = filedialog.askopenfilename(
                    parent=win,
                    title="Seleccionar foto de perfil",
                    filetypes=[("Imágenes", "*.jpg;*.jpeg;*.png;*.bmp")]
                )
                if ruta and os.path.exists(ruta):
                    foto_state["nueva_ruta"] = ruta
                    foto_state["eliminar"] = False
                    _mostrar_avatar_desde_bytes(file_path=ruta)
                    lbl_foto_info.configure(text=f"Nueva foto: {os.path.basename(ruta)}")

            def _quitar_foto():
                foto_state["nueva_ruta"] = None
                foto_state["eliminar"] = True
                _mostrar_avatar_desde_bytes(None)
                lbl_foto_info.configure(text="Foto quitada (se aplicará al guardar)")

            btn_cam = make_btn(row_act_foto, "📷 Cambiar foto", command=_seleccionar_foto, tipo="primary", width=115, height=26)
            btn_cam.pack(side="left", padx=(0, 8))

            btn_del_foto = make_btn(row_act_foto, "🗑 Quitar foto", command=_quitar_foto, tipo="danger", width=105, height=26)
            btn_del_foto.pack(side="left")

            # ── 2. DATOS PRINCIPALES ──────────────────────────────────
            card_datos = make_card(content, fg_color=t["card"], corner_radius=8, border_color=t["border"])
            card_datos.pack(fill="x", pady=6, padx=2)

            d_inner = ctk.CTkFrame(card_datos, fg_color="transparent")
            d_inner.pack(fill="x", padx=14, pady=12)

            make_label(d_inner, "Datos Principales", tipo="seccion").pack(anchor="w", pady=(0, 8))

            # Nombre
            make_label(d_inner, "Nombre:", tipo="subtitulo").pack(anchor="w")
            ent_nom = ctk.CTkEntry(d_inner, height=32, fg_color=t["item_bg"])
            ent_nom.insert(0, perfil.get("nombre", ""))
            ent_nom.pack(fill="x", pady=(2, 8))

            # Apellido
            make_label(d_inner, "Apellido:", tipo="subtitulo").pack(anchor="w")
            ent_ape = ctk.CTkEntry(d_inner, height=32, fg_color=t["item_bg"])
            ent_ape.insert(0, perfil.get("apellido", ""))
            ent_ape.pack(fill="x", pady=(2, 8))

            # Email
            make_label(d_inner, "Correo Electrónico:", tipo="subtitulo").pack(anchor="w")
            ent_email = ctk.CTkEntry(d_inner, height=32, fg_color=t["item_bg"])
            ent_email.insert(0, perfil.get("email", ""))
            ent_email.pack(fill="x", pady=(2, 8))

            # Teléfono
            make_label(d_inner, "Teléfono / Celular:", tipo="subtitulo").pack(anchor="w")
            ent_tel = ctk.CTkEntry(d_inner, height=32, fg_color=t["item_bg"])
            ent_tel.insert(0, perfil.get("telefono", ""))
            ent_tel.pack(fill="x", pady=(2, 8))

            # Fecha de nacimiento
            make_label(d_inner, "Fecha de Nacimiento (DD/MM/AAAA):", tipo="subtitulo").pack(anchor="w")
            ent_fnac = ctk.CTkEntry(d_inner, height=32, fg_color=t["item_bg"])
            ent_fnac.insert(0, perfil.get("fecha_nacimiento", ""))
            ent_fnac.pack(fill="x", pady=(2, 4))

            # ── 3. CAMBIO DE CONTRASEÑA ───────────────────────────────
            card_clave = make_card(content, fg_color=t["card"], corner_radius=8, border_color=t["border"])
            card_clave.pack(fill="x", pady=6, padx=2)

            c_inner = ctk.CTkFrame(card_clave, fg_color="transparent")
            c_inner.pack(fill="x", padx=14, pady=12)

            make_label(c_inner, "Cambio de Contraseña (Opcional)", tipo="seccion").pack(anchor="w")
            make_label(c_inner, "La clave debe contener al menos 8 caracteres y al menos 1 letra mayúscula.", tipo="subtitulo").pack(anchor="w", pady=(2, 8))

            make_label(c_inner, "Contraseña actual (requerida sólo para cambiar clave):", tipo="subtitulo").pack(anchor="w")
            ent_clave_actual = ctk.CTkEntry(c_inner, height=32, fg_color=t["item_bg"], show="*")
            ent_clave_actual.pack(fill="x", pady=(2, 8))

            make_label(c_inner, "Nueva contraseña:", tipo="subtitulo").pack(anchor="w")
            ent_clave_nueva = ctk.CTkEntry(c_inner, height=32, fg_color=t["item_bg"], show="*")
            ent_clave_nueva.pack(fill="x", pady=(2, 8))

            make_label(c_inner, "Repetir nueva contraseña:", tipo="subtitulo").pack(anchor="w")
            ent_clave_nueva2 = ctk.CTkEntry(c_inner, height=32, fg_color=t["item_bg"], show="*")
            ent_clave_nueva2.pack(fill="x", pady=(2, 4))

            # ── BOTONES INFERIORES ────────────────────────────────────
            bot_bar = ctk.CTkFrame(win, fg_color="transparent")
            bot_bar.pack(fill="x", padx=16, pady=(4, 12))

            lbl_save_status = make_label(bot_bar, "", tipo="subtitulo")
            lbl_save_status.pack(side="left", fill="x", expand=True)

            def _do_guardar():
                nom_v = ent_nom.get().strip()
                ape_v = ent_ape.get().strip()
                email_v = ent_email.get().strip()
                tel_v = ent_tel.get().strip()
                fnac_v = ent_fnac.get().strip()

                c_act = ent_clave_actual.get().strip()
                c_new = ent_clave_nueva.get().strip()
                c_new2 = ent_clave_nueva2.get().strip()

                if not nom_v or not ape_v:
                    messagebox.showwarning("Atención", "Nombre y Apellido son obligatorios.")
                    return

                if c_new or c_new2 or c_act:
                    if not c_act:
                        messagebox.showwarning("Atención", "Debes ingresar tu contraseña actual para cambiarla.")
                        return
                    if c_new != c_new2:
                        messagebox.showwarning("Atención", "Las contraseñas nuevas no coinciden.")
                        return
                    if len(c_new) < 8:
                        messagebox.showwarning("Atención", "La nueva clave debe contener al menos 8 caracteres.")
                        return
                    if not any(ch.isupper() for ch in c_new):
                        messagebox.showwarning("Atención", "La nueva clave debe contener al menos una letra mayúscula.")
                        return

                btn_guardar.configure(state="disabled", text="⏳ Guardando...")
                lbl_save_status.configure(text="⏳ Guardando cambios en el campus virtual...")

                def save_task():
                    datos_update = {
                        "raw_form": perfil.get("raw_form", {}),
                        "nombre": nom_v,
                        "apellido": ape_v,
                        "email": email_v,
                        "telefono": tel_v,
                        "fecha_nacimiento": fnac_v
                    }
                    ok, res_msg = guardar_perfil_personal(
                        self.sess,
                        datos_update,
                        nueva_foto_path=foto_state["nueva_ruta"],
                        eliminar_foto=foto_state["eliminar"],
                        clave_actual=c_act,
                        nueva_clave=c_new
                    )

                    def on_save_done():
                        if ok:
                            messagebox.showinfo("Perfil Actualizado", "¡Tus datos de perfil han sido guardados con éxito!", parent=win)
                            nom_completo = f"{nom_v} {ape_v}".strip()
                            self.lbl_nombre.configure(text=nom_completo)
                            # Si se seleccionó nueva foto o se eliminó, actualizar avatar sidebar de forma segura
                            if foto_state["eliminar"]:
                                self._actualizar_sidebar_avatar(eliminar=True)
                            elif foto_state["nueva_ruta"]:
                                self._actualizar_sidebar_avatar(ruta_o_url=foto_state["nueva_ruta"])
                            win.destroy()
                        else:
                            btn_guardar.configure(state="normal", text="Guardar cambios")
                            lbl_save_status.configure(text=f"❌ {res_msg}")
                            messagebox.showerror("Error al Guardar", res_msg, parent=win)

                    win.after(0, on_save_done)

                threading.Thread(target=save_task, daemon=True).start()

            btn_cancel = make_btn(bot_bar, "Cancelar", command=win.destroy, tipo="flat", height=32, width=90)
            btn_cancel.pack(side="right", padx=(8, 0))

            btn_guardar = make_btn(bot_bar, "Guardar cambios", command=_do_guardar, tipo="primary", height=32, width=130)
            btn_guardar.pack(side="right")

        def _fetch_profile():
            try:
                perfil_data = get_perfil_personal(self.sess)
                win.after(0, lambda: _render_perfil(perfil_data))
            except Exception as e:
                win.after(0, lambda: make_label(content, f"Error al cargar perfil: {e}", tipo="subtitulo").pack(pady=20))

        threading.Thread(target=_fetch_profile, daemon=True).start()



