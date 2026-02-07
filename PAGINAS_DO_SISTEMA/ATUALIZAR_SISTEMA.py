import hashlib
import json
import re
import shutil
import urllib.request
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk


class AtualizarSistemaPage(ctk.CTkFrame):
    VERSAO_ATUAL = "1.0"
    DEFAULT_SOURCE = (
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
        self.settings_path = self.base_dir / "update_settings.json"
        self.source_var = ctk.StringVar(value=self._load_source())
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
            text="Fonte de atualização (online ou local):",
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", padx=20, pady=(12, 2))

        ctk.CTkLabel(
            info,
            textvariable=self.source_var,
            font=("Segoe UI", 12),
            wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 12))

        source_actions = ctk.CTkFrame(info, corner_radius=12)
        source_actions.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkButton(
            source_actions,
            text="Alterar fonte (URL/Drive)",
            command=self._alterar_fonte_url,
            width=200,
        ).pack(side="left", padx=(0, 12), pady=6)

        ctk.CTkButton(
            source_actions,
            text="Escolher pasta local",
            command=self._alterar_fonte_local,
            width=200,
        ).pack(side="left", padx=(0, 12), pady=6)

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
        source = self._get_source()
        manifest = self._carregar_manifest_local(source)
        if not manifest:
            manifest = self._carregar_manifest_drive(source)
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
            f"Fonte: {source}\n"
            f"Versão detectada: {nova_versao}\n"
            "Baixe os arquivos .py e coloque nesta pasta para aplicar.\n",
            encoding="utf-8",
        )
        self._append_history(
            action="buscar_atualizacoes",
            backup_dir=backup_dir,
            download_dir=download_dir,
            source_url=source,
        )
        baixado = self._baixar_arquivos_atualizacao(manifest, download_dir, source)
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
                source_url=self._get_source(),
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

    def _carregar_manifest_local(self, source: str) -> dict:
        if source:
            source_path = Path(source)
            if source_path.exists() and source_path.is_file() and source_path.suffix == ".json":
                try:
                    return json.loads(source_path.read_text(encoding="utf-8"))
                except Exception:
                    return {}
        candidates = [
            self.base_dir / "manifest.json",
            self.base_dir / "update_manifest.json",
            self.download_root / "manifest.json",
        ]
        if source and Path(source).exists():
            candidates.insert(0, Path(source) / "manifest.json")
        for path in candidates:
            if not path.exists():
                continue
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
        return {}

    def _carregar_manifest_drive(self, source: str) -> dict:
        if source and source.lower().endswith(".json"):
            content = self._download_url(source)
            if content:
                try:
                    return json.loads(content)
                except Exception:
                    return {}
        folder_id = self._extract_drive_folder_id(source)
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

    def _extract_drive_folder_id(self, source: str) -> str | None:
        match = re.search(r"/folders/([a-zA-Z0-9_-]+)", source or "")
        return match.group(1) if match else None

    def _listar_arquivos_drive(self, folder_id: str) -> list[dict]:
        url = f"https://drive.google.com/drive/folders/{folder_id}"
        try:
            with urllib.request.urlopen(self._request(url)) as response:
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
            with urllib.request.urlopen(self._request(url)) as response:
                return response.read().decode("utf-8", errors="ignore")
        except Exception:
            return None

    def _baixar_arquivos_atualizacao(self, manifest: dict, download_dir: Path, source: str) -> bool:
        if source and Path(source).exists():
            return self._copiar_arquivos_locais(manifest, Path(source), download_dir)

        folder_id = self._extract_drive_folder_id(source)
        if not folder_id:
            return False

        files = []
        manifest_files = None
        if isinstance(manifest, dict):
            manifest_files = manifest.get("files") or manifest.get("arquivos")
        if isinstance(manifest_files, list):
            for item in manifest_files:
                if isinstance(item, dict):
                    if item.get("name"):
                        files.append({"name": item["name"], "id": item.get("id")})
                    elif item.get("destino_relativo"):
                        files.append({
                            "destino_relativo": item.get("destino_relativo"),
                            "url": item.get("url"),
                            "sha256": item.get("sha256"),
                        })
                elif isinstance(item, str):
                    files.append({"name": item, "id": None})

        if not files:
            files = [f for f in self._listar_arquivos_drive(folder_id) if f["name"].endswith(".py")]

        if not files:
            return False

        ok = False
        for file_info in files:
            if file_info.get("destino_relativo") and file_info.get("url"):
                destino_relativo = file_info.get("destino_relativo")
                content = self._download_url(file_info["url"])
                if content is None:
                    continue
                if file_info.get("sha256") and not self._validate_sha256(content, file_info["sha256"]):
                    continue
                target_path = download_dir / Path(destino_relativo).name
                target_path.write_text(content, encoding="utf-8")
                ok = True
                continue

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

    def _copiar_arquivos_locais(self, manifest: dict, source_dir: Path, download_dir: Path) -> bool:
        files = []
        manifest_files = None
        if isinstance(manifest, dict):
            manifest_files = manifest.get("files") or manifest.get("arquivos")
        if isinstance(manifest_files, list):
            for item in manifest_files:
                if isinstance(item, dict):
                    if item.get("name"):
                        files.append(item["name"])
                    elif item.get("destino_relativo"):
                        files.append(item["destino_relativo"])
                elif isinstance(item, str):
                    files.append(item)

        if not files:
            files = [p.name for p in source_dir.glob("*.py")]

        ok = False
        for name in files:
            file_name = Path(name).name
            if not file_name.endswith(".py"):
                continue
            source_file = source_dir / file_name
            if not source_file.exists():
                continue
            shutil.copy2(source_file, download_dir / file_name)
            ok = True
        return ok

    def _aplicar_atualizacao(self, download_dir: Path, manifest: dict) -> bool:
        try:
            manifest_files = None
            if isinstance(manifest, dict):
                manifest_files = manifest.get("files") or manifest.get("arquivos")

            if isinstance(manifest_files, list) and manifest_files:
                for item in manifest_files:
                    destino = None
                    if isinstance(item, dict):
                        destino = item.get("destino_relativo") or item.get("name")
                    elif isinstance(item, str):
                        destino = item
                    if not destino:
                        continue
                    file_name = Path(destino).name
                    source = download_dir / file_name
                    if not source.exists():
                        continue
                    target = self.package_dir / destino
                    if not target.exists():
                        target = self.base_dir / destino
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                return True

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

    def _download_url(self, url: str) -> str | None:
        try:
            with urllib.request.urlopen(self._request(url)) as response:
                return response.read().decode("utf-8", errors="ignore")
        except Exception:
            return None

    @staticmethod
    def _request(url: str) -> urllib.request.Request:
        return urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
        )

    def _validate_sha256(self, content: str, expected: str) -> bool:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return digest.lower() == expected.lower()

    def _alterar_fonte_url(self):
        fonte = simpledialog.askstring(
            "Fonte de atualização",
            "Informe a URL/pasta do Drive:",
            initialvalue=self.source_var.get(),
        )
        if fonte:
            self._set_source(fonte.strip())

    def _alterar_fonte_local(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta de atualizações")
        if pasta:
            self._set_source(pasta)

    def _load_source(self) -> str:
        if self.settings_path.exists():
            try:
                data = json.loads(self.settings_path.read_text(encoding="utf-8"))
                return str(data.get("source", self.DEFAULT_SOURCE))
            except Exception:
                return self.DEFAULT_SOURCE
        return self.DEFAULT_SOURCE

    def _get_source(self) -> str:
        return self.source_var.get() or self.DEFAULT_SOURCE

    def _set_source(self, value: str):
        self.source_var.set(value)
        try:
            self.settings_path.write_text(
                json.dumps({"source": value}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

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
