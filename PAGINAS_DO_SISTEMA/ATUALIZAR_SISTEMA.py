import json
import shutil
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk


class AtualizarSistemaPage(ctk.CTkFrame):
    VERSAO_ATUAL = "1.0"
    SOURCE_URL = (
        "https://drive.google.com/drive/folders/"
        "1vmA4cBJqtQ8IFg43uBMWg79S1HiQD2nG?usp=drive_link"
    )

    def __init__(self, master, sistema=None, app=None, parent=None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = sistema or app or parent
        self.base_dir = Path(__file__).resolve().parent.parent
        self.package_dir = Path(__file__).resolve().parent
        self.backup_root = self.base_dir / "backup_versoes"
        self.download_root = self.base_dir / "atualizacoes_baixadas"
        self.history_path = self.base_dir / "update_history.json"
        self.status_var = ctk.StringVar(value="Pronto para buscar atualizações.")
        self._build_ui()

    def _build_ui(self):
        self.configure(fg_color="transparent")

        header = ctk.CTkFrame(self, corner_radius=12)
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header,
            text="Atualizar Sistema",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w", padx=20, pady=(16, 4))

        ctk.CTkLabel(
            header,
            text=f"Versão atual: {self.VERSAO_ATUAL}",
            font=("Segoe UI", 14),
        ).pack(anchor="w", padx=20, pady=(0, 12))

        info = ctk.CTkFrame(self, corner_radius=12)
        info.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            info,
            text="Fonte de atualização (Google Drive):",
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", padx=20, pady=(12, 2))

        ctk.CTkLabel(
            info,
            text=self.SOURCE_URL,
            font=("Segoe UI", 12),
            wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 12))

        ctk.CTkLabel(
            info,
            text="Tipo de atualização atual: arquivos .py",
            font=("Segoe UI", 12),
        ).pack(anchor="w", padx=20, pady=(0, 12))

        actions = ctk.CTkFrame(self, corner_radius=12)
        actions.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(
            actions,
            text="🔍 Buscar Atualizações",
            command=self._buscar_atualizacoes,
            width=220,
        ).pack(side="left", padx=20, pady=16)

        ctk.CTkButton(
            actions,
            text="↩️ Voltar para versão anterior",
            command=self._restaurar_ultima_versao,
            width=260,
        ).pack(side="left", padx=(0, 20), pady=16)

        ctk.CTkLabel(
            self,
            textvariable=self.status_var,
            font=("Segoe UI", 12),
            justify="left",
        ).pack(fill="x", padx=20, pady=(10, 0))

    def _buscar_atualizacoes(self):
        manifest = self._carregar_manifest_local()
        nova_versao = self._extract_version(manifest)

        if not nova_versao or not self._is_newer_version(nova_versao, self.VERSAO_ATUAL):
            self.status_var.set("Seu sistema já está atualizado.")
            return

        deseja = messagebox.askyesno(
            "Nova versão disponível",
            f"Nova versão disponível: {nova_versao}.\nDeseja atualizar?",
        )
        if not deseja:
            self.status_var.set("Atualização cancelada pelo usuário.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self._backup_current_version(timestamp)
        download_dir = self.download_root / timestamp
        download_dir.mkdir(parents=True, exist_ok=True)
        origem_path = download_dir / "ORIGEM_ATUALIZACAO.txt"
        origem_path.write_text(
            f"Fonte: {self.SOURCE_URL}\n"
            f"Versão detectada: {nova_versao}\n"
            "Baixe os arquivos .py e coloque nesta pasta para aplicar.\n",
            encoding="utf-8",
        )
        self._append_history(
            action="buscar_atualizacoes",
            backup_dir=backup_dir,
            download_dir=download_dir,
            source_url=self.SOURCE_URL,
        )
        self.status_var.set(
            "Backup criado e pasta de download preparada. "
            f"Local: {download_dir}"
        )

    def _restaurar_ultima_versao(self):
        if not self.backup_root.exists():
            self.status_var.set("Nenhum backup encontrado para restaurar.")
            return

        backups = sorted(
            [p for p in self.backup_root.iterdir() if p.is_dir()],
            reverse=True,
        )
        if not backups:
            self.status_var.set("Nenhum backup encontrado para restaurar.")
            return

        backup_dir = backups[0]
        restored = self._restore_backup(backup_dir)
        if restored:
            self._append_history(
                action="rollback",
                backup_dir=backup_dir,
                download_dir=None,
                source_url=self.SOURCE_URL,
            )
            self.status_var.set(f"Versão restaurada a partir de {backup_dir}.")
        else:
            self.status_var.set("Falha ao restaurar a versão anterior.")

    def _backup_current_version(self, timestamp: str) -> Path:
        backup_dir = self.backup_root / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_pkg = backup_dir / "PAGINAS_DO_SISTEMA"
        backup_pkg.mkdir(parents=True, exist_ok=True)

        for py_file in self.base_dir.glob("*.py"):
            shutil.copy2(py_file, backup_dir / py_file.name)

        for py_file in self.package_dir.glob("*.py"):
            shutil.copy2(py_file, backup_pkg / py_file.name)

        return backup_dir

    def _carregar_manifest_local(self) -> dict:
        candidates = [
            self.base_dir / "manifest.json",
            self.base_dir / "update_manifest.json",
            self.download_root / "manifest.json",
        ]
        for path in candidates:
            if not path.exists():
                continue
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
        return {}

    def _extract_version(self, manifest: dict) -> str | None:
        if not manifest:
            return None
        for key in ("version", "versao", "versão"):
            value = manifest.get(key)
            if value:
                return str(value)
        return None

    def _is_newer_version(self, nova: str, atual: str) -> bool:
        def parse(v: str) -> tuple[int, ...]:
            parts = []
            for chunk in str(v).split("."):
                try:
                    parts.append(int(chunk))
                except ValueError:
                    parts.append(0)
            return tuple(parts)

        return parse(nova) > parse(atual)

    def _restore_backup(self, backup_dir: Path) -> bool:
        try:
            for py_file in backup_dir.glob("*.py"):
                shutil.copy2(py_file, self.base_dir / py_file.name)

            backup_pkg = backup_dir / "PAGINAS_DO_SISTEMA"
            if backup_pkg.exists():
                for py_file in backup_pkg.glob("*.py"):
                    shutil.copy2(py_file, self.package_dir / py_file.name)
            return True
        except Exception as exc:
            print(f"Erro ao restaurar backup: {exc}")
            return False

    def _append_history(
        self,
        action: str,
        backup_dir: Path | None,
        download_dir: Path | None,
        source_url: str,
    ):
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "version": self.VERSAO_ATUAL,
            "backup_dir": str(backup_dir) if backup_dir else None,
            "download_dir": str(download_dir) if download_dir else None,
            "source_url": source_url,
        }

        history = []
        if self.history_path.exists():
            try:
                history = json.loads(self.history_path.read_text(encoding="utf-8"))
            except Exception:
                history = []

        history.append(entry)
        self.history_path.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
