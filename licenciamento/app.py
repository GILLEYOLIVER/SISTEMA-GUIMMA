from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from licenciamento.agent import main as agent_main
from licenciamento.autorun import install_autostart
from licenciamento.client import current_status_text, deactivate_current, load_config, save_config, sync_once
from licenciamento.machine import machine_id
from licenciamento.store import validate_state


WINDOW_WIDTH = 820
WINDOW_HEIGHT = 560
BG = "#F4F7FB"
PANEL = "#FFFFFF"
INK = "#111827"
MUTED = "#64748B"
BORDER = "#D8DEE9"
PRIMARY = "#2563EB"
PRIMARY_DARK = "#1D4ED8"
SUCCESS = "#15803D"
DANGER = "#B91C1C"
WARNING = "#B45309"


def _asset_path(*parts: str) -> Path | None:
    bases = [
        Path(getattr(sys, "_MEIPASS", "") or ""),
        Path(__file__).resolve().parent.parent,
        Path.cwd(),
    ]
    for base in bases:
        if not str(base):
            continue
        candidate = base.joinpath(*parts)
        if candidate.exists():
            return candidate
    return None


class LicenseApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Sistema Guimma Licenca")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(760, 520)
        self.root.configure(bg=BG)

        self.config = load_config()
        self.enabled_var = tk.BooleanVar(value=True)
        self.server_var = tk.StringVar(value=str(self.config.get("server_url") or ""))
        self.email_var = tk.StringVar(value=str(self.config.get("customer_email") or ""))
        self.status_var = tk.StringVar(value=current_status_text())
        self._icon_image = None

        self._configure_style()
        self._build()
        self._refresh_status()
        self._center_window()
        self.root.after(100, self._bring_to_front)

    def _build(self) -> None:
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=22, pady=22)
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(1, weight=1)

        self._build_header(shell)
        self._build_body(shell)
        self._build_footer(shell)

    def _build_header(self, parent: tk.Widget) -> None:
        header = tk.Frame(parent, bg=BG)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.grid_columnconfigure(1, weight=1)

        self._icon_image = self._load_icon()
        icon_box = tk.Frame(header, bg="#EAF2FF", width=58, height=58)
        icon_box.grid(row=0, column=0, sticky="nw")
        icon_box.grid_propagate(False)
        if self._icon_image:
            tk.Label(icon_box, image=self._icon_image, bg="#EAF2FF").place(relx=0.5, rely=0.5, anchor="center")
        else:
            tk.Label(icon_box, text="SG", bg="#EAF2FF", fg=PRIMARY, font=("Arial", 16, "bold")).place(
                relx=0.5, rely=0.5, anchor="center"
            )

        title_area = tk.Frame(header, bg=BG)
        title_area.grid(row=0, column=1, sticky="ew", padx=14)
        tk.Label(
            title_area,
            text="Licenciamento Sistema Guimma",
            bg=BG,
            fg=INK,
            font=("Arial", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_area,
            text="Validacao da assinatura mensal por email do cliente",
            bg=BG,
            fg=MUTED,
            font=("Arial", 11),
        ).pack(anchor="w", pady=(4, 0))

    def _build_body(self, parent: tk.Widget) -> None:
        body = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(1, weight=1)

        self._field(body, 0, "ID deste computador", machine_id(), readonly=True, copy_button=True)
        self._field(body, 1, "Email do cliente", self.email_var)

        option = tk.Checkbutton(
            body,
            text="Exigir licenca valida para abrir o Sistema Guimma",
            variable=self.enabled_var,
            bg=PANEL,
            fg=INK,
            activebackground=PANEL,
            activeforeground=INK,
            selectcolor=PANEL,
            font=("Arial", 11),
            anchor="w",
            state="disabled",
        )
        option.grid(row=2, column=1, sticky="w", padx=(0, 24), pady=(8, 14))

        status_wrap = tk.Frame(body, bg="#F8FAFC", highlightbackground=BORDER, highlightthickness=1)
        status_wrap.grid(row=3, column=0, columnspan=3, sticky="ew", padx=24, pady=(6, 20))
        status_wrap.grid_columnconfigure(1, weight=1)

        self.status_dot = tk.Label(status_wrap, text="", bg=WARNING, width=2, height=1)
        self.status_dot.grid(row=0, column=0, sticky="nw", padx=(16, 10), pady=16)
        tk.Label(
            status_wrap,
            text="Status da licenca",
            bg="#F8FAFC",
            fg=INK,
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=1, sticky="w", pady=(12, 0))
        self.status_label = tk.Label(
            status_wrap,
            textvariable=self.status_var,
            bg="#F8FAFC",
            fg=MUTED,
            font=("Arial", 11),
            wraplength=660,
            justify="left",
            anchor="w",
        )
        self.status_label.grid(row=1, column=1, sticky="ew", padx=(0, 16), pady=(4, 14))

    def _build_footer(self, parent: tk.Widget) -> None:
        footer = tk.Frame(parent, bg=BG)
        footer.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        footer.grid_columnconfigure(0, weight=1)

        tk.Label(
            footer,
            text="Use o email cadastrado na assinatura do cliente.",
            bg=BG,
            fg=MUTED,
            font=("Arial", 10),
        ).grid(row=0, column=0, sticky="w")

        buttons = tk.Frame(footer, bg=BG)
        buttons.grid(row=0, column=1, sticky="e")
        self._button(buttons, "Salvar", self._save, PRIMARY).pack(side="left", padx=4)
        self._button(buttons, "Validar agora", self._sync, SUCCESS).pack(side="left", padx=4)
        self._button(buttons, "Desativar", self._deactivate, DANGER).pack(side="left", padx=4)
        self._button(buttons, "Iniciar com o computador", self._install_autostart, "#475569").pack(side="left", padx=4)
        self._button(buttons, "Fechar", self.root.destroy, "#6B7280").pack(side="left", padx=4)

    def _field(
        self,
        parent: tk.Widget,
        row: int,
        label: str,
        value,
        readonly: bool = False,
        copy_button: bool = False,
    ) -> tk.Entry:
        tk.Label(parent, text=label, bg=PANEL, fg=INK, font=("Arial", 11, "bold")).grid(
            row=row,
            column=0,
            sticky="w",
            padx=(24, 16),
            pady=(22 if row == 0 else 10, 4),
        )

        if isinstance(value, tk.StringVar):
            entry = tk.Entry(parent, textvariable=value)
        else:
            entry = tk.Entry(parent)
            entry.insert(0, str(value))
        entry.configure(
            bg="#F8FAFC",
            fg=INK,
            insertbackground=PRIMARY,
            relief="flat",
            highlightbackground=BORDER,
            highlightcolor=PRIMARY,
            highlightthickness=1,
            font=("Arial", 11),
        )
        if readonly:
            entry.configure(state="readonly", readonlybackground="#F8FAFC")
        entry.grid(row=row, column=1, sticky="ew", padx=(0, 10), pady=(22 if row == 0 else 10, 4), ipady=8)

        if copy_button:
            self._button(parent, "Copiar", lambda: self._copy_machine_id(entry), "#475569").grid(
                row=row,
                column=2,
                sticky="ew",
                padx=(0, 24),
                pady=(22 if row == 0 else 10, 4),
            )
        else:
            tk.Frame(parent, bg=PANEL, width=72).grid(row=row, column=2, padx=(0, 24))
        return entry

    def _collect_config(self) -> dict:
        config = dict(self.config)
        config["enabled"] = True
        config["server_url"] = self.server_var.get().strip()
        config["customer_email"] = self.email_var.get().strip().lower()
        return config

    def _save(self) -> None:
        self.config = self._collect_config()
        save_config(self.config)
        self._refresh_status()
        messagebox.showinfo("Licenciamento", "Configuracao salva.", parent=self.root)

    def _sync(self) -> None:
        self.config = self._collect_config()
        save_config(self.config)
        try:
            sync_once(self.config)
            self._refresh_status()
            messagebox.showinfo("Licenciamento", "Licenca validada com sucesso.", parent=self.root)
        except Exception as exc:
            self._refresh_status()
            messagebox.showerror("Licenciamento", f"Nao foi possivel validar a licenca:\n{exc}", parent=self.root)

    def _deactivate(self) -> None:
        self.config = self._collect_config()
        save_config(self.config)
        confirmed = messagebox.askyesno(
            "Desativar licenca",
            "Deseja desativar a licenca neste computador?\n\nDepois disso ela podera ser ativada em outro computador.",
            parent=self.root,
        )
        if not confirmed:
            return

        try:
            result = deactivate_current(self.config)
            self._refresh_status()
            messagebox.showinfo(
                "Licenciamento",
                result.get("message") or "Licenca desativada neste computador.",
                parent=self.root,
            )
        except Exception as exc:
            self._refresh_status()
            messagebox.showerror("Licenciamento", f"Nao foi possivel desativar a licenca:\n{exc}", parent=self.root)

    def _install_autostart(self) -> None:
        try:
            result = install_autostart()
            messagebox.showinfo("Licenciamento", result, parent=self.root)
        except Exception as exc:
            messagebox.showerror("Licenciamento", f"Falha ao instalar inicializacao automatica:\n{exc}", parent=self.root)

    def _refresh_status(self) -> None:
        validation = validate_state()
        self.status_var.set(validation.message)
        if validation.ok:
            color = WARNING if validation.grace else SUCCESS
            text_color = WARNING if validation.grace else SUCCESS
        else:
            color = DANGER
            text_color = DANGER
        try:
            self.status_dot.configure(bg=color)
            self.status_label.configure(fg=text_color)
        except Exception:
            pass

    def _configure_style(self) -> None:
        try:
            style = ttk.Style(self.root)
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except Exception:
            pass

    def _button(self, parent: tk.Widget, text: str, command, bg: str) -> tk.Label:
        normal_bg = bg
        hover_bg = PRIMARY_DARK if bg == PRIMARY else self._darken(bg)
        button = tk.Label(
            parent,
            text=text,
            bg=bg,
            fg="white",
            cursor="hand2",
            font=("Arial", 10, "bold"),
            padx=14,
            pady=8,
        )
        button.bind("<Button-1>", lambda _event: command())
        button.bind("<Return>", lambda _event: command())
        button.bind("<Enter>", lambda _event: button.configure(bg=hover_bg))
        button.bind("<Leave>", lambda _event: button.configure(bg=normal_bg))
        button.configure(takefocus=True)
        return button

    def _darken(self, color: str) -> str:
        try:
            color = color.strip().lstrip("#")
            r = max(int(color[0:2], 16) - 24, 0)
            g = max(int(color[2:4], 16) - 24, 0)
            b = max(int(color[4:6], 16) - 24, 0)
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return color

    def _copy_machine_id(self, entry: tk.Entry) -> None:
        try:
            value = entry.get()
            self.root.clipboard_clear()
            self.root.clipboard_append(value)
            self.status_var.set("ID do computador copiado.")
        except Exception:
            pass

    def _load_icon(self):
        icon_path = _asset_path("icons", "ICONE_SISTEMA.png")
        if icon_path is None:
            return None
        try:
            from PIL import Image, ImageTk

            image = Image.open(icon_path).convert("RGBA").resize((42, 42), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except Exception:
            try:
                return tk.PhotoImage(file=str(icon_path))
            except Exception:
                return None

    def _center_window(self) -> None:
        self.root.update_idletasks()
        width = max(self.root.winfo_width(), WINDOW_WIDTH)
        height = max(self.root.winfo_height(), WINDOW_HEIGHT)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max((screen_w - width) // 2, 0)
        y = max((screen_h - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _bring_to_front(self) -> None:
        try:
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass


def main() -> int:
    passthrough = {
        "--daemon",
        "--sync-once",
        "--status",
        "--install-autostart",
        "--uninstall-autostart",
        "--enable",
        "--disable",
        "--deactivate",
    }
    if any(arg in passthrough for arg in sys.argv[1:]):
        return agent_main(sys.argv[1:])

    root = tk.Tk()
    LicenseApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
