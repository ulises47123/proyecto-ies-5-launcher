"""
ui/curso_detail.py — Vista detallada de una materia:
Programa interactivo con Acordeón por Unidades/Clases, Visor de PDFs y Enlaces web clicables,
Indicador visual de estado de actividades (Verde: Entregada / Naranja: Pendiente / Rojo: Cerrada),
Fechas de apertura/cierre resaltadas, Sección de Realización/Entrega,
Mensajes con lectura completa, Calificaciones y Contactos (con foto/avatar docente y copia de email).
Adaptado 100% para Windows con CustomTkinter.
"""
import os
import re
import io
import threading
import tempfile
import webbrowser
from PIL import Image
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from ui.widgets import make_label, make_btn, make_card, make_separator, make_badge, clear_frame
from ui.theme import tema_actual, registrar_listener_tema, desregistrar_listener_tema
from backend.session import CampusSession
from backend import programa as prog_mod
from backend import mensajes as msg_mod
from backend import calificaciones as cal_mod
from backend import contactos as cont_mod
from backend import cache_utils as chat_mod


class CursoDetailView(ctk.CTkFrame):
    """Vista completa de una materia con sus sub-secciones."""

    def __init__(self, parent, sess: CampusSession, curso: dict, on_back, cached_data: dict = None, actividad_inicial: dict = None):
        t = tema_actual()
        super().__init__(parent, fg_color=t["bg"])
        self.sess = sess
        self.curso = curso
        self.on_back = on_back
        self.cached_data = cached_data or {}
        self.actividad_inicial = actividad_inicial
        self._current_tab = 0
        self._msg_loaded = False
        self._cal_loaded = False
        self._cont_loaded = False
        self._chat_loaded = False
        self._contactos_data = None
        self._acordeon_estados = {}  # {unidad_id: bool_abierto}
        self._current_bandeja = "Inbox"
        self._selected_trash_ids = set()
        self._trash_chk_widgets = []
        self._destroyed = False

        self._build()
        registrar_listener_tema(self._on_tema_update)
        
        # Activar tab 0 de inicio y asegurar visibilidad
        self._switch_tab(0)

        # Carga dinámica del programa: si hay datos en caché, mostrarlos de inmediato
        # y luego actualizar en segundo plano para que nunca quede información estática.
        if self.cached_data and self.cached_data.get("programa"):
            self._show_programa(self.cached_data["programa"])
            self._actualizar_programa_background()
        else:
            self._load_programa()

        # Si se solicitó abrir directamente una actividad específica (desde la sección Pendientes)
        if self.actividad_inicial:
            self.after(350, self._abrir_actividad_inicial)

    def _abrir_actividad_inicial(self):
        if not self.actividad_inicial or getattr(self, "_destroyed", False) or not self.winfo_exists():
            return
        act = self.actividad_inicial
        tit = act.get("titulo", "Actividad").replace("⏰", "").replace("🔥", "").replace("✏️", "").strip()
        item = {
            "tipo": "actividad",
            "titulo": tit,
            "url": act.get("url", "")
        }
        self._abrir_item_programa(item)

    def destroy(self):
        self._destroyed = True
        desregistrar_listener_tema(self._on_tema_update)
        super().destroy()

    def _on_tema_update(self, t):
        if getattr(self, "_destroyed", False) or not self.winfo_exists():
            return
        self.configure(fg_color=t["bg"])
        self.after(50, self._refresh_ui)

    def _refresh_ui(self):
        if getattr(self, "_destroyed", False) or not self.winfo_exists():
            return
        for w in self.winfo_children():
            w.destroy()
        self._build()
        self._switch_tab(self._current_tab)

    def _build(self):
        t = tema_actual()

        # ── Header con botón volver y título ──────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(16, 8))

        btn_back = make_btn(
            hdr, "← Volver",
            command=self.on_back,
            tipo="flat", width=90, height=32
        )
        btn_back.pack(side="left", padx=(0, 14))

        curso_color = self.curso.get("color", t["accent"])
        bar = ctk.CTkFrame(hdr, width=5, height=28, fg_color=curso_color, corner_radius=2)
        bar.pack(side="left", padx=(0, 10))

        lbl_nombre = make_label(hdr, self.curso["nombre"], tipo="titulo", wrap=650)
        lbl_nombre.pack(side="left", fill="x", expand=True)

        sep = make_separator(self)
        sep.pack(fill="x", padx=20, pady=(4, 8))

        # ── Barra de sub-tabs ─────────────────────────────────────
        self.tab_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_bar.pack(fill="x", padx=20, pady=(0, 10))

        self.tab_buttons = []
        tab_names = [
            ("📚 Programa y Clases", 0),
            ("✉ Mensajes", 1),
            ("🎓 Calificaciones", 2),
            ("👥 Contactos", 3),
            ("💬 Chat General", 4)
        ]

        for name, idx in tab_names:
            btn = make_btn(
                self.tab_bar, name,
                command=lambda i=idx: self._switch_tab(i),
                tipo="primary" if self._current_tab == idx else "flat",
                height=32, width=135
            )
            btn.pack(side="left", padx=3)
            self.tab_buttons.append(btn)

        # ── Contenedor de contenido ───────────────────────────────
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Páginas
        self.page_programa = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")
        self.page_mensajes = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")
        self.page_calificaciones = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")
        self.page_contactos = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.page_chat = ctk.CTkFrame(self.content_container, fg_color="transparent")

        # Asegurar que la pestaña 0 (Programa) esté empaquetada y visible por defecto
        self.page_programa.pack(fill="both", expand=True)

    def _switch_tab(self, idx):
        self._current_tab = idx
        t = tema_actual()

        for i, b in enumerate(self.tab_buttons):
            if i == idx:
                b.configure(fg_color=t["accent"], hover_color=t["accent_hover"], text_color=t["btn_text"])
            else:
                b.configure(fg_color=t["item_bg"], hover_color=t["border"], text_color=t["text"])

        # Ocultar todas las páginas
        self.page_programa.pack_forget()
        self.page_mensajes.pack_forget()
        self.page_calificaciones.pack_forget()
        self.page_contactos.pack_forget()
        self.page_chat.pack_forget()

        # Mostrar la seleccionada
        if idx == 0:
            self.page_programa.pack(fill="both", expand=True)
            try:
                self.page_programa.update_idletasks()
                if hasattr(self.page_programa, "_parent_canvas"):
                    self.page_programa._parent_canvas.configure(
                        scrollregion=self.page_programa._parent_canvas.bbox("all")
                    )
            except Exception:
                pass
        elif idx == 1:
            self.page_mensajes.pack(fill="both", expand=True)
            if not self._msg_loaded:
                self._msg_loaded = True
                self._load_mensajes()
        elif idx == 2:
            self.page_calificaciones.pack(fill="both", expand=True)
            if not self._cal_loaded:
                self._cal_loaded = True
                self._load_calificaciones()
        elif idx == 3:
            self.page_contactos.pack(fill="both", expand=True)
            if not self._cont_loaded:
                self._cont_loaded = True
                self._load_contactos()
        elif idx == 4:
            self.page_chat.pack(fill="both", expand=True)
            if not self._chat_loaded:
                self._chat_loaded = True
                self._load_chat()

    def _guardar_programa_en_cache(self, unidades):
        try:
            from config import cargar_cache, guardar_cache
            cache = cargar_cache() or {}
            mats = cache.setdefault("materias_detalle", {})
            cid = str(self.curso.get("id"))
            entry = mats.setdefault(cid, {})
            entry["id"] = cid
            entry["nombre"] = self.curso.get("nombre")
            entry["programa"] = unidades
            guardar_cache(cache)
        except Exception:
            pass

    # ── PROGRAMA Y CLASES (ACORDEÓN) ──────────────────────────
    def _actualizar_programa_background(self):
        """Actualiza el programa en segundo plano para reflejar cambios dinámicos del campus."""
        def run():
            try:
                unidades = prog_mod.get_programa(self.sess, self.curso["id"])
                if getattr(self, "_destroyed", False) or not self.winfo_exists():
                    return
                if unidades:
                    self._guardar_programa_en_cache(unidades)
                    self.cached_data["programa"] = unidades
                    self.after(0, self._show_programa, unidades)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def _load_programa(self):
        clear_frame(self.page_programa)
        lbl_cargando = make_label(self.page_programa, "⏳ Cargando programa y unidades...", tipo="subtitulo")
        lbl_cargando.pack(pady=20)
        self.page_programa.pack(fill="both", expand=True)

        def run():
            try:
                unidades = prog_mod.get_programa(self.sess, self.curso["id"])
                if getattr(self, "_destroyed", False) or not self.winfo_exists():
                    return
                self._guardar_programa_en_cache(unidades)
                self.cached_data["programa"] = unidades
                self.after(0, self._show_programa, unidades)
            except Exception as e:
                if getattr(self, "_destroyed", False) or not self.winfo_exists():
                    return
                self.after(0, self._show_error, self.page_programa, str(e))

        threading.Thread(target=run, daemon=True).start()

    def _show_programa(self, unidades):
        if getattr(self, "_destroyed", False) or not self.winfo_exists():
            return
        t = tema_actual()
        clear_frame(self.page_programa)

        if self._current_tab == 0:
            self.page_programa.pack(fill="both", expand=True)

        if not unidades:
            lbl = make_label(self.page_programa, "ℹ No hay contenido de programa disponible para esta materia.", tipo="subtitulo")
            lbl.pack(pady=20, padx=10)
            return

        for idx, u in enumerate(unidades):
            uid = u.get("id") or str(idx)
            # Por defecto, la primera unidad abierta y el resto colapsadas
            if uid not in self._acordeon_estados:
                self._acordeon_estados[uid] = (idx == 0)

            self._render_unidad_acordeon(self.page_programa, u, uid)

        # Forzar actualización inmediata de geometría en CTkScrollableFrame
        try:
            self.page_programa.update_idletasks()
            if hasattr(self.page_programa, "_parent_canvas"):
                self.page_programa._parent_canvas.configure(
                    scrollregion=self.page_programa._parent_canvas.bbox("all")
                )
        except Exception:
            pass

    def _render_unidad_acordeon(self, parent, u: dict, uid: str):
        t = tema_actual()
        items = u.get("items", [])
        tiene_items = len(items) > 0

        card = make_card(parent, fg_color=t["card"], corner_radius=10, border_color=t["border"])
        card.pack(fill="x", pady=5, padx=2)

        # Cabecera de Acordeón Clicable
        hdr_frame = ctk.CTkFrame(
            card,
            fg_color="transparent",
            corner_radius=8,
            cursor="hand2"
        )
        hdr_frame.pack(fill="x", padx=4, pady=4)

        hdr_inner = ctk.CTkFrame(hdr_frame, fg_color="transparent")
        hdr_inner.pack(fill="x", padx=12, pady=6)

        flecha = "▼" if self._acordeon_estados.get(uid, False) else "▶"
        lbl_flecha = make_label(hdr_inner, flecha, tipo="seccion")
        lbl_flecha.pack(side="left", padx=(0, 10))

        lbl_u = make_label(hdr_inner, f"📦 {u['nombre']}", tipo="verde", wrap=540)
        lbl_u.pack(side="left", fill="x", expand=True)

        cnt_txt = f"{len(items)} ítems" if tiene_items else "Sin contenido"
        lbl_cnt = make_label(hdr_inner, cnt_txt, tipo="subtitulo")
        lbl_cnt.pack(side="right", padx=(8, 0))

        # Configurar eventos de clic y hover
        def _on_click(event=None):
            self._toggle_acordeon(uid)

        def _on_enter(event=None):
            hdr_frame.configure(fg_color=t["item_bg"])

        def _on_leave(event=None):
            hdr_frame.configure(fg_color="transparent")

        for w in (hdr_frame, hdr_inner, lbl_flecha, lbl_u, lbl_cnt):
            w.bind("<Button-1>", _on_click)
            w.bind("<Enter>", _on_enter)
            w.bind("<Leave>", _on_leave)

        # Contenedor de contenido colapsable
        if self._acordeon_estados.get(uid, False):
            if not tiene_items:
                vacio_box = ctk.CTkFrame(card, fg_color="transparent")
                vacio_box.pack(fill="x", padx=16, pady=(0, 12))
                lbl_v = make_label(vacio_box, "ℹ Esta clase aún no tiene contenido o actividades cargadas.", tipo="subtitulo")
                lbl_v.pack(anchor="w")
                return

            items_box = ctk.CTkFrame(card, fg_color="transparent")
            items_box.pack(fill="x", padx=14, pady=(0, 12))

            ICONOS = {"archivo": "📎", "texto": "📄", "actividad": "✏️", "link": "🔗", "otro": "•"}
            for item in items:
                item_row = ctk.CTkFrame(items_box, fg_color=t["item_bg"], corner_radius=6, border_width=1, border_color=t["border"])
                item_row.pack(fill="x", pady=3)

                icon = ICONOS.get(item.get("tipo"), "•")
                
                left_box = ctk.CTkFrame(item_row, fg_color="transparent")
                left_box.pack(side="left", fill="x", expand=True, padx=12, pady=6)

                # Si es actividad, mostrar indicador de estado con color sólido (Verde/Naranja/Rojo)
                tipo = item.get("tipo")
                est_color = item.get("estado_color", "orange")
                est_txt = item.get("estado", "Pendiente")
                
                # Fila de título con indicador sólido (Requerimiento 1)
                tit_row = ctk.CTkFrame(left_box, fg_color="transparent")
                tit_row.pack(anchor="w", fill="x")

                if tipo == "actividad":
                    color_solido = "#00CC66" if est_color == "green" else ("#FF8800" if est_color == "orange" else "#FF2222")
                    badge_dot = ctk.CTkFrame(tit_row, width=12, height=12, corner_radius=3, fg_color=color_solido)
                    badge_dot.pack(side="left", padx=(0, 8), pady=2)
                    badge_dot.pack_propagate(False)

                    lbl_i = make_label(tit_row, item['titulo'], tipo="blanco", wrap=420)
                    lbl_i.pack(side="left", anchor="w")
                else:
                    lbl_i = make_label(tit_row, f"{icon}  {item['titulo']}", tipo="blanco", wrap=440)
                    lbl_i.pack(side="left", anchor="w")

                sub_info = []
                if tipo == "actividad":
                    sub_info.append(f"Estado: {est_txt}")
                    if item.get("fecha_apertura"):
                        sub_info.append(item["fecha_apertura"])
                elif item.get("tipo_desc"):
                    sub_info.append(item["tipo_desc"])

                if sub_info:
                    lbl_td = make_label(left_box, " • ".join(sub_info), tipo="subtitulo")
                    lbl_td.pack(anchor="w", pady=(2, 0))

                # Botón Abrir / Ver
                btn_action = make_btn(
                    item_row, "Abrir ↗",
                    command=lambda it=item: self._abrir_item_programa(it),
                    tipo="primary" if tipo == "actividad" else "flat",
                    width=75, height=28
                )
                btn_action.pack(side="right", padx=12, pady=6)

    def _toggle_acordeon(self, uid: str):
        self._acordeon_estados[uid] = not self._acordeon_estados.get(uid, False)
        # Recargar vista de programa
        if self.cached_data and self.cached_data.get("programa"):
            self._show_programa(self.cached_data["programa"])
        else:
            self._load_programa()

    def _abrir_item_programa(self, item: dict):
        """Abre un modal interactivo para ver la actividad/texto, links o descargar/visualizar archivo."""
        tipo = item.get("tipo")
        url = item.get("url", "")

        if tipo == "link":
            try:
                webbrowser.open(url)
            except Exception:
                pass
            return

        t = tema_actual()
        top = ctk.CTkToplevel(self)
        top.title(f"{item.get('titulo')}")
        top.geometry("680x600")
        top.transient(self)
        top.grab_set()

        hdr = ctk.CTkFrame(top, fg_color=t["sidebar"], corner_radius=0)
        hdr.pack(fill="x")

        lbl_t = make_label(hdr, item.get('titulo', 'Detalle de ítem'), tipo="titulo_sm", wrap=620)
        lbl_t.pack(padx=20, pady=(16, 4), anchor="w")

        lbl_s = make_label(hdr, f"Tipo: {item.get('tipo_desc') or tipo.capitalize()}", tipo="subtitulo")
        lbl_s.pack(padx=20, pady=(0, 14), anchor="w")

        content = ctk.CTkScrollableFrame(top, fg_color=t["bg"])
        content.pack(fill="both", expand=True, padx=16, pady=12)

        lbl_carg = make_label(content, "⏳ Cargando contenido del campus...", tipo="subtitulo")
        lbl_carg.pack(pady=30)

        def run():
            if tipo == "actividad":
                detalle = prog_mod.get_detalle_actividad(self.sess, url)
                self.after(0, self._render_modal_actividad, content, detalle, top)
            elif tipo == "texto":
                data_txt = prog_mod.get_contenido_texto(self.sess, url)
                self.after(0, self._render_modal_texto, content, data_txt, top)
            elif tipo == "archivo":
                self.after(0, self._render_modal_archivo, content, item, top)
            else:
                data_txt = prog_mod.get_contenido_texto(self.sess, url)
                self.after(0, self._render_modal_texto, content, data_txt, top)

        threading.Thread(target=run, daemon=True).start()

    def _render_modal_actividad(self, parent, detalle: dict, top_win):
        t = tema_actual()
        clear_frame(parent)

        # 1. Bloque de Fechas y Estado Resaltado (Requerimiento 2.3)
        card_estado = make_card(parent, fg_color=t["card"], corner_radius=8, border_color=t["border"])
        card_estado.pack(fill="x", pady=(0, 8))

        inner_e = ctk.CTkFrame(card_estado, fg_color="transparent")
        inner_e.pack(fill="x", padx=16, pady=12)

        col_est = detalle.get("estado_color", "orange")
        # Colores fijos de alto contraste según Requerimiento 6
        badge_bg = "#00cc66" if col_est == "green" else ("#ff8800" if col_est == "orange" else "#ff2222")

        lbl_fechas = make_label(inner_e, f"📅 Fechas: {detalle.get('fechas', 'Sin fecha')}", tipo="seccion", wrap=380)
        lbl_fechas.pack(side="left")

        badge_est = make_badge(inner_e, f"● {detalle.get('estado', 'Pendiente')}", bg_color=badge_bg, text_color="#ffffff")
        badge_est.pack(side="right")

        # 2. Enunciado / Instrucciones
        card_cuerpo = make_card(parent, fg_color=t["card"], corner_radius=8, border_color=t["border"])
        card_cuerpo.pack(fill="x", pady=4)

        inner_c = ctk.CTkFrame(card_cuerpo, fg_color="transparent")
        inner_c.pack(fill="x", padx=16, pady=14)

        lbl_h_cons = make_label(inner_c, "CONSIGNA / INSTRUCCIONES", tipo="seccion")
        lbl_h_cons.pack(anchor="w", pady=(0, 6))

        lbl_cuerpo = make_label(inner_c, detalle.get("cuerpo", ""), tipo="blanco", wrap=600)
        lbl_cuerpo.pack(anchor="w")

        # Imágenes incrustadas o adjuntas (Requerimiento 4)
        imagenes = detalle.get("imagenes", [])
        if imagenes:
            lbl_img_h = make_label(inner_c, "🖼️ IMÁGENES DE LA ACTIVIDAD", tipo="seccion")
            lbl_img_h.pack(anchor="w", pady=(14, 6))

            for img_url in imagenes:
                img_container = ctk.CTkFrame(inner_c, fg_color=t["item_bg"], corner_radius=8, border_width=1, border_color=t["border"])
                img_container.pack(fill="x", pady=6)
                
                lbl_loading = make_label(img_container, "⏳ Cargando imagen...", tipo="subtitulo")
                lbl_loading.pack(padx=12, pady=12)

                def cargar_img_bg(url=img_url, container=img_container, lbl_load=lbl_loading):
                    try:
                        r_img = self.sess.get(url, timeout=15)
                        pil_img = Image.open(io.BytesIO(r_img.content))
                        
                        # Escalar proporcionalmente hasta un ancho max de 540px
                        orig_w, orig_h = pil_img.size
                        max_w = 540
                        if orig_w > max_w:
                            ratio = max_w / float(orig_w)
                            new_w = max_w
                            new_h = int(float(orig_h) * ratio)
                        else:
                            new_w, new_h = orig_w, orig_h

                        def mostrar_img():
                            try:
                                lbl_load.destroy()
                                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(new_w, new_h))
                                img_lbl = ctk.CTkLabel(container, image=ctk_img, text="")
                                img_lbl.image = ctk_img
                                img_lbl.pack(padx=8, pady=8)
                            except Exception:
                                pass
                        
                        self.after(0, mostrar_img)
                    except Exception as ex:
                        def mostrar_err():
                            lbl_load.configure(text=f"🖼️ [Imagen no visualizable: {url.split('/')[-1]}]")
                        self.after(0, mostrar_err)

                threading.Thread(target=cargar_img_bg, daemon=True).start()

        # Hipervínculos clicables en la consigna (Requerimiento 2.2)
        links = detalle.get("links", [])
        if links:
            lbl_lnk_h = make_label(inner_c, "ENLACES DE LA ACTIVIDAD", tipo="seccion")
            lbl_lnk_h.pack(anchor="w", pady=(12, 6))

            for lk in links:
                btn_lnk = make_btn(
                    inner_c, f"🔗 {lk['texto']}",
                    command=lambda u=lk['url']: webbrowser.open(u),
                    tipo="flat", height=28, anchor="w"
                )
                btn_lnk.pack(fill="x", pady=2)

        # Adjuntos de la consigna
        adjuntos = detalle.get("adjuntos", [])
        if adjuntos:
            card_adj = make_card(parent, fg_color=t["card"], corner_radius=8, border_color=t["border"])
            card_adj.pack(fill="x", pady=4)

            inner_a = ctk.CTkFrame(card_adj, fg_color="transparent")
            inner_a.pack(fill="x", padx=16, pady=12)

            lbl_adj_h = make_label(inner_a, "ARCHIVOS Y MATERIALES ADJUNTOS", tipo="seccion")
            lbl_adj_h.pack(anchor="w", pady=(0, 6))

            for adj in adjuntos:
                row_adj = ctk.CTkFrame(inner_a, fg_color="transparent")
                row_adj.pack(fill="x", pady=3)

                lbl_a_nom = make_label(row_adj, f"📎 {adj['nombre']}", tipo="blanco", wrap=400)
                lbl_a_nom.pack(side="left")

                if adj['url'].lower().endswith('.pdf') or 'pdf' in adj['nombre'].lower():
                    btn_v = make_btn(
                        row_adj, "Ver PDF ↗",
                        command=lambda u=adj['url'], nom=adj['nombre']: self._visualizar_pdf(u, nom),
                        tipo="primary", width=90, height=28
                    )
                    btn_v.pack(side="right", padx=(4, 0))

                btn_d = make_btn(
                    row_adj, "Descargar 📥",
                    command=lambda u=adj['url'], nom=adj['nombre']: self._descargar_archivo(u, nom),
                    tipo="flat", width=95, height=28
                )
                btn_d.pack(side="right")

        # 3. Sección Realización / Entrega (Requerimiento 2.4)
        entrega = detalle.get("entrega")
        if entrega:
            card_ent = make_card(parent, fg_color=t["card"], corner_radius=8, border_color=t["success"])
            card_ent.pack(fill="x", pady=6)

            inner_ent = ctk.CTkFrame(card_ent, fg_color="transparent")
            inner_ent.pack(fill="x", padx=16, pady=14)

            lbl_ent_h = make_label(inner_ent, "✅ TU ENTREGA / REALIZACIÓN", tipo="seccion")
            lbl_ent_h.pack(anchor="w", pady=(0, 6))

            lbl_ent_txt = make_label(inner_ent, entrega.get("texto", ""), tipo="blanco", wrap=600)
            lbl_ent_txt.pack(anchor="w")

            for e_adj in entrega.get("adjuntos", []):
                btn_ea = make_btn(
                    inner_ent, f"📥 {e_adj['nombre']}",
                    command=lambda u=e_adj['url'], nom=e_adj['nombre']: self._descargar_archivo(u, nom),
                    tipo="primary", height=30
                )
                btn_ea.pack(fill="x", pady=4)
        elif detalle.get("permite_entrega") or detalle.get("estado_color") == "orange":
            # Botón para Realizar / Entregar Actividad
            card_act_ent = make_card(parent, fg_color=t["card"], corner_radius=8, border_color=t["warning"])
            card_act_ent.pack(fill="x", pady=6)

            inner_act_ent = ctk.CTkFrame(card_act_ent, fg_color="transparent")
            inner_act_ent.pack(fill="x", padx=16, pady=14)

            lbl_ae_h = make_label(inner_act_ent, "📝 ENTREGAR ESTA ACTIVIDAD", tipo="seccion")
            lbl_ae_h.pack(anchor="w", pady=(0, 4))

            lbl_ae_desc = make_label(
                inner_act_ent,
                "Podés redactar un comentario y adjuntar un archivo para enviar tu realización al aula.",
                tipo="subtitulo",
                wrap=550
            )
            lbl_ae_desc.pack(anchor="w", pady=(0, 8))

            btn_entregar = make_btn(
                inner_act_ent, "Realizar Entrega / Adjuntar Archivo 📤",
                command=lambda act=detalle: self._abrir_dialogo_entrega(act, top_win),
                tipo="primary", height=34
            )
            btn_entregar.pack(fill="x")

        bot = ctk.CTkFrame(top_win, fg_color="transparent")
        bot.pack(fill="x", padx=16, pady=(0, 12))
        btn_close = make_btn(bot, "Cerrar", command=top_win.destroy, tipo="primary", height=34)
        btn_close.pack(fill="x")

    def _abrir_dialogo_entrega(self, act: dict, parent_modal=None):
        """Abre un diálogo para redactar un comentario y seleccionar un archivo para la entrega."""
        t = tema_actual()
        diag = ctk.CTkToplevel(self)
        diag.title(f"Entregar Actividad: {act.get('titulo', '')[:40]}")
        diag.geometry("540x480")
        diag.transient(parent_modal if parent_modal else self)
        diag.grab_set()

        hdr = ctk.CTkFrame(diag, fg_color=t["sidebar"], corner_radius=0)
        hdr.pack(fill="x")

        lbl_t = make_label(hdr, "📤 Entrega de Actividad", tipo="titulo_sm")
        lbl_t.pack(padx=20, pady=(16, 4), anchor="w")

        lbl_s = make_label(hdr, act.get("titulo", "Actividad"), tipo="subtitulo", wrap=500)
        lbl_s.pack(padx=20, pady=(0, 14), anchor="w")

        body = ctk.CTkFrame(diag, fg_color=t["bg"])
        body.pack(fill="both", expand=True, padx=20, pady=16)

        lbl_txt = make_label(body, "Texto / Comentario de la Entrega:", tipo="seccion")
        lbl_txt.pack(anchor="w", pady=(0, 4))

        txt_box = ctk.CTkTextbox(body, height=140, fg_color=t["item_bg"], text_color=t["text"], border_color=t["border"], border_width=1)
        txt_box.pack(fill="x", pady=(0, 12))

        lbl_adj = make_label(body, "Archivo Adjunto (Opcional):", tipo="seccion")
        lbl_adj.pack(anchor="w", pady=(0, 4))

        file_row = ctk.CTkFrame(body, fg_color="transparent")
        file_row.pack(fill="x", pady=(0, 16))

        selected_file_path = [""]
        lbl_file = make_label(file_row, "Ningún archivo seleccionado", tipo="subtitulo", wrap=350)
        lbl_file.pack(side="left", fill="x", expand=True)

        def _seleccionar():
            fpath = filedialog.askopenfilename(title="Seleccionar archivo para entrega")
            if fpath:
                selected_file_path[0] = fpath
                lbl_file.configure(text=os.path.basename(fpath), text_color=t["accent"])

        btn_sel = make_btn(file_row, "Examinar...", command=_seleccionar, tipo="flat", width=95, height=30)
        btn_sel.pack(side="right")

        lbl_status = make_label(body, "", tipo="subtitulo")
        lbl_status.pack(anchor="w", pady=(0, 8))

        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x")

        def _enviar():
            comentario = txt_box.get("1.0", "end").strip()
            archivo = selected_file_path[0]

            if not comentario and not archivo:
                messagebox.showwarning("Atención", "Por favor ingresa un comentario o adjunta un archivo para enviar.")
                return

            btn_send.configure(state="disabled", text="⏳ Enviando entrega...")
            lbl_status.configure(text="Conectando con el campus y enviando entrega...")

            def run():
                act_id = act.get("id") or act.get("id_actividad", "")
                res = prog_mod.realizar_entrega_actividad(
                    self.sess,
                    self.curso["id"],
                    act_id,
                    texto=comentario,
                    archivo_path=archivo if archivo else None
                )

                def after_send():
                    if res.get("ok"):
                        messagebox.showinfo("Entrega Enviada", "¡Tu entrega ha sido enviada con éxito al campus virtual!")
                        diag.destroy()
                        if parent_modal:
                            parent_modal.destroy()
                        self._load_programa()
                    else:
                        btn_send.configure(state="normal", text="Confirmar y Enviar Entrega")
                        lbl_status.configure(text=f"❌ {res.get('msg', 'Error al enviar')}", text_color=t["error"])
                        messagebox.showerror("Error al Entregar", f"No se pudo completar el envío:\n{res.get('msg')}")

                self.after(0, after_send)

            threading.Thread(target=run, daemon=True).start()

        btn_send = make_btn(btn_row, "Confirmar y Enviar Entrega", command=_enviar, tipo="primary", height=34)
        btn_send.pack(side="right", fill="x", expand=True, padx=(4, 0))

        btn_cancel = make_btn(btn_row, "Cancelar", command=diag.destroy, tipo="flat", width=90, height=34)
        btn_cancel.pack(side="left", padx=(0, 4))

    def _render_modal_texto(self, parent, data: dict, top_win):
        t = tema_actual()
        clear_frame(parent)

        card = make_card(parent, fg_color=t["card"], corner_radius=8, border_color=t["border"])
        card.pack(fill="both", expand=True, padx=4, pady=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=16)

        lbl = make_label(inner, data.get("texto", ""), tipo="blanco", wrap=580)
        lbl.pack(anchor="w")

        # Links si existen
        links = data.get("links", [])
        if links:
            lbl_lnk_h = make_label(inner, "ENLACES CLICABLES", tipo="seccion")
            lbl_lnk_h.pack(anchor="w", pady=(12, 6))

            for lk in links:
                btn_lnk = make_btn(
                    inner, f"🔗 {lk['texto']}",
                    command=lambda u=lk['url']: webbrowser.open(u),
                    tipo="flat", height=28, anchor="w"
                )
                btn_lnk.pack(fill="x", pady=2)

        bot = ctk.CTkFrame(top_win, fg_color="transparent")
        bot.pack(fill="x", padx=16, pady=(0, 12))
        btn_close = make_btn(bot, "Cerrar", command=top_win.destroy, tipo="primary", height=34)
        btn_close.pack(fill="x")

    def _render_modal_archivo(self, parent, item: dict, top_win):
        t = tema_actual()
        clear_frame(parent)

        card = make_card(parent, fg_color=t["card"], corner_radius=8, border_color=t["border"])
        card.pack(fill="both", expand=True, padx=4, pady=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=16)

        lbl = make_label(inner, f"📎 Archivo: {item.get('titulo')}\n\nPuedes visualizarlo directamente o guardarlo en tu computadora.", tipo="blanco", wrap=580)
        lbl.pack(anchor="w", pady=(0, 14))

        url = item.get("url", "")
        if url.lower().endswith('.pdf') or 'pdf' in item.get('titulo', '').lower():
            btn_pdf = make_btn(
                inner, "📄 Ver PDF en visor",
                command=lambda: self._visualizar_pdf(url, item.get('titulo')),
                tipo="primary", height=38
            )
            btn_pdf.pack(fill="x", pady=4)

        btn_dl = make_btn(
            inner, "📥 Guardar en mi computadora",
            command=lambda: self._descargar_archivo(url),
            tipo="flat", height=38
        )
        btn_dl.pack(fill="x", pady=4)

        bot = ctk.CTkFrame(top_win, fg_color="transparent")
        bot.pack(fill="x", padx=16, pady=(0, 12))
        btn_close = make_btn(bot, "Cerrar", command=top_win.destroy, tipo="flat", height=34)
        btn_close.pack(fill="x")

    def _resolver_url_descarga(self, url: str) -> str:
        """Resuelve la URL real de descarga en caso de que sea una página intermedia o de previsualización."""
        if not url:
            return url
        # Si es prg_archivo.cgi?wAccion=ver_archivo -> cambiar a wAccion=descargar
        if "prg_archivo.cgi" in url and "wAccion=ver_archivo" in url:
            return url.replace("wAccion=ver_archivo", "wAccion=descargar")
        return url

    def _visualizar_pdf(self, url: str, nombre_doc: str = "documento"):
        """Descarga el PDF con la sesión autenticada y lo abre con el visor del sistema."""
        try:
            url_dl = self._resolver_url_descarga(url)
            r = self.sess.get(url_dl, stream=True, timeout=25)
            
            # Sanitizar nombre
            safe_name = "".join(c for c in nombre_doc if c.isalnum() or c in (' ', '_', '-', '.')).strip()
            if not safe_name.lower().endswith('.pdf'):
                safe_name += ".pdf"

            temp_dir = tempfile.gettempdir()
            target_path = os.path.join(temp_dir, safe_name)

            with open(target_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Verificar si el archivo es un PDF válido
            with open(target_path, "rb") as f_check:
                header = f_check.read(10)
                if not header.startswith(b'%PDF'):
                    # Si no es PDF nativo, intentar abrir como URL en el navegador
                    webbrowser.open(url_dl)
                    return

            # Abrir con visor del sistema
            os.startfile(target_path)
        except Exception as e:
            try:
                webbrowser.open(url)
            except Exception:
                messagebox.showerror("Error al abrir PDF", f"No se pudo abrir el visor de PDF:\n{e}")

    def _descargar_archivo(self, url: str, nombre_default: str = ""):
        """Descarga el archivo autenticado preservando el nombre y extensión real con verificación de contenido."""
        try:
            url_dl = self._resolver_url_descarga(url)
            r = self.sess.get(url_dl, stream=True, timeout=25)
            
            # Verificar si se recibió una página HTML de error en lugar de un archivo
            ct = r.headers.get("Content-Type", "").lower()
            if "text/html" in ct and not any(url_dl.lower().endswith(ext) for ext in ('.htm', '.html')):
                # Leer primeros bytes para comprobar si es HTML de error
                primer_bloque = r.raw.read(1024) if hasattr(r, 'raw') else b""
                if b"<html" in primer_bloque.lower() or b"<!doctype" in primer_bloque.lower() or b"error" in primer_bloque.lower():
                    messagebox.showwarning("Archivo no disponible", "El archivo solicitado no está disponible en el servidor del campus o hubo un error al procesarlo.")
                    return

            cd = r.headers.get("Content-Disposition", "")
            fname = ""
            if "filename=" in cd:
                m_f = re.findall(r'filename=["\']?([^"\';]+)["\']?', cd)
                if m_f:
                    fname = m_f[0]
            if not fname:
                fname = nombre_default or "archivo_descargado"
                if "." not in fname:
                    if "pdf" in ct: fname += ".pdf"
                    elif "zip" in ct: fname += ".zip"
                    elif "word" in ct or "docx" in ct: fname += ".docx"
                    elif "image/jpeg" in ct: fname += ".jpg"
                    elif "image/png" in ct: fname += ".png"

            # Sanitizar
            fname = "".join(c for c in fname if c.isalnum() or c in (' ', '_', '-', '.')).strip()

            path = filedialog.asksaveasfilename(
                initialfile=fname,
                title="Guardar archivo adjunto"
            )
            if path:
                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                messagebox.showinfo("Descarga Completa", f"El archivo fue guardado con éxito en:\n{path}")
        except Exception as e:
            err_msg = str(e)
            if "inestable" in err_msg or "conexión" in err_msg:
                messagebox.showerror("Error de Conexión", err_msg)
            else:
                messagebox.showerror("Error de Descarga", f"No se pudo descargar el archivo:\n{e}")

    # ── MENSAJES ──────────────────────────────────────────────
    def _load_mensajes(self, bandeja: str = None):
        if bandeja:
            self._current_bandeja = bandeja
        clear_frame(self.page_mensajes)
        lbl_cargando = make_label(self.page_mensajes, f"⏳ Cargando mensajes ({self._current_bandeja})...", tipo="subtitulo")
        lbl_cargando.pack(pady=20)

        def run():
            try:
                msgs = msg_mod.get_mensajes(self.sess, self.curso["id"], bandeja=self._current_bandeja)
                if getattr(self, "_destroyed", False):
                    return
                self.after(0, self._show_mensajes, msgs)
            except Exception as e:
                if getattr(self, "_destroyed", False):
                    return
                self.after(0, self._show_error, self.page_mensajes, str(e))

        threading.Thread(target=run, daemon=True).start()

    def _show_mensajes(self, msgs):
        if getattr(self, "_destroyed", False) or not self.winfo_exists():
            return
        t = tema_actual()
        clear_frame(self.page_mensajes)
        self._selected_trash_ids.clear()
        self._trash_chk_widgets = []

        # Barra superior con Sub-bandejas y botón de Redactar
        top_bar = ctk.CTkFrame(self.page_mensajes, fg_color="transparent")
        top_bar.pack(fill="x", padx=4, pady=(4, 8))

        # Selector de sub-bandejas: Recibidos, Enviados, Papelera
        tabs_sub = ctk.CTkFrame(top_bar, fg_color="transparent")
        tabs_sub.pack(side="left")

        sub_bandejas = [
            ("📥 Recibidos", "Inbox"),
            ("📤 Enviados", "Outbox"),
            ("🗑 Papelera", "Trash")
        ]
        for label, b_key in sub_bandejas:
            is_active = (self._current_bandeja == b_key)
            btn_b = make_btn(
                tabs_sub, label,
                command=lambda k=b_key: self._load_mensajes(bandeja=k),
                tipo="primary" if is_active else "flat",
                width=110, height=30
            )
            btn_b.pack(side="left", padx=(0, 6))

        btn_redactar = make_btn(
            top_bar, "✉ Redactar mensaje",
            command=self._abrir_modal_redactar,
            tipo="primary", width=150, height=30
        )
        btn_redactar.pack(side="right")

        # Barra de acciones de papelera si estamos en Trash
        if self._current_bandeja == "Trash":
            trash_bar = ctk.CTkFrame(self.page_mensajes, fg_color=t["card"], corner_radius=8, border_color=t["border"])
            trash_bar.pack(fill="x", padx=4, pady=(2, 10))
            trash_inner = ctk.CTkFrame(trash_bar, fg_color="transparent")
            trash_inner.pack(fill="x", padx=10, pady=8)

            chk_all_var = ctk.BooleanVar(value=False)

            def _toggle_all():
                val = chk_all_var.get()
                if val:
                    for m in msgs:
                        if m.get("id"):
                            self._selected_trash_ids.add(str(m["id"]))
                else:
                    self._selected_trash_ids.clear()
                for chk, mid in self._trash_chk_widgets:
                    if val:
                        chk.select()
                    else:
                        chk.deselect()

            chk_all = ctk.CTkCheckBox(
                trash_inner, text="Seleccionar todos",
                variable=chk_all_var, command=_toggle_all,
                font=ctk.CTkFont(family="Segoe UI", size=12)
            )
            chk_all.pack(side="left", padx=(0, 14))

            btn_rest = make_btn(
                trash_inner, "↩ Restaurar e-mails",
                command=lambda: self._accion_papelera("restaurar"),
                tipo="primary", width=135, height=28
            )
            btn_rest.pack(side="left", padx=4)

            btn_elim_perm = make_btn(
                trash_inner, "🗑 Eliminar permanentemente",
                command=lambda: self._accion_papelera("eliminar"),
                tipo="danger", width=175, height=28
            )
            btn_elim_perm.pack(side="left", padx=4)

            btn_vaciar = make_btn(
                trash_inner, "🧹 Vaciar la papelera",
                command=lambda: self._accion_papelera("vaciar"),
                tipo="flat", width=135, height=28
            )
            btn_vaciar.pack(side="right")

        titulos_bandeja = {
            "Inbox": "BANDEJA DE ENTRADA",
            "Outbox": "MENSAJES ENVIADOS",
            "Trash": "PAPELERA DE RECICLAJE"
        }
        nom_b = titulos_bandeja.get(self._current_bandeja, "MENSAJES")
        lbl_hdr = make_label(self.page_mensajes, f"{nom_b} — {len(msgs)} MENSAJES", tipo="seccion")
        lbl_hdr.pack(anchor="w", padx=6, pady=(4, 6))

        if not msgs:
            lbl = make_label(self.page_mensajes, f"ℹ No hay mensajes en {nom_b.lower()}.", tipo="subtitulo")
            lbl.pack(pady=20, padx=10)
            return

        for m in msgs:
            card = make_card(
                self.page_mensajes,
                fg_color=t["card"],
                corner_radius=8,
                border_color=t["border"]
            )
            card.pack(fill="x", pady=4, padx=2)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=10)

            # Checkbox si es papelera
            if self._current_bandeja == "Trash":
                mid = str(m.get("id", ""))
                chk_v = ctk.BooleanVar(value=False)
                def _on_chk_toggle(msg_id=mid, var=chk_v):
                    if var.get():
                        self._selected_trash_ids.add(msg_id)
                    else:
                        self._selected_trash_ids.discard(msg_id)
                chk_item = ctk.CTkCheckBox(inner, text="", variable=chk_v, width=24, command=_on_chk_toggle)
                chk_item.pack(side="left", padx=(0, 10))
                self._trash_chk_widgets.append((chk_item, mid))

            asunto = m.get("asunto", "Sin asunto")
            remitente = m.get("remitente", "")
            fecha = m.get("fecha", "")

            # Fila de contenido
            left = ctk.CTkFrame(inner, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True)

            lbl_asunto = make_label(left, f"✉  {asunto}", tipo="blanco", wrap=480)
            lbl_asunto.pack(anchor="w")

            sub_row = ctk.CTkFrame(left, fg_color="transparent")
            sub_row.pack(fill="x", pady=(4, 0))

            lbl_pref = "Para: " if self._current_bandeja == "Outbox" else "De: "
            if remitente:
                lbl_rem = make_label(sub_row, f"{lbl_pref}{remitente}", tipo="subtitulo")
                lbl_rem.pack(side="left")

            if fecha:
                lbl_f = make_label(sub_row, f"📅 {fecha}", tipo="subtitulo")
                lbl_f.pack(side="right")

            # Botón Leer
            btn_leer = make_btn(
                inner, "Leer →",
                command=lambda msg=m: self._abrir_popup_mensaje(msg),
                tipo="primary", width=80, height=30
            )
            btn_leer.pack(side="right", padx=(10, 0))

    def _accion_papelera(self, accion: str):
        ids = list(self._selected_trash_ids)
        if accion in ("restaurar", "eliminar") and not ids:
            messagebox.showwarning("Atención", "Debes seleccionar al menos un mensaje de la papelera.")
            return

        if accion == "vaciar":
            if not messagebox.askyesno("Vaciar la papelera", "¿Estás seguro de que deseas vaciar completamente la papelera? Esta acción no se puede deshacer."):
                return
            def run_v():
                ok, res = msg_mod.vaciar_papelera(self.sess, str(self.curso["id"]))
                self.after(0, lambda: self._on_papelera_done(ok, res))
            threading.Thread(target=run_v, daemon=True).start()
        elif accion == "eliminar":
            if not messagebox.askyesno("Confirmar Eliminación", f"¿Estás seguro de que deseas eliminar permanentemente {len(ids)} mensaje(s) seleccionado(s)?"):
                return
            def run_e():
                ok, res = msg_mod.eliminar_permanente_papelera(self.sess, str(self.curso["id"]), ids)
                self.after(0, lambda: self._on_papelera_done(ok, res))
            threading.Thread(target=run_e, daemon=True).start()
        elif accion == "restaurar":
            def run_r():
                ok, res = msg_mod.restaurar_mensajes_papelera(self.sess, str(self.curso["id"]), ids)
                self.after(0, lambda: self._on_papelera_done(ok, res))
            threading.Thread(target=run_r, daemon=True).start()

    def _on_papelera_done(self, ok: bool, res: str):
        if ok:
            messagebox.showinfo("Éxito", res)
            self._load_mensajes(bandeja="Trash")
        else:
            messagebox.showerror("Error", res)

    def _abrir_popup_mensaje(self, m: dict):
        """Abre un modal con el contenido completo del mensaje."""
        t = tema_actual()
        top = ctk.CTkToplevel(self)
        top.title(f"Mensaje: {m.get('asunto')}")
        top.geometry("680x560")
        top.transient(self)
        top.grab_set()

        hdr = ctk.CTkFrame(top, fg_color=t["sidebar"], corner_radius=0)
        hdr.pack(fill="x")

        lbl_t = make_label(hdr, m.get('asunto', 'Mensaje'), tipo="titulo_sm", wrap=620)
        lbl_t.pack(padx=20, pady=(14, 2), anchor="w")

        lbl_s = make_label(hdr, f"De: {m.get('remitente')}  |  Fecha: {m.get('fecha')}", tipo="subtitulo")
        lbl_s.pack(padx=20, pady=(0, 4), anchor="w")

        # Barra de botones de acción
        actions_bar = ctk.CTkFrame(top, fg_color=t["card"], corner_radius=0)
        actions_bar.pack(fill="x", padx=0, pady=(0, 6))

        content = ctk.CTkScrollableFrame(top, fg_color=t["bg"])
        content.pack(fill="both", expand=True, padx=16, pady=6)

        lbl_carg = make_label(content, "⏳ Cargando contenido del mensaje...", tipo="subtitulo")
        lbl_carg.pack(pady=30)

        def run():
            detalle = msg_mod.get_detalle_mensaje(self.sess, m.get("link", m.get("id", "")), self.curso["id"])
            self.after(0, self._render_modal_mensaje, content, detalle, top, actions_bar, m)

        threading.Thread(target=run, daemon=True).start()

    def _render_modal_mensaje(self, parent, detalle: dict, top_win, actions_bar, m: dict):
        t = tema_actual()
        clear_frame(parent)
        clear_frame(actions_bar)

        # Botones de acción 100% operativos
        btn_reply = make_btn(
            actions_bar, "↩ Responder",
            command=lambda: self._abrir_modal_responder(detalle),
            tipo="primary", height=28, width=95
        )
        btn_reply.pack(side="left", padx=(16, 6), pady=4)

        btn_fwd = make_btn(
            actions_bar, "↪ Reenviar",
            command=lambda: self._abrir_modal_reenviar(detalle),
            tipo="flat", height=28, width=90
        )
        btn_fwd.pack(side="left", padx=6, pady=4)

        btn_del = make_btn(
            actions_bar, "🗑 Eliminar",
            command=lambda: self._confirmar_eliminar_mensaje(detalle, top_win),
            tipo="danger", height=28, width=85
        )
        btn_del.pack(side="left", padx=6, pady=4)

        # Encabezado con datos del destinatario
        para_txt = detalle.get("para") or getattr(self.sess, "nombre", "") or getattr(self.sess, "usuario", "Estudiante")
        if para_txt:
            card_para = make_card(parent, fg_color=t["item_bg"], corner_radius=6, border_color=t["border"])
            card_para.pack(fill="x", pady=(0, 6))
            inner_p = ctk.CTkFrame(card_para, fg_color="transparent")
            inner_p.pack(fill="x", padx=12, pady=6)
            lbl_p = make_label(inner_p, f"👤 Para: {para_txt}", tipo="subtitulo")
            lbl_p.pack(side="left")

        card = make_card(parent, fg_color=t["card"], corner_radius=8, border_color=t["border"])
        card.pack(fill="both", expand=True, padx=2, pady=4)

        # TextBox con selección de texto habilitada
        txt_body = ctk.CTkTextbox(
            card,
            fg_color="transparent",
            text_color=t["text"],
            wrap="word",
            activate_scrollbars=True,
            border_width=0,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        txt_body.insert("1.0", detalle.get("cuerpo", "(Sin contenido)"))
        txt_body.configure(state="disabled")
        txt_body.pack(fill="both", expand=True, padx=14, pady=14)

        # Botón de copiar texto
        btn_copy_body = make_btn(
            card, "📋 Copiar texto",
            command=lambda: self._copiar_al_portapapeles(detalle.get("cuerpo", "")),
            tipo="flat", width=100, height=24
        )
        btn_copy_body.pack(anchor="e", padx=14, pady=(0, 8))

        # Adjuntos
        adjuntos = detalle.get("adjuntos", [])
        if adjuntos:
            sep = make_separator(card)
            sep.pack(fill="x", padx=14, pady=6)

            lbl_adj_h = make_label(card, "ARCHIVOS ADJUNTOS", tipo="seccion")
            lbl_adj_h.pack(padx=14, pady=(4, 6), anchor="w")

            for adj in adjuntos:
                btn_d = make_btn(
                    card, f"📥 {adj['nombre']}",
                    command=lambda u=adj['url'], nom=adj['nombre']: self._descargar_archivo(u, nom),
                    tipo="primary", height=32
                )
                btn_d.pack(padx=14, pady=4, fill="x")

        bot = ctk.CTkFrame(top_win, fg_color="transparent")
        bot.pack(fill="x", padx=16, pady=(0, 10))
        btn_close = make_btn(bot, "Cerrar", command=top_win.destroy, tipo="primary", height=34)
        btn_close.pack(fill="x")

    def _abrir_modal_responder(self, detalle: dict):
        t = tema_actual()
        win = ctk.CTkToplevel(self)
        win.title("Responder Mensaje")
        win.geometry("580x480")
        win.transient(self)
        win.grab_set()

        hdr = ctk.CTkFrame(win, fg_color=t["sidebar"], corner_radius=0)
        hdr.pack(fill="x")
        make_label(hdr, "↩ Responder Mensaje", tipo="titulo_sm").pack(padx=16, pady=(12, 2), anchor="w")
        dest_txt = detalle.get("remitente", "Remitente")
        dest_id = detalle.get("destinatario_id") or ""
        lbl_sub_dest = f"Para: {dest_txt} ({dest_id})" if dest_id else f"Para: {dest_txt}"
        make_label(hdr, lbl_sub_dest, tipo="subtitulo").pack(padx=16, pady=(0, 10), anchor="w")

        body_f = ctk.CTkFrame(win, fg_color="transparent")
        body_f.pack(fill="both", expand=True, padx=16, pady=10)

        make_label(body_f, "Asunto:", tipo="seccion").pack(anchor="w", pady=(0, 2))
        orig_asunto = detalle.get("asunto", "")
        def_asunto = orig_asunto if orig_asunto.upper().startswith("RE:") else f"RE: {orig_asunto}"
        ent_asunto = ctk.CTkEntry(body_f, height=34, fg_color=t["item_bg"])
        ent_asunto.insert(0, def_asunto)
        ent_asunto.pack(fill="x", pady=(0, 10))

        make_label(body_f, "Mensaje de respuesta:", tipo="seccion").pack(anchor="w", pady=(0, 2))
        txt_cuerpo = ctk.CTkTextbox(body_f, fg_color=t["item_bg"], wrap="word")
        txt_cuerpo.pack(fill="both", expand=True, pady=(0, 10))
        txt_cuerpo.focus()

        lbl_estado_envio = make_label(body_f, "", tipo="subtitulo")
        lbl_estado_envio.pack(anchor="w", pady=(0, 6))

        btn_row = ctk.CTkFrame(body_f, fg_color="transparent")
        btn_row.pack(fill="x")

        def _do_send():
            asunto = ent_asunto.get().strip()
            cuerpo = txt_cuerpo.get("1.0", "end-1c").strip()
            if not asunto:
                messagebox.showwarning("Atención", "Por favor ingresa un asunto.")
                return
            if not cuerpo:
                messagebox.showwarning("Atención", "Por favor escribe un mensaje de respuesta.")
                return

            target_id = dest_id or detalle.get("remitente", "")
            btn_enviar.configure(state="disabled", text="⏳ Enviando...")
            lbl_estado_envio.configure(text="⏳ Enviando respuesta al campus virtual...")

            def send_task():
                ok, msg_res = msg_mod.responder_mensaje(
                    self.sess,
                    str(self.curso["id"]),
                    str(detalle.get("id", "")),
                    target_id,
                    asunto,
                    cuerpo
                )
                def on_done():
                    if ok:
                        messagebox.showinfo("Éxito", "¡Respuesta enviada con éxito al campus virtual!")
                        win.destroy()
                    else:
                        btn_enviar.configure(state="normal", text="Enviar Respuesta")
                        lbl_estado_envio.configure(text=f"❌ {msg_res}")
                        messagebox.showerror("Error al Enviar", msg_res)

                self.after(0, on_done)

            threading.Thread(target=send_task, daemon=True).start()

        btn_cancel = make_btn(btn_row, "Cancelar", command=win.destroy, tipo="flat", height=32, width=90)
        btn_cancel.pack(side="left")

        btn_enviar = make_btn(btn_row, "Enviar Respuesta", command=_do_send, tipo="primary", height=32, width=130)
        btn_enviar.pack(side="right")

    def _abrir_modal_reenviar(self, detalle: dict):
        t = tema_actual()
        win = ctk.CTkToplevel(self)
        win.title("Reenviar Mensaje")
        win.geometry("580x520")
        win.transient(self)
        win.grab_set()

        hdr = ctk.CTkFrame(win, fg_color=t["sidebar"], corner_radius=0)
        hdr.pack(fill="x")
        make_label(hdr, "↪ Reenviar Mensaje", tipo="titulo_sm").pack(padx=16, pady=(12, 2), anchor="w")
        make_label(hdr, f"Mensaje original: {detalle.get('asunto', '')}", tipo="subtitulo").pack(padx=16, pady=(0, 10), anchor="w")

        body_f = ctk.CTkFrame(win, fg_color="transparent")
        body_f.pack(fill="both", expand=True, padx=16, pady=10)

        make_label(body_f, "Destinatario (DNI o nombre de usuario):", tipo="seccion").pack(anchor="w", pady=(0, 2))
        ent_dest = ctk.CTkEntry(body_f, height=34, fg_color=t["item_bg"], placeholder_text="Ej: 46174575 o usuario")
        ent_dest.pack(fill="x", pady=(0, 10))

        make_label(body_f, "Asunto:", tipo="seccion").pack(anchor="w", pady=(0, 2))
        orig_asunto = detalle.get("asunto", "")
        def_asunto = orig_asunto if orig_asunto.upper().startswith("RV:") else f"RV: {orig_asunto}"
        ent_asunto = ctk.CTkEntry(body_f, height=34, fg_color=t["item_bg"])
        ent_asunto.insert(0, def_asunto)
        ent_asunto.pack(fill="x", pady=(0, 10))

        make_label(body_f, "Nota adicional (opcional):", tipo="seccion").pack(anchor="w", pady=(0, 2))
        txt_nota = ctk.CTkTextbox(body_f, fg_color=t["item_bg"], wrap="word", height=100)
        txt_nota.pack(fill="both", expand=True, pady=(0, 10))

        lbl_estado_reenvio = make_label(body_f, "", tipo="subtitulo")
        lbl_estado_reenvio.pack(anchor="w", pady=(0, 6))

        btn_row = ctk.CTkFrame(body_f, fg_color="transparent")
        btn_row.pack(fill="x")

        def _do_forward():
            dest = ent_dest.get().strip()
            asunto = ent_asunto.get().strip()
            nota = txt_nota.get("1.0", "end-1c").strip()
            if not dest:
                messagebox.showwarning("Atención", "Por favor ingresa el destinatario para reenviar.")
                return
            if not asunto:
                messagebox.showwarning("Atención", "Por favor ingresa un asunto.")
                return

            btn_fwd_send.configure(state="disabled", text="⏳ Reenviando...")
            lbl_estado_reenvio.configure(text="⏳ Reenviando mensaje al campus virtual...")

            def fwd_task():
                ok, msg_res = msg_mod.reenviar_mensaje(
                    self.sess,
                    str(self.curso["id"]),
                    str(detalle.get("id", "")),
                    dest,
                    asunto,
                    nota
                )
                def on_done():
                    if ok:
                        messagebox.showinfo("Éxito", "¡Mensaje reenviado con éxito al campus virtual!")
                        win.destroy()
                    else:
                        btn_fwd_send.configure(state="normal", text="Reenviar Mensaje")
                        lbl_estado_reenvio.configure(text=f"❌ {msg_res}")
                        messagebox.showerror("Error al Reenviar", msg_res)

                self.after(0, on_done)

            threading.Thread(target=fwd_task, daemon=True).start()

        btn_cancel = make_btn(btn_row, "Cancelar", command=win.destroy, tipo="flat", height=32, width=90)
        btn_cancel.pack(side="left")

        btn_fwd_send = make_btn(btn_row, "Reenviar Mensaje", command=_do_forward, tipo="primary", height=32, width=130)
        btn_fwd_send.pack(side="right")

    def _confirmar_eliminar_mensaje(self, detalle: dict, top_win):
        if messagebox.askyesno("Confirmar Eliminación", "¿Estás seguro de que deseas eliminar este mensaje?"):
            def del_task():
                ok, msg_res = msg_mod.eliminar_mensaje(
                    self.sess,
                    str(self.curso["id"]),
                    str(detalle.get("id", "")),
                    detalle.get("csrf_token", "")
                )
                def on_done():
                    if ok:
                        messagebox.showinfo("Mensaje Eliminado", "El mensaje fue movido a la papelera.")
                        top_win.destroy()
                        self._load_mensajes()
                    else:
                        messagebox.showerror("Error al Eliminar", msg_res)
                self.after(0, on_done)

            threading.Thread(target=del_task, daemon=True).start()

    def _abrir_modal_selector_contactos(self, seleccionados_actuales: list[dict], on_done):
        """
        Abre el modal de selección de destinatarios para 'Para...'.
        Permite buscar en tiempo real, filtrar por alumnos y docentes, seleccionar múltiples contactos y confirmar con Aceptar.
        """
        t = tema_actual()
        top = ctk.CTkToplevel(self)
        top.title("Seleccionar Destinatarios")
        top.geometry("540x560")
        top.transient(self)
        top.grab_set()

        hdr = ctk.CTkFrame(top, fg_color=t["sidebar"], corner_radius=0)
        hdr.pack(fill="x")
        make_label(hdr, "👥 Destinatarios — Para...", tipo="titulo_sm").pack(padx=16, pady=(12, 2), anchor="w")
        make_label(hdr, "Selecciona los alumnos o docentes a quienes enviar el mensaje", tipo="subtitulo").pack(padx=16, pady=(0, 10), anchor="w")

        body = ctk.CTkFrame(top, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=10)

        # Buscador en tiempo real
        search_f = ctk.CTkFrame(body, fg_color="transparent")
        search_f.pack(fill="x", pady=(0, 8))
        ent_buscar = ctk.CTkEntry(search_f, height=32, placeholder_text="🔍 Buscar por nombre o apellido...")
        ent_buscar.pack(fill="x")

        # Accesos rápidos / filtros: Todos, Alumnos, Docentes
        filtro_row = ctk.CTkFrame(body, fg_color="transparent")
        filtro_row.pack(fill="x", pady=(0, 8))
        make_label(filtro_row, "Accesos rápidos:", tipo="seccion").pack(side="left", padx=(0, 8))

        filtro_actual = ["todos"]

        btn_todos = make_btn(filtro_row, "Todos", tipo="primary", width=60, height=24)
        btn_todos.pack(side="left", padx=2)
        btn_alumnos = make_btn(filtro_row, "Alumnos", tipo="flat", width=75, height=24)
        btn_alumnos.pack(side="left", padx=2)
        btn_docentes = make_btn(filtro_row, "Docentes", tipo="flat", width=75, height=24)
        btn_docentes.pack(side="left", padx=2)

        scroll_dest = ctk.CTkScrollableFrame(body, fg_color=t["item_bg"], corner_radius=6)
        scroll_dest.pack(fill="both", expand=True, pady=(0, 10))

        # Mapa de IDs seleccionados
        selected_map = {str(p["id"]): p for p in seleccionados_actuales if p.get("id")}
        todos_contactos = []

        def _render_lista():
            clear_frame(scroll_dest)
            filtro_t = filtro_actual[0]
            query = ent_buscar.get().strip().lower()

            encontrados = 0
            for c in todos_contactos:
                rol_c = c.get("rol", "").lower()
                if filtro_t == "alumnos" and "alumno" not in rol_c:
                    continue
                if filtro_t == "docentes" and "docente" not in rol_c:
                    continue
                if query and query not in c.get("nombre", "").lower() and query not in c.get("email", "").lower():
                    continue

                encontrados += 1
                cid = str(c.get("id", ""))
                row = ctk.CTkFrame(scroll_dest, fg_color=t["card"], corner_radius=6)
                row.pack(fill="x", pady=2, padx=4)

                inner_r = ctk.CTkFrame(row, fg_color="transparent")
                inner_r.pack(fill="x", padx=10, pady=6)

                chk_var = ctk.BooleanVar(value=(cid in selected_map))

                def _toggle(contact=c, var=chk_var):
                    c_id = str(contact.get("id", ""))
                    if var.get():
                        selected_map[c_id] = contact
                    else:
                        selected_map.pop(c_id, None)

                icon = "👨‍🏫" if "docente" in rol_c else "👤"
                chk = ctk.CTkCheckBox(
                    inner_r, text=f"{icon}  {c.get('nombre', '')}  ({c.get('rol', '')})",
                    variable=chk_var, command=_toggle,
                    font=ctk.CTkFont(family="Segoe UI", size=12)
                )
                chk.pack(side="left", fill="x", expand=True)

            if encontrados == 0:
                make_label(scroll_dest, "ℹ No se encontraron contactos coincidentes.", tipo="subtitulo").pack(pady=15)

        def _set_filtro(f):
            filtro_actual[0] = f
            btn_todos.configure(tipo="primary" if f == "todos" else "flat")
            btn_alumnos.configure(tipo="primary" if f == "alumnos" else "flat")
            btn_docentes.configure(tipo="primary" if f == "docentes" else "flat")
            _render_lista()

        btn_todos.configure(command=lambda: _set_filtro("todos"))
        btn_alumnos.configure(command=lambda: _set_filtro("alumnos"))
        btn_docentes.configure(command=lambda: _set_filtro("docentes"))
        ent_buscar.bind("<KeyRelease>", lambda e: _render_lista())

        lbl_carg = make_label(scroll_dest, "⏳ Cargando contactos del aula...", tipo="subtitulo")
        lbl_carg.pack(pady=20)

        def _load():
            nonlocal todos_contactos
            try:
                data = cont_mod.get_contactos(self.sess, self.curso["id"], obtener_detalles_completos=False)
                docs = data.get("docentes", [])
                alums = data.get("alumnos", [])
                todos_contactos = docs + alums
                self.after(0, _render_lista)
            except Exception as e:
                self.after(0, lambda: make_label(scroll_dest, f"Error: {e}", tipo="subtitulo").pack(pady=10))

        threading.Thread(target=_load, daemon=True).start()

        bot_f = ctk.CTkFrame(top, fg_color="transparent")
        bot_f.pack(fill="x", padx=16, pady=(0, 12))

        def _on_accept():
            on_done(list(selected_map.values()))
            top.destroy()

        btn_cancel = make_btn(bot_f, "Cancelar", command=top.destroy, tipo="flat", height=32, width=90)
        btn_cancel.pack(side="left")

        btn_ok = make_btn(bot_f, "Aceptar", command=_on_accept, tipo="primary", height=32, width=110)
        btn_ok.pack(side="right")

    def _abrir_modal_redactar(self):
        t = tema_actual()
        win = ctk.CTkToplevel(self)
        win.title("Enviar mensaje")
        win.geometry("620x620")
        win.transient(self)
        win.grab_set()

        hdr = ctk.CTkFrame(win, fg_color=t["sidebar"], corner_radius=0)
        hdr.pack(fill="x")
        make_label(hdr, "✉ Enviar mensaje", tipo="titulo_sm").pack(padx=16, pady=(12, 2), anchor="w")
        make_label(hdr, f"Materia: {self.curso.get('nombre', '')}", tipo="subtitulo").pack(padx=16, pady=(0, 10), anchor="w")

        body_f = ctk.CTkFrame(win, fg_color="transparent")
        body_f.pack(fill="both", expand=True, padx=16, pady=10)

        # Fila Para...
        para_hdr_f = ctk.CTkFrame(body_f, fg_color="transparent")
        para_hdr_f.pack(fill="x", pady=(0, 2))
        make_label(para_hdr_f, "Para:", tipo="seccion").pack(side="left")

        destinatarios_seleccionados = []  # list of dicts: [{"id":..., "nombre":...}]

        def _actualizar_para(seleccionados):
            nonlocal destinatarios_seleccionados
            destinatarios_seleccionados = seleccionados
            nombres = [p.get("nombre", "") for p in seleccionados]
            texto_mostrar = "; ".join(nombres) if nombres else ""
            ent_dest.configure(state="normal")
            ent_dest.delete(0, "end")
            ent_dest.insert(0, texto_mostrar)
            ent_dest.configure(state="readonly")

        btn_para = make_btn(
            para_hdr_f, "Para...",
            command=lambda: self._abrir_modal_selector_contactos(destinatarios_seleccionados, _actualizar_para),
            tipo="primary", width=85, height=24
        )
        btn_para.pack(side="right")

        ent_dest = ctk.CTkEntry(
            body_f, height=34, fg_color=t["item_bg"],
            placeholder_text="Presiona el botón 'Para...' para seleccionar alumnos o docentes"
        )
        ent_dest.configure(state="readonly")
        ent_dest.pack(fill="x", pady=(0, 10))

        # Asunto
        make_label(body_f, "Asunto:", tipo="seccion").pack(anchor="w", pady=(0, 2))
        ent_asunto = ctk.CTkEntry(body_f, height=34, fg_color=t["item_bg"], placeholder_text="Asunto del mensaje...")
        ent_asunto.pack(fill="x", pady=(0, 10))

        # Mensaje
        make_label(body_f, "Mensaje:", tipo="seccion").pack(anchor="w", pady=(0, 2))
        txt_cuerpo = ctk.CTkTextbox(body_f, fg_color=t["item_bg"], wrap="word", height=130)
        txt_cuerpo.pack(fill="both", expand=True, pady=(0, 10))
        ent_asunto.bind("<Return>", lambda _: txt_cuerpo.focus())
        txt_cuerpo.focus()

        # Adjuntos (Permitido hasta 30 MB)
        adjunto_path = [None]

        adj_frame = ctk.CTkFrame(body_f, fg_color=t["card"], corner_radius=6, border_width=1, border_color=t["border"])
        adj_frame.pack(fill="x", pady=(0, 10))

        adj_inner = ctk.CTkFrame(adj_frame, fg_color="transparent")
        adj_inner.pack(fill="x", padx=10, pady=8)

        lbl_adj_title = make_label(adj_inner, "Adjuntos (Permitido hasta 30 megabytes):", tipo="seccion")
        lbl_adj_title.pack(anchor="w")

        adj_info_row = ctk.CTkFrame(adj_inner, fg_color="transparent")
        adj_info_row.pack(fill="x", pady=(4, 0))

        lbl_adj_status = make_label(adj_info_row, "Sin archivo adjunto", tipo="subtitulo")
        lbl_adj_status.pack(side="left", padx=(0, 10))

        btn_quitar_adj = make_btn(adj_info_row, "❌ Quitar", command=None, tipo="danger", width=70, height=24)

        def _quitar_archivo():
            adjunto_path[0] = None
            lbl_adj_status.configure(text="Sin archivo adjunto")
            btn_quitar_adj.pack_forget()

        btn_quitar_adj.configure(command=_quitar_archivo)

        def _seleccionar_archivo():
            ruta = filedialog.askopenfilename(title="Seleccionar archivo adjunto")
            if ruta:
                if not os.path.exists(ruta):
                    return
                tamanio = os.path.getsize(ruta)
                if tamanio > 30 * 1024 * 1024:
                    messagebox.showerror("Archivo demasiado grande", "El archivo supera el tamaño máximo permitido de 30 megabytes.")
                    return
                adjunto_path[0] = ruta
                if tamanio < 1024:
                    sz_str = f"{tamanio} B"
                elif tamanio < 1024 * 1024:
                    sz_str = f"{tamanio / 1024:.1f} KB"
                else:
                    sz_str = f"{tamanio / (1024 * 1024):.1f} MB"
                nombre_f = os.path.basename(ruta)
                lbl_adj_status.configure(text=f"📎 {nombre_f} ({sz_str})")
                btn_quitar_adj.pack(side="left")

        btn_sel_adj = make_btn(
            adj_info_row, "📁 Buscar archivo...",
            command=_seleccionar_archivo,
            tipo="primary", width=125, height=24
        )
        btn_sel_adj.pack(side="right")

        lbl_estado_envio = make_label(body_f, "", tipo="subtitulo")
        lbl_estado_envio.pack(anchor="w", pady=(0, 6))

        btn_row = ctk.CTkFrame(body_f, fg_color="transparent")
        btn_row.pack(fill="x")

        def _do_send_new():
            if not destinatarios_seleccionados:
                messagebox.showwarning("Atención", "Por favor selecciona al menos un destinatario usando el botón 'Para...'.")
                return
            asunto = ent_asunto.get().strip()
            cuerpo = txt_cuerpo.get("1.0", "end-1c").strip()
            if not asunto:
                messagebox.showwarning("Atención", "Por favor ingresa un asunto.")
                return
            if not cuerpo:
                messagebox.showwarning("Atención", "Por favor escribe el mensaje.")
                return

            dest_ids = [str(p["id"]) for p in destinatarios_seleccionados if p.get("id")]
            btn_enviar.configure(state="disabled", text="⏳ Enviando...")
            lbl_estado_envio.configure(text="⏳ Enviando mensaje al campus virtual...")

            def send_task():
                ok, msg_res = msg_mod.enviar_nuevo_mensaje(
                    self.sess,
                    str(self.curso["id"]),
                    dest_ids,
                    asunto,
                    cuerpo,
                    archivo_adjunto=adjunto_path[0]
                )
                def on_done():
                    if ok:
                        messagebox.showinfo("Mensaje Enviado", msg_res)
                        win.destroy()
                        self._load_mensajes()
                    else:
                        btn_enviar.configure(state="normal", text="Enviar Mensaje")
                        lbl_estado_envio.configure(text=f"❌ {msg_res}")
                        messagebox.showerror("Error al Enviar", msg_res)

                self.after(0, on_done)

            threading.Thread(target=send_task, daemon=True).start()

        btn_cancel = make_btn(btn_row, "Cancelar", command=win.destroy, tipo="flat", height=32, width=90)
        btn_cancel.pack(side="left")

        btn_enviar = make_btn(btn_row, "Enviar Mensaje", command=_do_send_new, tipo="primary", height=32, width=130)
        btn_enviar.pack(side="right")

    # ── CALIFICACIONES ────────────────────────────────────────
    def _load_calificaciones(self):
        clear_frame(self.page_calificaciones)
        lbl_cargando = make_label(self.page_calificaciones, "⏳ Cargando calificaciones y evaluaciones...", tipo="subtitulo")
        lbl_cargando.pack(pady=20)

        def run():
            try:
                cals = cal_mod.get_calificaciones(self.sess, self.curso["id"])
                if getattr(self, "_destroyed", False):
                    return
                self.after(0, self._show_calificaciones, cals)
            except Exception as e:
                if getattr(self, "_destroyed", False):
                    return
                self.after(0, self._show_error, self.page_calificaciones, str(e))

        threading.Thread(target=run, daemon=True).start()

    def _show_calificaciones(self, cals):
        if getattr(self, "_destroyed", False) or not self.winfo_exists():
            return
        t = tema_actual()
        clear_frame(self.page_calificaciones)

        if not cals:
            lbl = make_label(self.page_calificaciones, "ℹ No hay calificaciones registradas aún en esta materia.", tipo="subtitulo")
            lbl.pack(pady=20, padx=10)
            return

        lbl_hdr = make_label(self.page_calificaciones, f"CALIFICACIONES — {len(cals)} REGISTROS", tipo="seccion")
        lbl_hdr.pack(anchor="w", padx=4, pady=(4, 10))

        for c in cals:
            row = make_card(self.page_calificaciones, fg_color=t["item_bg"], corner_radius=8, border_color=t["border"])
            row.pack(fill="x", pady=4, padx=2)

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=12)

            left = ctk.CTkFrame(inner, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True)

            nombre = c.get("nombre", "Sin nombre")
            lbl_nom = make_label(left, nombre, tipo="blanco", wrap=480)
            lbl_nom.pack(anchor="w")

            meta = []
            if c.get("categoria") and c.get("categoria") != "General":
                cat_clean = c['categoria'].splitlines()[-1].strip() if '\n' in c['categoria'] else c['categoria']
                meta.append(f"📁 {cat_clean}")
            if c.get("docente"):
                meta.append(f"👨‍🏫 {c['docente']}")
            if c.get("fecha"):
                meta.append(f"📅 {c['fecha']}")
            if c.get("peso"):
                meta.append(f"Ponderación: {c['peso']}")

            if meta:
                lbl_meta = make_label(left, "   •   ".join(meta), tipo="subtitulo")
                lbl_meta.pack(anchor="w", pady=(3, 0))

            if c.get("observaciones"):
                lbl_obs = make_label(left, f"💬 {c['observaciones']}", tipo="verde", wrap=460)
                lbl_obs.pack(anchor="w", pady=(3, 0))

            nota = c.get("nota", "—")
            badge_color = t["success"] if nota not in ("—", "Desaprobado", "Insuficiente") else t["card"]
            badge = make_badge(inner, f"Nota: {nota}", bg_color=badge_color, text_color="#ffffff")
            badge.pack(side="right", padx=10)

    # ── CONTACTOS ─────────────────────────────────────────────
    def _load_contactos(self, forzar_recarga: bool = False):
        clear_frame(self.page_contactos)
        lbl_cargando = make_label(self.page_contactos, "⏳ Extrayendo datos de docentes, compañeros y perfiles...", tipo="subtitulo")
        lbl_cargando.pack(pady=20)

        def run():
            try:
                data = cont_mod.get_contactos(self.sess, self.curso["id"], obtener_detalles_completos=True, forzar_recarga=forzar_recarga)
                if getattr(self, "_destroyed", False):
                    return
                self.after(0, self._show_contactos, data)
            except Exception as e:
                if getattr(self, "_destroyed", False):
                    return
                self.after(0, self._show_error, self.page_contactos, str(e))

        threading.Thread(target=run, daemon=True).start()

    def _show_contactos(self, data):
        if getattr(self, "_destroyed", False) or not self.winfo_exists():
            return
        t = tema_actual()
        clear_frame(self.page_contactos)
        self._contactos_data = data

        docentes = data.get("docentes", [])
        alumnos = data.get("alumnos", [])

        # Barra superior con botones de Acción
        top_bar = ctk.CTkFrame(self.page_contactos, fg_color="transparent")
        top_bar.pack(fill="x", padx=4, pady=(0, 10))

        totales = len(docentes) + len(alumnos)
        lbl_tot = make_label(top_bar, f"CONTACTOS DEL AULA — {totales} REGISTROS", tipo="seccion")
        lbl_tot.pack(side="left")

        btn_csv = make_btn(
            top_bar, "📥 Exportar a CSV",
            command=self._exportar_csv_contactos,
            tipo="primary", width=140, height=30
        )
        btn_csv.pack(side="right")

        btn_recargar = make_btn(
            top_bar, "🔄 Actualizar",
            command=lambda: self._load_contactos(forzar_recarga=True),
            tipo="flat", width=110, height=30
        )
        btn_recargar.pack(side="right", padx=(0, 8))

        # Scroll de contactos
        scroll_c = ctk.CTkScrollableFrame(self.page_contactos, fg_color="transparent")
        scroll_c.pack(fill="both", expand=True)

        if not docentes and not alumnos:
            lbl = make_label(scroll_c, "ℹ No se encontraron contactos registrados en este curso.", tipo="subtitulo")
            lbl.pack(pady=20, padx=10)
            return

        if docentes:
            lbl_doc = make_label(scroll_c, f"DOCENTES ({len(docentes)})", tipo="seccion")
            lbl_doc.pack(anchor="w", padx=4, pady=(4, 6))

            for p in docentes:
                self._render_persona(scroll_c, p, "👨‍🏫", es_docente=True)

        if alumnos:
            lbl_alu = make_label(scroll_c, f"COMPAÑEROS ({len(alumnos)})", tipo="seccion")
            lbl_alu.pack(anchor="w", padx=4, pady=(10, 6))

            for p in alumnos:
                self._render_persona(scroll_c, p, "👤", es_docente=False)

    def _cargar_avatar_async(self, label_widget, url: str, size: tuple = (34, 34), fallback_text: str = "👤"):
        if not url or not url.startswith("http"):
            return

        def _fetch():
            try:
                import hashlib
                from config import CONFIG_DIR
                avatars_dir = os.path.join(CONFIG_DIR, "avatars")
                os.makedirs(avatars_dir, exist_ok=True)

                clean_url = url.split("?")[0]
                url_hi = url.replace("thumb_40x45.jpg", "thumb_80_90.jpg")
                h = hashlib.md5(clean_url.encode("utf-8")).hexdigest()
                cached_file = os.path.join(avatars_dir, f"{h}_{size[0]}.png")

                if not os.path.exists(cached_file):
                    r = None
                    if "thumb_80_90.jpg" in url_hi:
                        try:
                            r = self.sess.get(url_hi, timeout=8)
                        except Exception:
                            r = None
                    if not r or r.status_code != 200:
                        r = self.sess.get(url, timeout=8)

                    if r and r.status_code == 200 and len(r.content) > 100:
                        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
                        img = img.resize(size, Image.LANCZOS)
                        img.save(cached_file, "PNG")

                if os.path.exists(cached_file):
                    def _apply():
                        try:
                            pil_img = Image.open(cached_file).convert("RGBA")
                            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
                            label_widget.configure(image=ctk_img, text="")
                            label_widget.image = ctk_img
                        except Exception:
                            pass

                    self.after(0, _apply)
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def _render_persona(self, parent, p, icon, es_docente=False):
        t = tema_actual()
        card = make_card(parent, fg_color=t["item_bg"], corner_radius=8, border_color=t["border"])
        card.pack(fill="x", pady=2, padx=2)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)

        # Avatar o Ícono circular
        avatar_box = ctk.CTkFrame(inner, width=40, height=40, fg_color=t["card"], corner_radius=20)
        avatar_box.pack(side="left", padx=(0, 12))
        avatar_box.pack_propagate(False)

        lbl_av = make_label(avatar_box, icon, tipo="blanco", anchor="center")
        lbl_av.pack(expand=True)

        foto_url = p.get("foto_url")
        if foto_url:
            self._cargar_avatar_async(lbl_av, foto_url, size=(40, 40), fallback_text=icon)

        # Centro / Izquierda: Información de la persona
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        # Fila 1: Nombre con rol/badge al lado
        top_name_row = ctk.CTkFrame(left, fg_color="transparent")
        top_name_row.pack(fill="x", anchor="w")

        nombre = p.get("nombre", "—")
        lbl_nom = make_label(top_name_row, nombre, tipo="blanco", wrap=420)
        lbl_nom.pack(side="left", anchor="w")

        rol_text = "Docente" if es_docente else "Compañero"
        badge_bg = t.get("accent", "#2563eb") if es_docente else t.get("card", "#1b2a47")
        badge_fg = "#ffffff" if es_docente else t.get("muted", "#94a3b8")
        badge_rol = make_badge(top_name_row, rol_text, bg_color=badge_bg, text_color=badge_fg)
        badge_rol.pack(side="left", padx=(8, 0))

        # Fila 2: Datos de contacto (Email, Teléfono, Ubicación)
        info_row = ctk.CTkFrame(left, fg_color="transparent")
        info_row.pack(fill="x", anchor="w", pady=(3, 0))

        email = p.get("email")
        tel = p.get("telefono")
        lugar = p.get("lugar")

        tiene_datos = False
        if email and email != "No especificado":
            tiene_datos = True
            lbl_em = make_label(info_row, f"✉ {email}", tipo="subtitulo")
            lbl_em.pack(side="left", padx=(0, 6))

            btn_copy = make_btn(
                info_row, "📋",
                command=lambda em=email: self._copiar_al_portapapeles(em),
                tipo="flat", width=22, height=18
            )
            btn_copy.pack(side="left", padx=(0, 8))

        if tel and tel != "No especificado":
            tiene_datos = True
            lbl_tel = make_label(info_row, f"📞 {tel}", tipo="subtitulo")
            lbl_tel.pack(side="left", padx=(0, 8))

        if lugar and lugar != "No especificado":
            tiene_datos = True
            lbl_lug = make_label(info_row, f"📍 {lugar}", tipo="subtitulo")
            lbl_lug.pack(side="left", padx=(0, 8))

        if not tiene_datos:
            lbl_nodata = make_label(info_row, "🔒 Perfil privado / Datos disponibles en ficha", tipo="subtitulo")
            lbl_nodata.pack(side="left")

        # Derecha: Botón Ver Ficha Completa
        btn_ver = make_btn(
            inner, "Ver Ficha",
            command=lambda pers=p: self._abrir_popup_perfil(pers),
            tipo="flat", width=80, height=28
        )
        btn_ver.pack(side="right", padx=(6, 0))

    def _copiar_al_portapapeles(self, texto: str):
        try:
            self.clipboard_clear()
            self.clipboard_append(texto)
            messagebox.showinfo("Copiado", f"Copiado al portapapeles:\n{texto}")
        except Exception:
            pass

    def _abrir_popup_perfil(self, p: dict):
        """Muestra un modal con los detalles de perfil del contacto."""
        t = tema_actual()
        top = ctk.CTkToplevel(self)
        top.title(f"Ficha de Perfil — {p.get('nombre', '')}")
        top.geometry("480x520")
        top.transient(self)
        top.grab_set()

        hdr = ctk.CTkFrame(top, fg_color=t["sidebar"], corner_radius=0)
        hdr.pack(fill="x")

        hdr_row = ctk.CTkFrame(hdr, fg_color="transparent")
        hdr_row.pack(fill="x", padx=16, pady=12)

        # Avatar modal
        av_box_m = ctk.CTkFrame(hdr_row, width=50, height=50, fg_color=t["card"], corner_radius=25)
        av_box_m.pack(side="left", padx=(0, 12))
        av_box_m.pack_propagate(False)

        def_icon = "👨‍🏫" if "docente" in p.get("rol", "").lower() else "👤"
        lbl_av_m = make_label(av_box_m, def_icon, tipo="titulo", anchor="center")
        lbl_av_m.pack(expand=True)

        foto_url = p.get("foto_url")
        if foto_url:
            self._cargar_avatar_async(lbl_av_m, foto_url, size=(50, 50), fallback_text=def_icon)

        hdr_info = ctk.CTkFrame(hdr_row, fg_color="transparent")
        hdr_info.pack(side="left", fill="x", expand=True)

        lbl_t = make_label(hdr_info, p.get('nombre', ''), tipo="titulo_sm", wrap=360)
        lbl_t.pack(anchor="w")

        lbl_rol = make_label(hdr_info, f"Rol: {p.get('rol', 'Contacto')}", tipo="seccion")
        lbl_rol.pack(anchor="w", pady=(2, 0))

        content = ctk.CTkScrollableFrame(top, fg_color=t["bg"])
        content.pack(fill="both", expand=True, padx=16, pady=12)

        campos = [
            ("Correo Electrónico:", p.get("email") or "No especificado"),
            ("Teléfono / Móvil:", p.get("telefono") or "No especificado"),
            ("Localidad / Lugar:", p.get("lugar") or "No especificado"),
            ("Documento / DNI:", p.get("documento") or "No especificado"),
            ("Fecha de Nacimiento:", p.get("nacimiento") or "No especificado"),
            ("Género:", p.get("genero") or "No especificado"),
            ("Comentarios / Bio:", p.get("comentarios") or "Sin comentarios")
        ]

        for k, v in campos:
            card_f = make_card(content, fg_color=t["card"], corner_radius=6, border_color=t["border"])
            card_f.pack(fill="x", pady=3)
            
            box = ctk.CTkFrame(card_f, fg_color="transparent")
            box.pack(fill="x", padx=12, pady=8)
            
            lbl_k = make_label(box, k, tipo="seccion")
            lbl_k.pack(anchor="w")
            
            val_row = ctk.CTkFrame(box, fg_color="transparent")
            val_row.pack(fill="x", pady=(2, 0))

            lbl_v = make_label(val_row, v, tipo="blanco", wrap=380)
            lbl_v.pack(side="left")

            if "Correo" in k and v and v != "No especificado":
                btn_c = make_btn(
                    val_row, "📋 Copiar",
                    command=lambda em=v: self._copiar_al_portapapeles(em),
                    tipo="flat", width=65, height=22
                )
                btn_c.pack(side="right")

        bot = ctk.CTkFrame(top, fg_color="transparent")
        bot.pack(fill="x", padx=16, pady=(0, 14))
        btn_close = make_btn(bot, "Cerrar", command=top.destroy, tipo="primary", height=34)
        btn_close.pack(fill="x")

    def _exportar_csv_contactos(self):
        if not self._contactos_data:
            return
        nombre_sanitizado = "".join(c for c in self.curso.get("nombre", "materia") if c.isalnum() or c in (' ', '_', '-')).strip()
        default_file = f"contactos_{nombre_sanitizado}.csv"
        
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Archivos CSV", "*.csv")],
            initialfile=default_file,
            title="Guardar contactos extraídos"
        )
        if path:
            try:
                cont_mod.exportar_contactos_csv(self._contactos_data, path)
                messagebox.showinfo("Exportación Exitosa", f"Se exportaron los contactos correctamente en:\n{path}")
            except Exception as e:
                messagebox.showerror("Error al Exportar", f"No se pudo guardar el archivo CSV:\n{e}")

    # ── CHAT GENERAL DE LA MATERIA ────────────────────────────
    def _load_chat(self):
        clear_frame(self.page_chat)
        lbl_cargando = make_label(self.page_chat, "⏳ Cargando mensajes del chat del aula...", tipo="subtitulo")
        lbl_cargando.pack(pady=20)

        def run():
            try:
                mensajes = chat_mod.get_mensajes_chat(self.sess, self.curso["id"])
                if getattr(self, "_destroyed", False):
                    return
                self.after(0, self._show_chat, mensajes)
            except Exception as e:
                if getattr(self, "_destroyed", False):
                    return
                self.after(0, self._show_error, self.page_chat, str(e))

        threading.Thread(target=run, daemon=True).start()

    def _forward_chat_scroll(self, event):
        """Redirige el scroll de la rueda del ratón desde las burbujas al contenedor del chat."""
        try:
            delta = -1 * int(event.delta / 120) if event.delta else 1
            if hasattr(self, "chat_scroll") and self.chat_scroll:
                self.chat_scroll._parent_canvas.yview_scroll(delta, "units")
        except Exception:
            pass

    def _bind_scroll_recursive(self, widget):
        """Asocia recursivamente el evento de la rueda del ratón al contenedor de scroll."""
        try:
            widget.bind("<MouseWheel>", self._forward_chat_scroll)
            if hasattr(widget, "_textbox"):
                widget._textbox.bind("<MouseWheel>", self._forward_chat_scroll)
        except Exception:
            pass
        for child in widget.winfo_children():
            self._bind_scroll_recursive(child)

    def _show_chat(self, chat_data):
        if getattr(self, "_destroyed", False) or not self.winfo_exists():
            return
        t = tema_actual()
        clear_frame(self.page_chat)

        if isinstance(chat_data, dict):
            disponible = chat_data.get("disponible", True)
            mensajes = chat_data.get("mensajes", [])
            msg_error = chat_data.get("msg", "Chat no disponible para esta materia.")
        else:
            disponible = True
            mensajes = chat_data or []
            msg_error = ""

        if not disponible:
            card_err = make_card(self.page_chat, fg_color=t["card"], corner_radius=10, border_color=t["border"])
            card_err.pack(fill="both", expand=True, padx=4, pady=20)
            lbl_no = make_label(card_err, "💬 Chat no disponible para esta materia", tipo="titulo_sm", anchor="center")
            lbl_no.pack(pady=(40, 6))
            lbl_sub = make_label(card_err, "El docente o la institución no han habilitado una sala de chat en esta materia.", tipo="subtitulo", anchor="center")
            lbl_sub.pack(pady=(0, 40))
            return

        # Header con botón de recargar
        top_bar = ctk.CTkFrame(self.page_chat, fg_color="transparent")
        top_bar.pack(fill="x", padx=4, pady=(0, 10))

        lbl_hdr = make_label(top_bar, f"💬 CHAT GENERAL — {self.curso.get('nombre', 'Materia')}", tipo="seccion")
        lbl_hdr.pack(side="left")

        btn_refresh = make_btn(
            top_bar, "🔄 Actualizar",
            command=self._load_chat,
            tipo="flat", width=100, height=30
        )
        btn_refresh.pack(side="right")

        # Scroll de mensajes de chat
        chat_scroll = ctk.CTkScrollableFrame(self.page_chat, fg_color=t["card"], corner_radius=10)
        chat_scroll.pack(fill="both", expand=True, padx=2, pady=(0, 10))
        self.chat_scroll = chat_scroll

        if not mensajes:
            lbl_empty = make_label(chat_scroll, "ℹ No hay mensajes registrados en el chat de esta materia todavía.\n¡Sé el primero en saludar!", tipo="subtitulo")
            lbl_empty.pack(pady=30, padx=10)
        else:
            for msg in mensajes:
                es_mio = msg.get("es_propio", False)
                bubble_color = t["accent"] if es_mio else t["item_bg"]
                border_col = t["accent_hover"] if es_mio else t["border"]
                align = "e" if es_mio else "w"
                pad_sides = (60, 6) if es_mio else (6, 60)

                bubble = ctk.CTkFrame(chat_scroll, fg_color=bubble_color, corner_radius=10, border_color=border_col, border_width=1)
                bubble.pack(fill="x", pady=4, padx=pad_sides, anchor=align)

                b_inner = ctk.CTkFrame(bubble, fg_color="transparent")
                b_inner.pack(fill="x", padx=12, pady=8)

                hdr_row = ctk.CTkFrame(b_inner, fg_color="transparent")
                hdr_row.pack(fill="x", pady=(0, 4))

                nombre_rem = "Tú" if es_mio else msg.get("remitente", msg.get("autor", "Usuario"))
                lbl_autor = make_label(hdr_row, f"👤 {nombre_rem}", tipo="verde" if not es_mio else "blanco")
                if es_mio:
                    lbl_autor.configure(text_color=t["btn_text"])
                lbl_autor.pack(side="left")

                if msg.get("fecha"):
                    lbl_fecha = make_label(hdr_row, msg.get("fecha"), tipo="subtitulo")
                    if es_mio:
                        lbl_fecha.configure(text_color=t["btn_text"])
                    lbl_fecha.pack(side="right")

                lbl_texto = ctk.CTkTextbox(
                    b_inner,
                    fg_color="transparent",
                    text_color=t["btn_text"] if es_mio else t["text"],
                    wrap="word",
                    height=30,
                    activate_scrollbars=False,
                    border_width=0
                )
                lbl_texto.insert("1.0", msg.get("texto", ""))
                lbl_texto.configure(state="disabled")
                lbl_texto.pack(fill="x", anchor="w")

                # Bindeo recursivo de rueda del ratón para permitir scroll sobre toda la burbuja
                self._bind_scroll_recursive(bubble)

        # Barra de envío de mensaje abajo
        input_frame = ctk.CTkFrame(self.page_chat, fg_color="transparent")
        input_frame.pack(fill="x", padx=2, pady=(0, 4))

        txt_input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Escribe un mensaje para el chat del aula...",
            height=38,
            fg_color=t["item_bg"],
            text_color=t["text"],
            border_color=t["border"]
        )
        txt_input.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def _enviar_chat():
            texto = txt_input.get().strip()
            if not texto:
                return

            btn_send.configure(state="disabled", text="⏳ Enviando...")

            def run():
                ok_send, msg_res = chat_mod.enviar_mensaje_chat(self.sess, self.curso["id"], texto)

                def after_send():
                    btn_send.configure(state="normal", text="Enviar 💬")
                    if ok_send:
                        txt_input.delete(0, "end")
                        self._load_chat()
                    else:
                        messagebox.showerror("Error al Enviar", f"No se pudo enviar el mensaje al chat:\n{msg_res}")

                self.after(0, after_send)

            threading.Thread(target=run, daemon=True).start()

        txt_input.bind("<Return>", lambda e: _enviar_chat())

        btn_send = make_btn(
            input_frame, "Enviar 💬",
            command=_enviar_chat,
            tipo="primary", width=100, height=38
        )
        btn_send.pack(side="right")

    def _show_error(self, parent, msg):
        if getattr(self, "_destroyed", False) or not self.winfo_exists():
            return
        try:
            if parent and parent.winfo_exists():
                clear_frame(parent)
                lbl = make_label(parent, f"❌ Error al cargar datos: {msg}", tipo="error", wrap=500)
                lbl.pack(pady=20, padx=10)
        except Exception:
            pass

