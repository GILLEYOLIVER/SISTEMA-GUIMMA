# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from PAGINAS_DO_SISTEMA.LOGOMARCA import (
    clear_custom_logo,
    get_logo_path,
    load_visual_settings,
    set_logo_from_file,
)


class ConfiguracoesSistemaPage(ctk.CTkFrame):
    """Configuracoes visuais e gerais do sistema."""

    def __init__(self, master, sistema=None, app=None, host=None):
        super().__init__(master)
        self.sistema = sistema or app or host
        self.app = self.sistema
        self.logo_preview = None
        self.logo_path_var = ctk.StringVar(value=get_logo_path())
        self._apply_colors()
        self._build_ui()
        self._refresh_logo_preview()

    def _color(self, name: str, fallback: str) -> str:
        return getattr(self.sistema, name, fallback) if self.sistema is not None else fallback

    def _apply_colors(self):
        self.cor_fundo = self._color("cor_fundo", "#F8FAFC")
        self.cor_secundaria = self._color("cor_secundaria", "#E5E7EB")
        self.cor_terciaria = self._color("cor_terciaria", "#FFFFFF")
        self.cor_texto = self._color("cor_texto", "#111827")
        self.cor_borda = self._color("cor_borda", "#CBD5E1")
        self.cor_primaria = self._color("cor_primaria", "#2563EB")
        self.cor_hover = self._color("cor_hover", "#1D4ED8")

    def _build_ui(self):
        self.configure(fg_color=self.cor_fundo)
        main = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        main.pack(fill="both", expand=True, padx=18, pady=16)

        ctk.CTkLabel(
            main,
            text="Configuracoes do Sistema",
            font=("Arial", 22, "bold"),
            text_color=self.cor_texto,
        ).pack(anchor="w", pady=(0, 14))

        panel = ctk.CTkFrame(
            main,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            border_width=1,
            corner_radius=8,
        )
        panel.pack(fill="x", anchor="n")
        panel.grid_columnconfigure(1, weight=1)

        preview_box = ctk.CTkFrame(panel, fg_color=self.cor_secundaria, width=210, height=130, corner_radius=8)
        preview_box.grid(row=0, column=0, rowspan=6, padx=14, pady=14, sticky="n")
        preview_box.grid_propagate(False)
        self.preview_label = ctk.CTkLabel(preview_box, text="", text_color=self.cor_texto)
        self.preview_label.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            panel,
            text="Logomarca do cliente",
            font=("Arial", 16, "bold"),
            text_color=self.cor_texto,
        ).grid(row=0, column=1, padx=(0, 14), pady=(16, 4), sticky="w")

        ctk.CTkLabel(
            panel,
            text="O sistema sai sem logomarca. Escolha a imagem do cliente para salvar no banco e distribuir para todos os computadores da rede.",
            text_color=self.cor_texto,
            wraplength=680,
            justify="left",
        ).grid(row=1, column=1, padx=(0, 14), pady=(0, 10), sticky="w")

        ctk.CTkLabel(
            panel,
            text=(
                "Formato recomendado: PNG com fundo transparente ou JPG, logo horizontal, "
                "proporcao entre 3:1 e 4:1, minimo 600x180 px. "
                "No topo do sistema ela aparece em ate 120x38 px, sempre sem distorcer."
            ),
            text_color=self.cor_texto,
            wraplength=680,
            justify="left",
        ).grid(row=2, column=1, padx=(0, 14), pady=(0, 10), sticky="w")

        self.path_entry = ctk.CTkEntry(
            panel,
            textvariable=self.logo_path_var,
            height=34,
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
        )
        self.path_entry.grid(row=3, column=1, padx=(0, 14), pady=(0, 8), sticky="ew")

        self.logo_info_label = ctk.CTkLabel(
            panel,
            text="",
            text_color=self.cor_texto,
            justify="left",
        )
        self.logo_info_label.grid(row=4, column=1, padx=(0, 14), pady=(0, 10), sticky="w")

        actions = ctk.CTkFrame(panel, fg_color="transparent")
        actions.grid(row=5, column=1, padx=(0, 14), pady=(0, 16), sticky="w")

        ctk.CTkButton(
            actions,
            text="Escolher imagem",
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            command=self._choose_logo,
            width=150,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            actions,
            text="Remover logomarca",
            fg_color="#6B7280",
            hover_color="#4B5563",
            command=self._restore_default_logo,
            width=155,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            actions,
            text="Abrir pasta",
            fg_color="#0F766E",
            hover_color="#115E59",
            command=self._open_logo_folder,
            width=110,
        ).pack(side="left")

        self.status_label = ctk.CTkLabel(main, text="", text_color=self.cor_texto)
        self.status_label.pack(anchor="w", pady=(10, 0))

    def _choose_logo(self):
        path = filedialog.askopenfilename(
            title="Escolher logomarca",
            filetypes=[
                ("Imagens", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not path:
            return
        try:
            saved_path = set_logo_from_file(path)
            self.logo_path_var.set(saved_path)
            self._refresh_logo_preview()
            self.status_label.configure(text="Logomarca atualizada. Reabra telas ja abertas para aplicar em todos os lugares.")
            if self.sistema is not None:
                setattr(self.sistema, "logo_path", saved_path)
                if hasattr(self.sistema, "_refresh_system_logo"):
                    self.sistema._refresh_system_logo()
        except Exception as exc:
            messagebox.showerror("Logomarca", f"Falha ao salvar logomarca:\n{exc}", parent=self)

    def _restore_default_logo(self):
        clear_custom_logo()
        self.logo_path_var.set(get_logo_path())
        self._refresh_logo_preview()
        self.status_label.configure(text="Logomarca removida. O sistema ficara sem logo ate o cliente escolher uma.")
        if self.sistema is not None and hasattr(self.sistema, "_refresh_system_logo"):
            self.sistema._refresh_system_logo()

    def _refresh_logo_preview(self):
        path = self.logo_path_var.get() or get_logo_path()
        if not path or not os.path.isfile(path):
            self.preview_label.configure(image=None, text="Sem logomarca")
            self.logo_info_label.configure(text="")
            self.logo_preview = None
            return
        try:
            img = Image.open(path)
            original_w, original_h = img.size
            preview_img = img.copy()
            preview_img.thumbnail((180, 100))
            self.logo_preview = ctk.CTkImage(light_image=preview_img, dark_image=preview_img, size=preview_img.size)
            self.preview_label.configure(image=self.logo_preview, text="")
            ratio = (original_w / original_h) if original_h else 0
            hint = ""
            if ratio and (ratio < 3.0 or ratio > 4.0):
                hint = " | Fora da proporcao recomendada"
            self.logo_info_label.configure(
                text=f"Imagem: {original_w}x{original_h} px | proporcao {ratio:.2f}:1{hint}"
            )
        except Exception:
            self.preview_label.configure(image=None, text="Imagem invalida")
            self.logo_info_label.configure(text="")
            self.logo_preview = None

    def _open_logo_folder(self):
        settings = load_visual_settings()
        current = settings.get("logo_path") or self.logo_path_var.get()
        folder = Path(current).parent if current else Path.home()
        try:
            os.startfile(str(folder))
        except Exception:
            messagebox.showinfo("Pasta da logomarca", str(folder), parent=self)
