"""
ui/theme.py — Gestión del tema visual, colores de alto contraste y selector de temas.
Adaptado 100% para Windows con CustomTkinter y Tkinter.
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import colorchooser
from config import cargar_tema, guardar_tema, DEFAULT_THEME, TEMAS_PREDEFINIDOS

_tema_actual: dict = {}
_listeners = []


def registrar_listener_tema(callback):
    """Registra una función que se llamará cada vez que cambie el tema."""
    if callback not in _listeners:
        _listeners.append(callback)


def desregistrar_listener_tema(callback):
    if callback in _listeners:
        _listeners.remove(callback)


def aplicar_tema(tema: dict | None = None):
    """Aplica el tema seleccionado y notifica a las vistas."""
    global _tema_actual
    if tema is None:
        tema = cargar_tema()
    _tema_actual = dict(tema)

    # Configurar modo de apariencia en CustomTkinter
    if _tema_actual.get("is_dark", True):
        ctk.set_appearance_mode("dark")
    else:
        ctk.set_appearance_mode("light")

    # Notificar a todos los suscriptores
    for cb in list(_listeners):
        try:
            cb(_tema_actual)
        except Exception:
            pass


def tema_actual() -> dict:
    global _tema_actual
    if not _tema_actual:
        _tema_actual = cargar_tema()
    return _tema_actual


def cambiar_tema_predefinido(nombre_o_id: str):
    """Cambia a uno de los temas predefinidos."""
    for nombre, t in TEMAS_PREDEFINIDOS.items():
        if nombre == nombre_o_id or t.get("id") == nombre_o_id:
            guardar_tema(t)
            aplicar_tema(t)
            return t
    return tema_actual()


def abrir_dialogo_tema(parent, on_tema_cambiado=None):
    """Abre una ventana modal moderna para seleccionar temas predefinidos o personalizar colores."""
    t = dict(tema_actual())
    
    top = ctk.CTkToplevel(parent)
    top.title("🎨 Personalizar Tema y Colores")
    top.geometry("520x680")
    top.minsize(480, 600)
    top.transient(parent)
    top.grab_set()
    
    # Encabezado
    hdr = ctk.CTkFrame(top, corner_radius=0, fg_color=t["sidebar"])
    hdr.pack(fill="x", padx=0, pady=0)
    
    lbl_title = ctk.CTkLabel(
        hdr, text="🎨 Configuración de Apariencia y Contraste",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=t["text"]
    )
    lbl_title.pack(padx=20, pady=(16, 4), anchor="w")
    
    lbl_sub = ctk.CTkLabel(
        hdr, text="Elegí uno de los 5 temas optimizados para máxima legibilidad o ajustá los colores.",
        font=ctk.CTkFont(size=12),
        text_color=t["muted"],
        wraplength=460, justify="left"
    )
    lbl_sub.pack(padx=20, pady=(0, 16), anchor="w")
    
    # Scroll content
    scroll = ctk.CTkScrollableFrame(top, fg_color=t["bg"])
    scroll.pack(fill="both", expand=True, padx=16, pady=12)
    
    # Selector de temas predefinidos
    sec_predef = ctk.CTkFrame(scroll, fg_color=t["card"], corner_radius=10, border_width=1, border_color=t["border"])
    sec_predef.pack(fill="x", pady=(0, 12), padx=4)
    
    lbl_p = ctk.CTkLabel(
        sec_predef, text="TEMAS DISPONIBLES (5 TEMAS DE ALTO CONTRASTE)",
        font=ctk.CTkFont(size=11, weight="bold"),
        text_color=t["accent"]
    )
    lbl_p.pack(anchor="w", padx=16, pady=(14, 8))
    
    temas_nombres = list(TEMAS_PREDEFINIDOS.keys())
    
    # Determinar nombre actual
    nombre_actual = temas_nombres[0]
    for nom, t_item in TEMAS_PREDEFINIDOS.items():
        if t_item.get("id") == t.get("id") or t_item.get("bg") == t.get("bg"):
            nombre_actual = nom
            break
            
    combo_temas = ctk.CTkOptionMenu(
        sec_predef,
        values=temas_nombres,
        fg_color=t["accent"],
        button_color=t["accent_hover"],
        text_color=t["btn_text"],
        font=ctk.CTkFont(size=13, weight="bold"),
        height=36,
        dynamic_resizing=False
    )
    combo_temas.set(nombre_actual)
    combo_temas.pack(fill="x", padx=16, pady=(0, 14))
    
    def on_select_preset(choice):
        nuevo = TEMAS_PREDEFINIDOS[choice]
        guardar_tema(nuevo)
        aplicar_tema(nuevo)
        if on_tema_cambiado:
            try:
                on_tema_cambiado()
            except Exception:
                pass
        try:
            top.destroy()
        except Exception:
            pass
        
    combo_temas.configure(command=on_select_preset)
    
    # Editor detallado de colores
    sec_colores = ctk.CTkFrame(scroll, fg_color=t["card"], corner_radius=10, border_width=1, border_color=t["border"])
    sec_colores.pack(fill="x", pady=4, padx=4)
    
    lbl_c = ctk.CTkLabel(
        sec_colores, text="AJUSTE INDIVIDUAL DE COLORES",
        font=ctk.CTkFont(size=11, weight="bold"),
        text_color=t["accent"]
    )
    lbl_c.pack(anchor="w", padx=16, pady=(14, 10))
    
    LABELS = {
        "bg":       "Fondo Principal de la Aplicación",
        "sidebar":  "Barra Lateral / Menú",
        "card":     "Tarjetas y Contenedores",
        "item_bg":  "Fondo de Ítems / Subsecciones",
        "accent":   "Color de Acento (Botones y Títulos)",
        "text":     "Texto Principal (Alto Contraste)",
        "muted":    "Texto Secundario / Metadatos",
        "border":   "Bordes y Separadores",
        "success":  "Color de Éxito / Progreso",
        "warning":  "Color de Advertencia"
    }
    
    entradas_colores = {}
    
    for key, label in LABELS.items():
        row = ctk.CTkFrame(sec_colores, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)
        
        lbl_k = ctk.CTkLabel(
            row, text=label,
            font=ctk.CTkFont(size=12),
            text_color=t["text"],
            anchor="w"
        )
        lbl_k.pack(side="left", fill="x", expand=True)
        
        # Muestra de color actual
        color_val = t.get(key, "#ffffff")
        btn_pick = ctk.CTkButton(
            row, text=color_val,
            fg_color=color_val,
            hover_color=color_val,
            text_color="#ffffff" if key not in ("text", "bg", "light") else "#000000",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=85, height=28,
            corner_radius=6
        )
        
        def pick_color(k=key, b=btn_pick):
            actual = t.get(k, "#ffffff")
            res = colorchooser.askcolor(color=actual, title=f"Elegir color para {LABELS[k]}")
            if res and res[1]:
                hex_c = res[1]
                t[k] = hex_c
                b.configure(fg_color=hex_c, hover_color=hex_c, text=hex_c)
                
        btn_pick.configure(command=pick_color)
        btn_pick.pack(side="right")
        entradas_colores[key] = btn_pick
        
    # Botones inferiores
    bot = ctk.CTkFrame(top, corner_radius=0, fg_color=t["sidebar"])
    bot.pack(fill="x", padx=0, pady=0)
    
    def on_guardar_personalizado():
        guardar_tema(t)
        aplicar_tema(t)
        if on_tema_cambiado:
            on_tema_cambiado()
        top.destroy()
        
    def on_restaurar_defecto():
        guardar_tema(dict(DEFAULT_THEME))
        aplicar_tema(dict(DEFAULT_THEME))
        if on_tema_cambiado:
            on_tema_cambiado()
        top.destroy()
        
    btn_guardar = ctk.CTkButton(
        bot, text="Guardar Cambios",
        fg_color=t["accent"],
        hover_color=t["accent_hover"],
        text_color=t["btn_text"],
        font=ctk.CTkFont(size=13, weight="bold"),
        height=38,
        command=on_guardar_personalizado
    )
    btn_guardar.pack(side="right", padx=16, pady=12)
    
    btn_reset = ctk.CTkButton(
        bot, text="Restaurar Defecto",
        fg_color=t["card"],
        hover_color=t["border"],
        text_color=t["text"],
        font=ctk.CTkFont(size=12),
        height=38,
        command=on_restaurar_defecto
    )
    btn_reset.pack(side="left", padx=16, pady=12)
