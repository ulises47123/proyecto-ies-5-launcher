"""
ui/tutorial.py — Módulo de bienvenida y tutorial guiado para usuarios nuevos (Onboarding).
Presenta una serie de 4 diapositivas concisas con controles de navegación (Anterior, Siguiente, Omitir, Comenzar).
Totalmente adaptable a temas oscuros y claros con CustomTkinter.
"""
import customtkinter as ctk
import tkinter as tk
from ui.widgets import make_label, make_btn, make_card, make_separator
from ui.theme import tema_actual, registrar_listener_tema, desregistrar_listener_tema
from config import marcar_tutorial_visto

PASOS_TUTORIAL = [
    {
        "icono": "🧭",
        "titulo": "Bienvenido al Campus Virtual",
        "subtitulo": "Paso 1 de 4: Vista Principal y Navegación",
        "items": [
            ("📌", "Barra Lateral", "Accedé rápidamente a tus asignaturas, avisos, asistente IA, estadísticas y configuración."),
            ("🎨", "Personalización", "Elegí entre 8 temas visuales de alto contraste diseñados para facilitar la lectura."),
            ("🔄", "Sincronización", "Podes forzar una actualización manual de tus datos con un solo clic en 'Actualizar'.")
        ]
    },
    {
        "icono": "📚",
        "titulo": "Mis Materias y Actividades",
        "subtitulo": "Paso 2 de 4: Seguimiento Académico Integral",
        "items": [
            ("📖", "Programa y Clases", "Navegá por unidades interactivas tipo acordeón con acceso a archivos y textos."),
            ("🟢", "Control de Entregas", "Identificá al instante tareas Entregadas (Verde), Pendientes (Naranja) y Cerradas (Rojo)."),
            ("✉️", "Mensajería y Notas", "Leé correos internos del aula, revisá tus calificaciones y contactá a tus docentes.")
        ]
    },
    {
        "icono": "⚡",
        "titulo": "Actualización y Notificaciones",
        "subtitulo": "Paso 3 de 4: Novedades en Segundo Plano",
        "items": [
            ("🕒", "Frecuencia Automática", "El programa consulta el campus periódicamente en segundo plano (por defecto cada 10 min)."),
            ("🔔", "Notificaciones Nativas", "Recibí alertas en tu escritorio ante nuevas consignas o mensajes importantes."),
            ("🗔", "Bandeja del Sistema", "Minimizá la aplicación a la bandeja sin interrumpir el monitoreo ni cerrarla.")
        ]
    },
    {
        "icono": "🤖",
        "titulo": "Asistente IA Inteligente",
        "subtitulo": "Paso 4 de 4: Tu Tutor y Asistente Virtual",
        "items": [
            ("💬", "Consultas Locales", "Preguntale sobre tus materias, avance, docentes a cargo y tareas pendientes."),
            ("🔒", "100% Privado y Rápido", "En modo local funciona al instante procesando tus datos cacheados sin enviar nada a internet."),
            ("🔑", "IA Avanzada Opcional", "Podés conectar tu clave de Gemini o OpenAI en Ajustes para resúmenes y explicaciones complejas.")
        ]
    }
]


