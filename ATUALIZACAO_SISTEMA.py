import threading
from tkinter import messagebox

import customtkinter as ctk

from sistema_atualizacao import atualizar_sistema, downgrade_sistema


class AtualizacaoSistemaPage(ctk.CTkFrame):
    def __init__(self, master=None, parent=None, app=None, sistema=None, host=None, **kwargs):
        container = master or parent
        if container is None:
            raise ValueError("Container principal não informado para AtualizacaoSistemaPage.")
        super().__init__(container, **kwargs)
        self.app = app or sistema or host

        self._build_layout()

    def _build_layout(self) -> None:
        self.configure(fg_color=self._get_color("cor_fundo", "#1e1e1e"))

        container = ctk.CTkFrame(
            self,
            fg_color=self._get_color("cor_secundaria", "#2d2d30"),
            corner_radius=16,
            border_width=1,
            border_color=self._get_color("cor_borda", "#404040"),
        )
        container.pack(fill="both", expand=True, padx=40, pady=40)

        title = ctk.CTkLabel(
            container,
            text="Atualização do Sistema",
            font=("Arial", 20, "bold"),
            text_color=self._get_color("cor_texto", "#cccccc"),
        )
        title.pack(pady=(30, 10))

        subtitle = ctk.CTkLabel(
            container,
            text="Use os botões abaixo para aplicar uma nova versão ou voltar ao último backup.",
            font=("Arial", 14),
            text_color=self._get_color("cor_texto_secundario", "#888888"),
            wraplength=520,
            justify="center",
        )
        subtitle.pack(pady=(0, 30))

        button_frame = ctk.CTkFrame(container, fg_color="transparent")
        button_frame.pack(pady=10)

        self.update_button = ctk.CTkButton(
            button_frame,
            text="Atualizar Sistema",
            width=220,
            height=45,
            fg_color=self._get_color("cor_destaque", "#007acc"),
            hover_color=self._get_color("cor_hover", "#4a4a4a"),
            command=self._handle_update,
        )
        self.update_button.grid(row=0, column=0, padx=15, pady=10)

        self.downgrade_button = ctk.CTkButton(
            button_frame,
            text="Voltar Versão (Downgrade)",
            width=220,
            height=45,
            fg_color=self._get_color("cor_alerta", "#a1260d"),
            hover_color=self._get_color("cor_hover", "#4a4a4a"),
            command=self._handle_downgrade,
        )
        self.downgrade_button.grid(row=0, column=1, padx=15, pady=10)

        self.status_label = ctk.CTkLabel(
            container,
            text="",
            font=("Arial", 12),
            text_color=self._get_color("cor_texto_secundario", "#888888"),
        )
        self.status_label.pack(pady=(20, 10))

    def _get_color(self, attr_name: str, fallback: str) -> str:
        if self.app and hasattr(self.app, attr_name):
            return getattr(self.app, attr_name)
        return fallback

    def _set_status(self, message: str) -> None:
        self.status_label.configure(text=message)

    def _run_in_thread(self, target, description: str) -> None:
        self.update_button.configure(state="disabled")
        self.downgrade_button.configure(state="disabled")
        self._set_status(description)

        def worker():
            try:
                log_path = target()
                self.after(0, lambda: self._show_success(log_path))
            except Exception as exc:
                self.after(0, lambda: self._show_error(exc))
            finally:
                self.after(0, self._restore_buttons)

        threading.Thread(target=worker, daemon=True).start()

    def _restore_buttons(self) -> None:
        self.update_button.configure(state="normal")
        self.downgrade_button.configure(state="normal")

    def _show_success(self, log_path: str) -> None:
        self._set_status("Processo concluído com sucesso.")
        messagebox.showinfo(
            "Atualização do Sistema",
            f"Processo concluído com sucesso.\nLog salvo em:\n{log_path}",
            parent=self,
        )

    def _show_error(self, exc: Exception) -> None:
        self._set_status("Ocorreu um erro no processo.")
        messagebox.showerror(
            "Atualização do Sistema",
            f"Ocorreu um erro durante o processo:\n{exc}",
            parent=self,
        )

    def _handle_update(self) -> None:
        if not messagebox.askyesno(
            "Atualizar Sistema",
            "Deseja aplicar a atualização a partir da pasta 'Versao do Sistema'?",
            parent=self,
        ):
            return
        self._run_in_thread(atualizar_sistema, "Executando atualização...")

    def _handle_downgrade(self) -> None:
        if not messagebox.askyesno(
            "Voltar Versão",
            "Deseja restaurar o último backup de atualização?",
            parent=self,
        ):
            return
        self._run_in_thread(downgrade_sistema, "Executando downgrade...")
