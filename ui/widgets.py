"""
ui/widgets.py — Widgets reutilizables con CustomTkinter para Windows.
Diseñados con alto contraste, bordes claros y excelente legibilidad.
"""
import customtkinter as ctk
import tkinter as tk
from ui.theme import tema_actual


def make_label(parent, text, tipo="normal", wrap=0, anchor="w", **kwargs):
    """
    Crea un CTkLabel con tipografía y color de alto contraste según el tipo.
    Tipos: 'titulo', 'titulo_sm', 'subtitulo', 'seccion', 'verde', 'accent', 'warn', 'error', 'blanco', 'normal'
    """
    t = tema_actual()
    font_family = "Segoe UI"
    
    config = {
        "titulo":    {"size": 18, "weight": "bold",   "color": t["accent"]},
        "titulo_sm": {"size": 14, "weight": "bold",   "color": t["accent"]},
        "subtitulo": {"size": 12, "weight": "normal", "color": t["muted"]},
        "seccion":   {"size": 11, "weight": "bold",   "color": t["success"]},
        "verde":     {"size": 13, "weight": "bold",   "color": t["success"]},
        "accent":    {"size": 13, "weight": "bold",   "color": t["accent"]},
        "warn":      {"size": 12, "weight": "bold",   "color": t["warning"]},
        "error":     {"size": 12, "weight": "bold",   "color": t["accent"]},
        "blanco":    {"size": 13, "weight": "normal", "color": t["text"]},
        "normal":    {"size": 13, "weight": "normal", "color": t["text"]},
    }.get(tipo, {"size": 13, "weight": "normal", "color": t["text"]})
    
    font = ctk.CTkFont(family=font_family, size=config["size"], weight=config["weight"])
    lbl = ctk.CTkLabel(
        parent,
        text=text,
        font=font,
        text_color=config["color"],
        anchor=anchor,
        wraplength=wrap,
        justify="left" if anchor in ("w", "nw", "sw") else "center",
        **kwargs
    )
    return lbl


def make_btn(parent, text, command=None, tipo="primary", width=100, height=34, **kwargs):
    """
    Crea un botón estilizado con texto de alto contraste y esquinas redondeadas.
    Tipos: 'primary', 'nav', 'flat', 'danger', 'success'
    """
    t = tema_actual()
    
    if tipo == "primary":
        fg = t["accent"]
        hover = t["accent_hover"]
        tc = t["btn_text"]
        border_w = 0
        border_c = None
    elif tipo == "nav":
        fg = "transparent"
        hover = t["card"]
        tc = t["text"]
        border_w = 0
        border_c = None
    elif tipo == "flat":
        fg = t["item_bg"]
        hover = t["border"]
        tc = t["text"]
        border_w = 1
        border_c = t["border"]
    elif tipo == "danger":
        fg = "#ef4444"
        hover = "#dc2626"
        tc = "#ffffff"
        border_w = 0
        border_c = None
    elif tipo == "success":
        fg = t["success"]
        hover = t["accent_hover"]
        tc = "#ffffff"
        border_w = 0
        border_c = None
    else:
        fg = t["card"]
        hover = t["border"]
        tc = t["text"]
        border_w = 1
        border_c = t["border"]
        
    btn_args = {
        "master": parent,
        "text": text,
        "command": command,
        "fg_color": fg,
        "hover_color": hover,
        "text_color": tc,
        "font": ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        "corner_radius": 8,
        "border_width": border_w,
        "width": width,
        "height": height,
    }
    if border_c is not None:
        btn_args["border_color"] = border_c
    btn_args.update(kwargs)
    
    btn = ctk.CTkButton(**btn_args)
    return btn


def make_card(parent, fg_color=None, border_color=None, corner_radius=10, **kwargs):
    """Crea una tarjeta contenedora con borde y fondo contrastante."""
    t = tema_actual()
    return ctk.CTkFrame(
        parent,
        fg_color=fg_color or t["card"],
        border_color=border_color or t["border"],
        border_width=1,
        corner_radius=corner_radius,
        **kwargs
    )


def make_separator(parent, orientation="horizontal", **kwargs):
    """Crea un separador sutil y visible."""
    t = tema_actual()
    if orientation == "horizontal":
        return ctk.CTkFrame(parent, height=1, fg_color=t["border"], corner_radius=0, **kwargs)
    else:
        return ctk.CTkFrame(parent, width=1, fg_color=t["border"], corner_radius=0, **kwargs)


def make_badge(parent, text, bg_color=None, text_color="#ffffff", **kwargs):
    """Crea una etiqueta o insignia con fondo de color."""
    t = tema_actual()
    frame = ctk.CTkFrame(
        parent,
        fg_color=bg_color or t["accent"],
        corner_radius=12,
        height=22,
        **kwargs
    )
    lbl = ctk.CTkLabel(
        frame,
        text=text,
        font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
        text_color=text_color,
        padx=8,
        pady=2
    )
    lbl.pack()
    return frame


def clear_frame(frame):
    """Elimina todos los widgets hijos de un frame."""
    for widget in frame.winfo_children():
        widget.destroy()


def make_header(parent, title, subtitle=None, right_widget=None):
    """Crea un encabezado estándar de sección."""
    t = tema_actual()
    hdr = ctk.CTkFrame(parent, fg_color="transparent")
    hdr.pack(fill="x", padx=20, pady=(16, 8))
    
    left = ctk.CTkFrame(hdr, fg_color="transparent")
    left.pack(side="left", fill="x", expand=True)
    
    lbl_title = make_label(left, title, tipo="titulo")
    lbl_title.pack(anchor="w")
    
    if subtitle:
        lbl_sub = make_label(left, subtitle, tipo="subtitulo", wrap=600)
        lbl_sub.pack(anchor="w", pady=(2, 0))
        
    if right_widget:
        right_widget.pack(side="right")
        
    sep = make_separator(parent)
    sep.pack(fill="x", padx=20, pady=(4, 10))
    return hdr