class TutorialWindow(ctk.CTkToplevel):
    """Ventana modal interactiva de bienvenida y tutorial paso a paso."""

    def __init__(self, parent, on_finish=None):
        super().__init__(parent)
        self.parent = parent
        self.on_finish = on_finish
        self.paso_actual = 0

        self.title("Bienvenida — Campus Virtual IES N°5")
        self.geometry("640x520")
        self.resizable(False, False)

        # Centrar ventana con respecto al padre
        self._centrar_en_padre()

        # Hacerla modal
        self.transient(parent)
        self.grab_set()

        t = tema_actual()
        self.configure(fg_color=t["bg"])

        self._build_ui()
        registrar_listener_tema(self._on_tema_update)

    def _centrar_en_padre(self):
        self.update_idletasks()
        try:
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            w = 640
            h = 520
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def _on_tema_update(self, t):
        self.configure(fg_color=t["bg"])
        self._render_paso()

    def destroy(self):
        desregistrar_listener_tema(self._on_tema_update)
        marcar_tutorial_visto(True)
        if self.on_finish:
            try:
                self.on_finish()
            except Exception:
                pass
        super().destroy()

    def _build_ui(self):
        t = tema_actual()

        # Contenedor principal
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=24, pady=20)

        # Card de contenido
        self.card = make_card(self.main_frame, fg_color=t["card"], corner_radius=14, border_color=t["border"])
        self.card.pack(fill="both", expand=True, pady=(0, 16))

        self.card_content = ctk.CTkFrame(self.card, fg_color="transparent")
        self.card_content.pack(fill="both", expand=True, padx=24, pady=20)

        # Barra inferior de navegación
        self.nav_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.nav_frame.pack(fill="x")

        self.btn_skip = make_btn(
            self.nav_frame, "Omitir",
            command=self._finalizar,
            tipo="flat", width=90, height=36
        )
        self.btn_skip.pack(side="left")

        # Indicador de puntos (dots)
        self.dots_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        self.dots_frame.pack(side="left", expand=True)

        self.btn_prev = make_btn(
            self.nav_frame, "← Anterior",
            command=self._paso_anterior,
            tipo="flat", width=90, height=36
        )
        self.btn_prev.pack(side="right", padx=(8, 0))

        self.btn_next = make_btn(
            self.nav_frame, "Siguiente →",
            command=self._paso_siguiente,
            tipo="primary", width=110, height=36
        )
        self.btn_next.pack(side="right")

        self._render_paso()

    def _render_paso(self):
        t = tema_actual()
        paso = PASOS_TUTORIAL[self.paso_actual]

        # Limpiar card
        for w in self.card_content.winfo_children():
            w.destroy()

        # Header del paso
        hdr = ctk.CTkFrame(self.card_content, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 12))

        lbl_ico = make_label(hdr, paso["icono"], tipo="titulo")
        lbl_ico.configure(font=ctk.CTkFont(size=32))
        lbl_ico.pack(side="left", padx=(0, 12))

        title_box = ctk.CTkFrame(hdr, fg_color="transparent")
        title_box.pack(side="left", fill="x", expand=True)

        lbl_tit = make_label(title_box, paso["titulo"], tipo="titulo", wrap=440)
        lbl_tit.pack(anchor="w")

        lbl_sub = make_label(title_box, paso["subtitulo"], tipo="subtitulo")
        lbl_sub.pack(anchor="w")

        sep = make_separator(self.card_content)
        sep.pack(fill="x", pady=(0, 14))

        # Lista de ítems del paso
        for ico_item, tit_item, desc_item in paso["items"]:
            item_frame = ctk.CTkFrame(self.card_content, fg_color=t["item_bg"], corner_radius=10, border_width=1, border_color=t["border"])
            item_frame.pack(fill="x", pady=5)

            row = ctk.CTkFrame(item_frame, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=10)

            lbl_it_ico = make_label(row, ico_item, tipo="titulo")
            lbl_it_ico.pack(side="left", padx=(0, 10))

            text_box = ctk.CTkFrame(row, fg_color="transparent")
            text_box.pack(side="left", fill="x", expand=True)

            lbl_it_tit = make_label(text_box, tit_item, tipo="verde")
            lbl_it_tit.pack(anchor="w")

            lbl_it_desc = make_label(text_box, desc_item, tipo="normal", wrap=430)
            lbl_it_desc.pack(anchor="w", pady=(2, 0))

        # Actualizar dots
        for w in self.dots_frame.winfo_children():
            w.destroy()

        for i in range(len(PASOS_TUTORIAL)):
            dot_color = t["accent"] if i == self.paso_actual else t["border"]
            dot = ctk.CTkFrame(self.dots_frame, width=12, height=12, corner_radius=6, fg_color=dot_color)
            dot.pack(side="left", padx=4)

        # Actualizar botones
        if self.paso_actual == 0:
            self.btn_prev.configure(state="disabled")
        else:
            self.btn_prev.configure(state="normal")

        if self.paso_actual == len(PASOS_TUTORIAL) - 1:
            self.btn_next.configure(
                text="¡Comenzar! ✨",
                fg_color=t["success"],
                hover_color=t["accent_hover"],
                text_color=t["btn_text"]
            )
        else:
            self.btn_next.configure(
                text="Siguiente →",
                fg_color=t["accent"],
                hover_color=t["accent_hover"],
                text_color=t["btn_text"]
            )

    def _paso_siguiente(self):
        if self.paso_actual < len(PASOS_TUTORIAL) - 1:
            self.paso_actual += 1
            self._render_paso()
        else:
            self._finalizar()

    def _paso_anterior(self):
        if self.paso_actual > 0:
            self.paso_actual -= 1
            self._render_paso()

    def _finalizar(self):
        self.destroy()
