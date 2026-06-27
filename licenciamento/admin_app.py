from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from licenciamento.admin_client import (
    extend_license,
    format_customer_summary,
    get_customer,
    load_admin_config,
    release_activation,
    save_admin_config,
    upsert_license,
)


WINDOW_WIDTH = 860
WINDOW_HEIGHT = 600
BG = "#F4F7FB"
PANEL = "#FFFFFF"
INK = "#111827"
MUTED = "#64748B"
BORDER = "#D8DEE9"
PRIMARY = "#2563EB"
SUCCESS = "#15803D"
DANGER = "#B91C1C"
WARNING = "#B45309"
SLATE = "#475569"


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


class AdminLicenseApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Sistema Guimma Licencas Admin")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(820, 560)
        self.root.configure(bg=BG)

        self.config = load_admin_config()
        self.email_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.days_var = tk.StringVar(value=str(self.config.get("default_days") or 30))
        self.result_var = tk.StringVar(value="Digite o email do cliente e escolha uma acao.")
        self._icon_image = None

        self._build()
        self._center_window()
        self.root.after(100, self._bring_to_front)

    def _build(self) -> None:
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=22, pady=22)
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(2, weight=1)

        self._build_header(shell)
        self._build_form(shell)
        self._build_result(shell)
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
            text="Administrar Licencas",
            bg=BG,
            fg=INK,
            font=("Arial", 22, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_area,
            text="Controle de ativacao, bloqueio, renovacao e troca de computador",
            bg=BG,
            fg=MUTED,
            font=("Arial", 11),
        ).pack(anchor="w", pady=(4, 0))

    def _build_form(self, parent: tk.Widget) -> None:
        form = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        form.grid(row=1, column=0, sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        self._field(form, 0, "Email do cliente", self.email_var)
        self._field(form, 1, "Nome do cliente", self.name_var)
        self._field(form, 2, "Dias", self.days_var, width=12, sticky="w")

        actions = tk.Frame(form, bg=PANEL)
        actions.grid(row=3, column=0, columnspan=3, sticky="ew", padx=24, pady=(14, 22))
        actions.grid_columnconfigure(5, weight=1)

        self._button(actions, "Consultar", self._consult, SLATE).grid(row=0, column=0, padx=(0, 8), sticky="w")
        self._button(actions, "Ativar", self._activate, SUCCESS).grid(row=0, column=1, padx=8, sticky="w")
        self._button(actions, "Renovar", self._renew, PRIMARY).grid(row=0, column=2, padx=8, sticky="w")
        self._button(actions, "Desativar/Bloquear", self._block, DANGER).grid(row=0, column=3, padx=8, sticky="w")
        self._button(actions, "Liberar computador", self._release, WARNING).grid(row=0, column=4, padx=8, sticky="w")
        self._button(actions, "Configurar", self._open_settings, "#6B7280").grid(row=0, column=6, padx=(8, 0), sticky="e")

    def _build_result(self, parent: tk.Widget) -> None:
        result = tk.Frame(parent, bg="#F8FAFC", highlightbackground=BORDER, highlightthickness=1)
        result.grid(row=2, column=0, sticky="nsew", pady=(16, 0))
        result.grid_columnconfigure(0, weight=1)
        result.grid_rowconfigure(1, weight=1)

        tk.Label(
            result,
            text="Resultado",
            bg="#F8FAFC",
            fg=INK,
            font=("Arial", 13, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 6))

        self.result_text = tk.Text(
            result,
            bg="#F8FAFC",
            fg=INK,
            relief="flat",
            wrap="word",
            font=("Menlo", 12),
            height=12,
        )
        self.result_text.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 16))
        self.result_text.insert("1.0", self.result_var.get())
        self.result_text.configure(state="disabled")

    def _build_footer(self, parent: tk.Widget) -> None:
        footer = tk.Frame(parent, bg=BG)
        footer.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        footer.grid_columnconfigure(0, weight=1)
        tk.Label(
            footer,
            text="Desativar/Bloquear corta o acesso por pagamento. Liberar computador apenas permite trocar de maquina.",
            bg=BG,
            fg=MUTED,
            font=("Arial", 10),
        ).grid(row=0, column=0, sticky="w")
        self._button(footer, "Fechar", self.root.destroy, "#6B7280").grid(row=0, column=1, sticky="e")

    def _field(
        self,
        parent: tk.Widget,
        row: int,
        label: str,
        variable: tk.StringVar,
        width: int | None = None,
        sticky: str = "ew",
    ) -> tk.Entry:
        tk.Label(parent, text=label, bg=PANEL, fg=INK, font=("Arial", 11, "bold")).grid(
            row=row,
            column=0,
            sticky="w",
            padx=(24, 16),
            pady=(22 if row == 0 else 10, 4),
        )
        entry = tk.Entry(parent, textvariable=variable, width=width or 40)
        entry.configure(
            bg="#F8FAFC",
            fg=INK,
            insertbackground=PRIMARY,
            relief="flat",
            highlightbackground=BORDER,
            highlightcolor=PRIMARY,
            highlightthickness=1,
            font=("Arial", 12),
        )
        entry.grid(
            row=row,
            column=1,
            sticky=sticky,
            padx=(0, 24),
            pady=(22 if row == 0 else 10, 4),
            ipady=8,
        )
        return entry

    def _button(self, parent: tk.Widget, text: str, command, bg: str) -> tk.Label:
        button = tk.Label(
            parent,
            text=text,
            bg=bg,
            fg="white",
            cursor="hand2",
            font=("Arial", 10, "bold"),
            padx=14,
            pady=9,
        )
        button.bind("<Button-1>", lambda _event: command())
        button.bind("<Return>", lambda _event: command())
        button.bind("<Enter>", lambda _event: button.configure(bg=self._darken(bg)))
        button.bind("<Leave>", lambda _event: button.configure(bg=bg))
        button.configure(takefocus=True)
        return button

    def _email(self) -> str:
        return self.email_var.get().strip().lower()

    def _days(self) -> int:
        try:
            return max(int(self.days_var.get().strip() or "30"), 1)
        except Exception:
            return 30

    def _set_result(self, text: str) -> None:
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text)
        self.result_text.configure(state="disabled")

    def _run(self, action) -> None:
        self.config = load_admin_config()
        try:
            text = action()
            self._set_result(text)
        except Exception as exc:
            self._set_result(f"Erro:\n{exc}")
            messagebox.showerror("Licencas", str(exc), parent=self.root)

    def _consult(self) -> None:
        self._run(lambda: format_customer_summary(get_customer(self._email(), self.config)))

    def _activate(self) -> None:
        def action() -> str:
            result = upsert_license(
                self._email(),
                "active",
                self.config,
                customer_name=self.name_var.get().strip(),
                days=self._days(),
            )
            details = format_customer_summary(get_customer(self._email(), self.config))
            return "Licenca ativada.\n\n" + details

        self._run(action)

    def _renew(self) -> None:
        def action() -> str:
            extend_license(self._email(), self.config, days=self._days())
            details = format_customer_summary(get_customer(self._email(), self.config))
            return f"Licenca renovada por {self._days()} dias.\n\n" + details

        self._run(action)

    def _block(self) -> None:
        confirmed = messagebox.askyesno(
            "Desativar/Bloquear",
            "Deseja bloquear o acesso desta licenca?\n\nO cliente nao conseguira validar enquanto estiver bloqueada.",
            parent=self.root,
        )
        if not confirmed:
            return

        def action() -> str:
            upsert_license(
                self._email(),
                "inactive",
                self.config,
                customer_name=self.name_var.get().strip(),
                days=self._days(),
            )
            details = format_customer_summary(get_customer(self._email(), self.config))
            return "Licenca bloqueada.\n\n" + details

        self._run(action)

    def _release(self) -> None:
        confirmed = messagebox.askyesno(
            "Liberar computador",
            "Deseja liberar o computador ativo desta licenca?\n\nIsso nao cancela a assinatura. Apenas permite ativar em outro computador.",
            parent=self.root,
        )
        if not confirmed:
            return

        def action() -> str:
            release_activation(self._email(), self.config)
            details = format_customer_summary(get_customer(self._email(), self.config))
            return "Computador liberado.\n\n" + details

        self._run(action)

    def _open_settings(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Configuracao administrativa")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        server_var = tk.StringVar(value=str(self.config.get("server_url") or ""))
        token_var = tk.StringVar(value=str(self.config.get("admin_token") or ""))
        days_var = tk.StringVar(value=str(self.config.get("default_days") or 30))

        panel = tk.Frame(dialog, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        panel.pack(fill="both", expand=True, padx=18, pady=18)
        panel.grid_columnconfigure(1, weight=1)

        self._settings_field(panel, 0, "Servidor", server_var)
        self._settings_field(panel, 1, "Token admin", token_var, show="*")
        self._settings_field(panel, 2, "Dias padrao", days_var, width=12, sticky="w")

        buttons = tk.Frame(panel, bg=PANEL)
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", padx=18, pady=(18, 16))

        def save() -> None:
            config = dict(self.config)
            config["server_url"] = server_var.get().strip()
            config["admin_token"] = token_var.get().strip()
            config["default_days"] = days_var.get().strip() or "30"
            try:
                save_admin_config(config)
                self.config = load_admin_config()
                self.days_var.set(str(self.config.get("default_days") or 30))
                dialog.destroy()
                messagebox.showinfo("Licencas", "Configuracao salva.", parent=self.root)
            except Exception as exc:
                messagebox.showerror("Licencas", str(exc), parent=dialog)

        self._button(buttons, "Salvar", save, PRIMARY).pack(side="left", padx=4)
        self._button(buttons, "Cancelar", dialog.destroy, "#6B7280").pack(side="left", padx=4)

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _settings_field(
        self,
        parent: tk.Widget,
        row: int,
        label: str,
        variable: tk.StringVar,
        show: str = "",
        width: int | None = None,
        sticky: str = "ew",
    ) -> tk.Entry:
        tk.Label(parent, text=label, bg=PANEL, fg=INK, font=("Arial", 11, "bold")).grid(
            row=row,
            column=0,
            sticky="w",
            padx=(18, 12),
            pady=(18 if row == 0 else 10, 4),
        )
        entry = tk.Entry(parent, textvariable=variable, show=show, width=width or 54)
        entry.configure(
            bg="#F8FAFC",
            fg=INK,
            relief="flat",
            highlightbackground=BORDER,
            highlightcolor=PRIMARY,
            highlightthickness=1,
            font=("Arial", 11),
        )
        entry.grid(row=row, column=1, sticky=sticky, padx=(0, 18), pady=(18 if row == 0 else 10, 4), ipady=7)
        return entry

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

    def _darken(self, color: str) -> str:
        try:
            value = color.strip().lstrip("#")
            r = max(int(value[0:2], 16) - 24, 0)
            g = max(int(value[2:4], 16) - 24, 0)
            b = max(int(value[4:6], 16) - 24, 0)
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return color


def main() -> int:
    root = tk.Tk()
    AdminLicenseApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
