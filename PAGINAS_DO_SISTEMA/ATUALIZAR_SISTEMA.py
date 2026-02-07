import json
import re
import shutil
import urllib.request
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
        if not manifest:
            manifest = self._carregar_manifest_drive()
        nova_versao = self._extract_version(manifest)

        if not nova_versao:
            self.status_var.set("Manifesto não encontrado para verificar atualizações.")
            return

        if not self._is_newer_version(nova_versao, self.VERSAO_ATUAL):
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
        baixado = self._baixar_arquivos_atualizacao(manifest, download_dir)
        if not baixado:
            self.status_var.set("Falha ao baixar arquivos de atualização.")
            return
        aplicado = self._aplicar_atualizacao(download_dir, manifest)
        if aplicado:
            self.status_var.set(
                "Atualização aplicada com sucesso. "
                f"Backup em: {backup_dir}"
            )
        else:
            self.status_var.set("Falha ao aplicar a atualização.")

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

    def _carregar_manifest_drive(self) -> dict:
        folder_id = self._extract_drive_folder_id()
        if not folder_id:
            return {}
        files = self._listar_arquivos_drive(folder_id)
        manifest = next((f for f in files if f["name"] == "manifest.json"), None)
        if not manifest:
            return {}
        content = self._download_drive_file(manifest["id"])
        if not content:
            return {}
        try:
            return json.loads(content)
        except Exception:
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

    def _extract_drive_folder_id(self) -> str | None:
        match = re.search(r"/folders/([a-zA-Z0-9_-]+)", self.SOURCE_URL)
        return match.group(1) if match else None

    def _listar_arquivos_drive(self, folder_id: str) -> list[dict]:
        url = f"https://drive.google.com/drive/folders/{folder_id}"
        try:
            with urllib.request.urlopen(url) as response:
                html = response.read().decode("utf-8", errors="ignore")
        except Exception:
            return []

        files = []
        pattern = re.compile(r'\\[\"([^\"]+?)\",\"([a-zA-Z0-9_-]{10,})\"\\]')
        for name, file_id in pattern.findall(html):
            if name.endswith(".py") or name == "manifest.json":
                files.append({"name": name, "id": file_id})
        return files

    def _download_drive_file(self, file_id: str) -> str | None:
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        try:
            with urllib.request.urlopen(url) as response:
                return response.read().decode("utf-8", errors="ignore")
        except Exception:
            return None

    def _baixar_arquivos_atualizacao(self, manifest: dict, download_dir: Path) -> bool:
        folder_id = self._extract_drive_folder_id()
        if not folder_id:
            return False

        files = []
        manifest_files = manifest.get("files") if isinstance(manifest, dict) else None
        if isinstance(manifest_files, list):
            for item in manifest_files:
                if isinstance(item, dict) and item.get("name"):
                    files.append({"name": item["name"], "id": item.get("id")})
                elif isinstance(item, str):
                    files.append({"name": item, "id": None})

        if not files:
            files = [f for f in self._listar_arquivos_drive(folder_id) if f["name"].endswith(".py")]

        if not files:
            return False

        ok = False
        for file_info in files:
            name = file_info.get("name")
            file_id = file_info.get("id")
            if not name or not name.endswith(".py"):
                continue
            if not file_id:
                match = next(
                    (f for f in self._listar_arquivos_drive(folder_id) if f["name"] == name),
                    None,
                )
                if not match:
                    continue
                file_id = match["id"]
            content = self._download_drive_file(file_id)
            if content is None:
                continue
            (download_dir / name).write_text(content, encoding="utf-8")
            ok = True
        return ok

    def _aplicar_atualizacao(self, download_dir: Path, manifest: dict) -> bool:
        try:
            arquivos = list(download_dir.glob("*.py"))
            if not arquivos:
                return False
            for file_path in arquivos:
                target = self.package_dir / file_path.name
                if not target.exists():
                    target = self.base_dir / file_path.name
                shutil.copy2(file_path, target)
            return True
        except Exception as exc:
            print(f"Erro ao aplicar atualização: {exc}")
            return False

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
