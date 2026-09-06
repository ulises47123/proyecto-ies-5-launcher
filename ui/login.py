"""
ui/login.py — Pantalla de login con usuario/contraseña, auto-ingreso y selector de temas.
Adaptado 100% para Windows con CustomTkinter.
"""
import threading
import customtkinter as ctk
import tkinter as tk
from backend.session import CampusSession
from ui.widgets import make_label, make_btn, make_card, make_separator
from ui.theme import tema_actual, abrir_dialogo_tema, registrar_listener_tema, desregistrar_listener_tema
from config import cargar_creds, guardar_creds, borrar_creds, guardar_cookies_sesion, borrar_cookies_sesion


class LoginView(ctk.CTkFrame):
    """Vista de login. Llama a on_success(campus) al autenticar correctamente."""

    def __init__(self, parent, on_success):
        t = tema_actual()
        super().__init__(parent, fg_color=t["bg"])
        self.parent = parent
        self.on_success = on_success
        self._build()
        registrar_listener_tema(self._on_tema_update)

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

    def _build(self):
        t = tema_actual()

        # Contenedor central
        center_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_frame.pack(expand=True, padx=20, pady=20)

        card = make_card(center_frame, fg_color=t["card"], corner_radius=14, border_color=t["border"])
        card.pack(padx=10, pady=10)

        # Header del Card
        card_content = ctk.CTkFrame(card, fg_color="transparent")
        card_content.pack(padx=32, pady=28)

        # Logo institucional
        import os
        from PIL import Image
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Escudo-I.E.S.-N-5.png")
        if os.path.exists(icon_path):
            try:
                logo_img = ctk.CTkImage(light_image=Image.open(icon_path), dark_image=Image.open(icon_path), size=(56, 56))
                lbl_icon = ctk.CTkLabel(card_content, image=logo_img, text="")
                lbl_icon.pack(pady=(0, 8))
            except Exception:
                pass

        lbl_logo = make_label(card_content, "IES N°5 José E. Tello", tipo="titulo", anchor="center")
        lbl_logo.pack(fill="x", pady=(0, 2))

        lbl_sub = make_label(card_content, "Campus Virtual Oficial", tipo="subtitulo", anchor="center")
        lbl_sub.pack(fill="x", pady=(0, 4))

        lbl_desc = make_label(card_content, "Ingresá tus credenciales para acceder", tipo="blanco", anchor="center")
        lbl_desc.pack(fill="x", pady=(0, 16))

        sep = make_separator(card_content)
        sep.pack(fill="x", pady=(0, 16))

        # Campo Usuario
        lbl_u = make_label(card_content, "USUARIO / DNI", tipo="seccion")
        lbl_u.pack(anchor="w", pady=(0, 4))

        self.entry_user = ctk.CTkEntry(
            card_content,
            placeholder_text="Ingresá tu usuario o DNI",
            width=320,
            height=38,
            corner_radius=8,
            fg_color=t["input_bg"],
            border_color=t["border"],
            text_color=t["text"],
            placeholder_text_color=t["muted"],
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.entry_user.pack(pady=(0, 14))

        # Campo Contraseña
        lbl_p = make_label(card_content, "CONTRASEÑA", tipo="seccion")
        lbl_p.pack(anchor="w", pady=(0, 4))

        self.entry_pass = ctk.CTkEntry(
            card_content,
            placeholder_text="Ingresá tu contraseña",
            show="*",
            width=320,
            height=38,
            corner_radius=8,
            fg_color=t["input_bg"],
            border_color=t["border"],
            text_color=t["text"],
            placeholder_text_color=t["muted"],
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.entry_pass.pack(pady=(0, 10))

        # Opciones
        opts_frame = ctk.CTkFrame(card_content, fg_color="transparent")
        opts_frame.pack(fill="x", pady=(0, 14))

        self.chk_auto = ctk.CTkCheckBox(
            opts_frame,
            text="Recordar",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=t["text"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            border_color=t["border"]
        )
        self.chk_auto.pack(side="left")

        self.chk_show = ctk.CTkCheckBox(
            opts_frame,
            text="Ver contraseña",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=t["muted"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            border_color=t["border"],
            command=self._toggle_pass_visibility
        )
        self.chk_show.pack(side="right")

        # Mensaje de Error / Estado
        self.lbl_err = make_label(card_content, "", tipo="error", anchor="center", wrap=300)
        self.lbl_err.pack(fill="x", pady=(0, 10))

        # Botón Ingresar
        self.btn_login = make_btn(
            card_content, "Ingresar al Campus →",
            command=self._do_login,
            tipo="primary", width=320, height=42
        )
        self.btn_login.pack(pady=(4, 12))

        # Checkbox Tutorial para nuevos usuarios
        self.chk_tutorial = ctk.CTkCheckBox(
            card_content,
            text="Soy nuevo, mostrarme el tutorial",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=t["muted"],
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            border_color=t["border"]
        )
        self.chk_tutorial.pack(anchor="center", pady=(0, 4))

        # Enter key triggers
        self.entry_user.bind("<Return>", lambda _: self.entry_pass.focus())
        self.entry_pass.bind("<Return>", lambda _: self._do_login())

        # Pre-cargar credenciales si existen
        u, p = cargar_creds()
        if u:
            self.entry_user.insert(0, u)
            self.entry_pass.insert(0, p)
            self.chk_auto.select()

    def _toggle_pass_visibility(self):
        if self.chk_show.get() == 1:
            self.entry_pass.configure(show="")
        else:
            self.entry_pass.configure(show="*")

    def _do_login(self):
        u = self.entry_user.get().strip()
        p = self.entry_pass.get().strip()
        if not u or not p:
            self.lbl_err.configure(text="⚠ Por favor, completá usuario y contraseña.")
            return

        self.btn_login.configure(state="disabled", text="Verificando acceso...")
        self.lbl_err.configure(text="")
        auto = (self.chk_auto.get() == 1)
        solicitar_tutorial = (self.chk_tutorial.get() == 1)
        campus = CampusSession()

        def run():
            ok, msg = campus.login(u, p)
            self.after(0, self._on_result, ok, msg, campus, u, p, auto, solicitar_tutorial)

        threading.Thread(target=run, daemon=True).start()

    def _on_result(self, ok, msg, campus, u, p, auto, solicitar_tutorial=False):
        if ok:
            if auto:
                guardar_creds(u, p)
                guardar_cookies_sesion(campus.http.cookies)
            else:
                borrar_creds()
                borrar_cookies_sesion()
            # Extraer y guardar datos dinámicos del usuario autenticado
            from backend.user import get_current_user
            get_current_user(campus)
            self.on_success(campus, solicitar_tutorial)
        else:
            self.btn_login.configure(state="normal", text="Ingresar al Campus →")
            self.lbl_err.configure(text=f"❌ {msg}")
