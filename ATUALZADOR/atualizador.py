from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk


APP_DEFAULT_VERSION = "1.0"
APP_TITLE = "Atualizador do Sistema"
UPDATES_DIR = Path(r"C:\SISTEMA_GUIMMA\updates")
MANIFEST_FILENAME = "manifest.json"


class AtualizadorApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("light")

        self.title(APP_TITLE)
        self.geometry("980x620")
        self.minsize(900, 560)
        self.configure(fg_color="#F5F8FF")

        self._status_value = ctk.StringVar(value="Pronto para verificar atualizações.")
        self._last_check_value = ctk.StringVar(value="Última verificação: --/--/---- --:--")
        self._version_value = ctk.StringVar(value=f"Versão do sistema {self._carregar_versao()}")
        self._updates_path_value = ctk.StringVar(
            value=f"Pasta de atualizações: {UPDATES_DIR}",
        )

        self._montar_interface()

    def _montar_interface(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=16, fg_color="#E6F0FF")
        header.pack(fill="x", padx=24, pady=(24, 16))

        titulo = ctk.CTkLabel(
            header,
            text="Atualização do Sistema",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#0B4B91",
        )
        titulo.pack(anchor="w", padx=20, pady=(16, 4))

        subtitulo = ctk.CTkLabel(
            header,
            text="Gerencie versões, verifique novidades e aplique atualizações com segurança.",
            font=ctk.CTkFont(size=14),
            text_color="#2A5FA8",
        )
        subtitulo.pack(anchor="w", padx=20, pady=(0, 16))

        corpo = ctk.CTkFrame(self, corner_radius=20, fg_color="#FFFFFF")
        corpo.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        coluna_info = ctk.CTkFrame(corpo, corner_radius=16, fg_color="#F7FAFF")
        coluna_info.pack(side="left", fill="both", expand=True, padx=20, pady=20)

        self._criar_card(
            coluna_info,
            titulo="Versão instalada",
            valor=self._version_value,
        )
        self._criar_card(
            coluna_info,
            titulo="Status",
            valor=self._status_value,
        )
        self._criar_card(
            coluna_info,
            titulo="Verificação",
            valor=self._last_check_value,
        )
        self._criar_card(
            coluna_info,
            titulo="Origem dos arquivos",
            valor=self._updates_path_value,
        )

        coluna_acao = ctk.CTkFrame(corpo, corner_radius=16, fg_color="#EFF5FF")
        coluna_acao.pack(side="right", fill="y", padx=(0, 20), pady=20)

        ctk.CTkLabel(
            coluna_acao,
            text="Ações rápidas",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#0B4B91",
        ).pack(pady=(20, 12), padx=20)

        self._criar_botao(
            coluna_acao,
            texto="Verificar Atualizações",
            comando=self._verificar_atualizacoes,
            cor="#1E6BD6",
        )
        self._criar_botao(
            coluna_acao,
            texto="Atualizar Sistema",
            comando=self._atualizar_sistema,
            cor="#2B7BEA",
        )
        self._criar_botao(
            coluna_acao,
            texto="Restaurar Backup",
            comando=self._restaurar_backup,
            cor="#5C8FDB",
        )

        ctk.CTkLabel(
            coluna_acao,
            text="Tema leve com tons de azul.",
            font=ctk.CTkFont(size=12),
            text_color="#5C8FDB",
        ).pack(pady=(16, 20))

    def _criar_card(self, parent: ctk.CTkFrame, titulo: str, valor: ctk.StringVar) -> None:
        card = ctk.CTkFrame(parent, corner_radius=14, fg_color="#FFFFFF", border_width=1, border_color="#D8E6FF")
        card.pack(fill="x", padx=18, pady=12)

        ctk.CTkLabel(
            card,
            text=titulo,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#1E4F91",
        ).pack(anchor="w", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            card,
            textvariable=valor,
            font=ctk.CTkFont(size=15),
            text_color="#2C5EA8",
            wraplength=360,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 12))

    def _criar_botao(self, parent: ctk.CTkFrame, texto: str, comando, cor: str) -> None:
        ctk.CTkButton(
            parent,
            text=texto,
            command=comando,
            fg_color=cor,
            hover_color="#1A5CC0",
            text_color="#FFFFFF",
            corner_radius=12,
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(fill="x", padx=20, pady=8)

    def _carregar_versao(self) -> str:
        config_path = Path(__file__).resolve().parents[1] / "app_config.json"
        if not config_path.exists():
            return APP_DEFAULT_VERSION
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return APP_DEFAULT_VERSION
        return str(data.get("versao", APP_DEFAULT_VERSION))

    def _verificar_atualizacoes(self) -> None:
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        self._last_check_value.set(f"Última verificação: {agora}")
        manifest_path = UPDATES_DIR / MANIFEST_FILENAME
        if not manifest_path.exists():
            self._status_value.set(
                f"Nenhuma atualização encontrada. Falta {manifest_path}.",
            )
            messagebox.showwarning(
                "Atualizador",
                f"Manifesto não encontrado em {manifest_path}.",
            )
            return
        self._status_value.set("Manifesto localizado. Pronto para atualizar.")
        messagebox.showinfo(
            "Atualizador",
            f"Manifesto encontrado em {manifest_path}.",
        )

    def _atualizar_sistema(self) -> None:
        manifest_path = UPDATES_DIR / MANIFEST_FILENAME
        if not manifest_path.exists():
            self._status_value.set(
                "Não foi possível atualizar sem o manifesto.",
            )
            messagebox.showwarning(
                "Atualizador",
                f"Adicione o manifesto em {manifest_path} para continuar.",
            )
            return
        self._status_value.set("Atualização iniciada. Aguarde...")
        messagebox.showinfo(
            "Atualizador",
            "Aqui o atualizador fará backup e aplicará os arquivos de update.",
        )
        self._status_value.set("Atualização simulada concluída.")

    def _restaurar_backup(self) -> None:
        self._status_value.set("Restaurando backup...")
        messagebox.showwarning(
            "Atualizador",
            "A restauração de backup será implementada com segurança nesta etapa.",
        )
        self._status_value.set("Backup pronto para restauração.")


if __name__ == "__main__":
    app = AtualizadorApp()
    app.mainloop()
