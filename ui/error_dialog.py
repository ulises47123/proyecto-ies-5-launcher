"""
ui/error_dialog.py — Ventana emergente modal de error con texto seleccionable y copiable.
Permite seleccionar texto con el ratón, menú contextual de clic derecho y botón de copiado directo.
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from ui.theme import tema_actual


def mostrar_dialogo_error(titulo: str = "Error", mensaje: str = "", parent=None, tipo: str = "error"):
    """
    Muestra una ventana modal emergente de error o advertencia con texto 100% seleccionable y copiable.
    """
    try:
        t = tema_actual()

        # Buscar ventana raíz activa si parent no fue provisto
        if parent is None:
            parent = tk._default_root

        # Crear ventana emergente Toplevel
        dialog = ctk.CTkToplevel(parent)
        dialog.title(f"{titulo}")
        dialog.geometry("520x340")
        dialog.minsize(420, 260)
        dialog.configure(fg_color=t["bg"])

        # Asegurar comportamiento modal
        dialog.transient(parent)
        dialog.grab_set()

        # Centrar la ventana sobre la ventana padre o la pantalla
        try:
            dialog.update_idletasks()
            if parent and parent.winfo_viewable():
                px = parent.winfo_rootx() + (parent.winfo_width() // 2) - 260
                py = parent.winfo_rooty() + (parent.winfo_height() // 2) - 170
                dialog.geometry(f"+{max(10, px)}+{max(10, py)}")
            else:
                sx = (dialog.winfo_screenwidth() // 2) - 260
                sy = (dialog.winfo_screenheight() // 2) - 170
                dialog.geometry(f"+{max(10, sx)}+{max(10, sy)}")
        except Exception:
            pass

        # Encabezado con icono de error
        header_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(18, 8))

        es_warning = any(w in (titulo or "").lower() for w in ["aviso", "advertencia", "warning", "atención"])
        color_tit = "#f59e0b" if es_warning else "#ef4444"
        icono_tit = "⚠️" if es_warning else "❌"

        lbl_icono = ctk.CTkLabel(
            header_frame,
            text=icono_tit,
            font=ctk.CTkFont(family="Segoe UI", size=24)
        )
        lbl_icono.pack(side="left", padx=(0, 10))

        lbl_tit = ctk.CTkLabel(
            header_frame,
            text=titulo or "Se ha producido un error",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=color_tit,
            anchor="w"
        )
        lbl_tit.pack(side="left", fill="x", expand=True)

        lbl_sub = ctk.CTkLabel(
            dialog,
            text="Puedes seleccionar con el cursor o copiar todo el texto a continuación:",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=t["muted"],
            anchor="w"
        )
        lbl_sub.pack(fill="x", padx=20, pady=(0, 6))

        # Cuadro de texto seleccionable para el detalle del error
        text_box = ctk.CTkTextbox(
            dialog,
            fg_color=t["card"],
            text_color=t["text"],
            wrap="word",
            border_width=1,
            border_color=t["border"],
            font=ctk.CTkFont(family="Consolas" if "\n" in str(mensaje) else "Segoe UI", size=12),
            activate_scrollbars=True
        )
        text_box.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        msg_str = str(mensaje)
        text_box.insert("1.0", msg_str)

        # Menú contextual de clic derecho para copiar
        menu_ctx = tk.Menu(text_box, tearoff=0)

        def copiar_seleccion():
            try:
                sel = text_box.get(tk.SEL_FIRST, tk.SEL_LAST)
                if sel:
                    dialog.clipboard_clear()
                    dialog.clipboard_append(sel)
            except Exception:
                dialog.clipboard_clear()
                dialog.clipboard_append(text_box.get("1.0", "end-1c"))

        def copiar_todo():
            dialog.clipboard_clear()
            dialog.clipboard_append(text_box.get("1.0", "end-1c"))

        menu_ctx.add_command(label="Copiar selección", command=copiar_seleccion)
        menu_ctx.add_command(label="Copiar todo el error", command=copiar_todo)
        text_box.bind("<Button-3>", lambda e: menu_ctx.tk_popup(e.x_root, e.y_root))

        # Botonera inferior
        btn_box = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(0, 16))

        def on_copiar_btn():
            copiar_todo()
            btn_copiar.configure(text="✅ ¡Copiado!", fg_color=t["success"])
            dialog.after(1500, lambda: btn_copiar.configure(text="📋 Copiar error", fg_color=t["card"]))

        btn_copiar = ctk.CTkButton(
            btn_box,
            text="📋 Copiar error",
            command=on_copiar_btn,
            fg_color=t["card"],
            hover_color=t["border"],
            text_color=t["text"],
            border_width=1,
            border_color=t["border"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=34
        )
        btn_copiar.pack(side="left")

        def on_cerrar():
            try:
                dialog.grab_release()
                dialog.destroy()
            except Exception:
                pass

        btn_cerrar = ctk.CTkButton(
            btn_box,
            text="Cerrar",
            command=on_cerrar,
            fg_color=t["accent"],
            hover_color=t["accent_hover"],
            text_color=t["btn_text"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=34,
            width=90
        )
        btn_cerrar.pack(side="right")

        dialog.bind("<Escape>", lambda _: on_cerrar())
        dialog.focus_set()
        return dialog

    except Exception:
        if hasattr(messagebox, "_original_showerror"):
            return messagebox._original_showerror(titulo, mensaje, parent=parent)
        return None


def activar_dialogos_error_seleccionables():
    """Activa el hook global para que errores y avisos usen la ventana emergente seleccionable y copiable."""
    if not hasattr(messagebox, "_original_showerror"):
        messagebox._original_showerror = messagebox.showerror
        messagebox.showerror = mostrar_dialogo_error
    if not hasattr(messagebox, "_original_showwarning"):
        messagebox._original_showwarning = messagebox.showwarning
        messagebox.showwarning = lambda tit="Aviso", msg="", **kwargs: mostrar_dialogo_error(tit, msg, parent=kwargs.get("parent"))
