# -*- coding: utf-8 -*-
"""
ATUALIZADOR DO SISTEMA (LOCAL OU GOOGLE DRIVE) - UI CLARA + LINKS AUTOMÁTICOS
----------------------------------------------------------------------------
✅ Interface clara: você escolhe LOCAL ou ONLINE (Drive) e fica evidente de onde vem.
✅ Ao abrir a página: se houver atualização disponível (manifest com versão maior),
   aparece: "Nova atualização disponível: X.X — Deseja atualizar agora? (Sim/Não)"

✅ LOCAL:
   - Atualiza TODOS os arquivos .py que estiverem na pasta escolhida.

✅ ONLINE (Drive):
   - Você pode colar NO manifest o link normal do Drive (view) e o programa converte
     automaticamente para link de download.
   - Ex.: https://drive.google.com/file/d/ID/view?usp=sharing  ->  uc?export=download&id=ID
   - Recomendado: usar manifest.json com "files" e links do Drive (pode ser view mesmo).
   - Opcional: update_all=true + link de pasta /folders/... (tentativa, pode falhar às vezes).

Arquivos de estado:
- update_state.json     -> guarda versão atual
- update_settings.json  -> guarda modo + fonte local + fonte drive
"""

from __future__ import annotations

import json
import re
import shutil
import urllib.request
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk


class AtualizarSistemaPage(ctk.CTkFrame):
    VERSAO_PADRAO = "1.0"

    def __init__(self, master, sistema=None, app=None, parent=None, **kwargs):
        super().__init__(master, **kwargs)

        self.app = sistema or app or parent

        # Estrutura típica: este arquivo dentro de /PAGINAS -> base_dir = pasta do projeto
        self.base_dir = Path(__file__).resolve().parent.parent
        self.package_dir = Path(__file__).resolve().parent

        self.backup_root = self.base_dir / "backup_versoes"
        self.state_path = self.base_dir / "update_state.json"
        self.settings_path = self.base_dir / "update_settings.json"

        self.versao_atual = self._load_current_version()

        settings = self._load_settings()
        self.modo_var = ctk.StringVar(value=settings.get("mode", "local"))  # "local" ou "drive"
        self.local_source_var = ctk.StringVar(value=settings.get("local_source", ""))
        self.drive_source_var = ctk.StringVar(value=settings.get("drive_source", ""))

        self.version_var = ctk.StringVar(value=f"Versão atual: {self.versao_atual}")
        self.source_title_var = ctk.StringVar(value="")
        self.source_value_var = ctk.StringVar(value="")
        self.status_var = ctk.StringVar(value="Pronto.")

        self._build_ui()
        self._apply_mode_ui(initial=True)

        # Checagem automática ao abrir a página
        self.after(350, self._auto_check_updates_on_open)

    # ---------------- UI ----------------

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
            textvariable=self.version_var,
            font=("Segoe UI", 14),
        ).pack(anchor="w", padx=20, pady=(0, 12))

        # Seletor de modo
        modo_box = ctk.CTkFrame(self, corner_radius=12)
        modo_box.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            modo_box,
            text="Origem da atualização:",
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", padx=20, pady=(12, 6))

        row = ctk.CTkFrame(modo_box, corner_radius=12)
        row.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkRadioButton(
            row,
            text="Local (pasta do computador)",
            value="local",
            variable=self.modo_var,
            command=self._on_mode_changed,
        ).pack(side="left", padx=(0, 20), pady=6)

        ctk.CTkRadioButton(
            row,
            text="Online (Google Drive)",
            value="drive",
            variable=self.modo_var,
            command=self._on_mode_changed,
        ).pack(side="left", padx=(0, 20), pady=6)

        # Fonte conforme modo
        info = ctk.CTkFrame(self, corner_radius=12)
        info.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            info,
            textvariable=self.source_title_var,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", padx=20, pady=(12, 2))

        ctk.CTkLabel(
            info,
            textvariable=self.source_value_var,
            font=("Segoe UI", 12),
            wraplength=920,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 12))

        btn_row = ctk.CTkFrame(info, corner_radius=12)
        btn_row.pack(fill="x", padx=20, pady=(0, 12))
        self.btn_row = btn_row

        self.btn_local = ctk.CTkButton(
            btn_row,
            text="Escolher pasta local",
            command=self._alterar_fonte_local,
            width=220,
        )
        self.btn_drive = ctk.CTkButton(
            btn_row,
            text="Colar link do Drive",
            command=self._alterar_fonte_drive,
            width=220,
        )

        self.dica_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            info,
            textvariable=self.dica_var,
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

    # ---------------- Modo UI ----------------

    def _on_mode_changed(self):
        self._apply_mode_ui()
        self._save_settings()

    def _apply_mode_ui(self, initial: bool = False):
        mode = self.modo_var.get()

        for w in self.btn_row.winfo_children():
            w.pack_forget()

        if mode == "local":
            self.source_title_var.set("Fonte (LOCAL):")
            self.source_value_var.set(self.local_source_var.get() or "Nenhuma pasta selecionada.")
            self.dica_var.set("Atualiza todos os arquivos .py da pasta escolhida.")
            self.btn_local.pack(side="left", padx=(0, 12), pady=6)
        else:
            self.source_title_var.set("Fonte (ONLINE - Google Drive):")
            self.source_value_var.set(self.drive_source_var.get() or "Nenhum link informado.")
            self.dica_var.set(
                "Dica: você pode usar manifest.json com links normais do Drive (view) "
                "que o sistema converte automaticamente."
            )
            self.btn_drive.pack(side="left", padx=(0, 12), pady=6)

        if not initial:
            self.status_var.set("Pronto.")

    # ---------------- Checagem automática ao abrir ----------------

    def _auto_check_updates_on_open(self):
        try:
            mode = self.modo_var.get()

            if mode == "local":
                src = (self.local_source_var.get() or "").strip()
                if not src:
                    return
                p = Path(src)
                if not (p.exists() and p.is_dir()):
                    return
                manifest = self._load_manifest_local(p) or {}
            else:
                src = (self.drive_source_var.get() or "").strip()
                if not src:
                    return
                manifest = self._load_manifest_drive(src) or {}

            nova_versao = self._extract_version(manifest)
            if not nova_versao:
                return

            if self._is_newer_version(nova_versao, self.versao_atual):
                deseja = messagebox.askyesno(
                    "Atualização",
                    f"Nova atualização disponível: {nova_versao}\n\nDeseja atualizar agora?",
                )
                if deseja:
                    self._buscar_atualizacoes()
                else:
                    self.status_var.set("Atualização disponível. Você pode atualizar quando quiser.")
        except Exception:
            return

    # ---------------- Ações principais ----------------

    def _buscar_atualizacoes(self):
        mode = self.modo_var.get()

        if mode == "local":
            source = (self.local_source_var.get() or "").strip()
            if not source:
                messagebox.showwarning("Atualização", "Selecione uma pasta local primeiro.")
                return
            source_path = Path(source)
            if not (source_path.exists() and source_path.is_dir()):
                messagebox.showwarning("Atualização", "A pasta selecionada não é válida.")
                return

            self.status_var.set("Verificando atualizações...")
            manifest = self._load_manifest_local(source_path) or {}
            nova_versao = self._extract_version(manifest)

            if nova_versao and not self._is_newer_version(nova_versao, self.versao_atual):
                messagebox.showinfo("Atualização", "Nenhuma atualização disponível no momento.")
                self.status_var.set("Nenhuma atualização disponível.")
                return

            if nova_versao:
                deseja = messagebox.askyesno(
                    "Atualização",
                    f"Nova versão disponível: {nova_versao}\n\nDeseja atualizar agora?",
                )
                if not deseja:
                    self.status_var.set("Atualização cancelada.")
                    return
            else:
                deseja = messagebox.askyesno(
                    "Atualização",
                    "Deseja atualizar agora usando os arquivos desta pasta?",
                )
                if not deseja:
                    self.status_var.set("Atualização cancelada.")
                    return

            self._fazer_backup()

            self.status_var.set("Atualizando arquivos...")
            ok = self._aplicar_todos_py_da_pasta_local(source_path)

            if not ok:
                messagebox.showerror("Atualização", "Não encontrei arquivos .py nessa pasta para atualizar.")
                self.status_var.set("Não foi possível concluir a atualização.")
                return

            if nova_versao:
                self._set_versao_atual(nova_versao)

            messagebox.showinfo("Atualização", "Atualização concluída com sucesso!")
            self.status_var.set("Atualização concluída com sucesso.")
            return

        # Drive
        source = (self.drive_source_var.get() or "").strip()
        if not source:
            messagebox.showwarning("Atualização", "Cole um link do Google Drive primeiro.")
            return

        self.status_var.set("Verificando atualizações...")
        manifest = self._load_manifest_drive(source) or {}
        nova_versao = self._extract_version(manifest)

        if nova_versao and not self._is_newer_version(nova_versao, self.versao_atual):
            messagebox.showinfo("Atualização", "Nenhuma atualização disponível no momento.")
            self.status_var.set("Nenhuma atualização disponível.")
            return

        if nova_versao:
            deseja = messagebox.askyesno(
                "Atualização",
                f"Nova versão disponível: {nova_versao}\n\nDeseja atualizar agora?",
            )
            if not deseja:
                self.status_var.set("Atualização cancelada.")
                return
        else:
            deseja = messagebox.askyesno(
                "Atualização",
                "Deseja atualizar agora usando os arquivos desta fonte?",
            )
            if not deseja:
                self.status_var.set("Atualização cancelada.")
                return

        self._fazer_backup()

        self.status_var.set("Atualizando arquivos...")
        ok = self._aplicar_todos_py_da_fonte_drive(source, manifest)

        if not ok:
            messagebox.showerror(
                "Atualização",
                "Não foi possível atualizar pelo Drive.\n\n"
                "Verifique se:\n"
                "- O manifest.json está público (Qualquer pessoa com link)\n"
                "- Os arquivos do Drive estão públicos\n"
                "- Os links no manifest podem ser o link normal (view) que o sistema converte sozinho",
            )
            self.status_var.set("Não foi possível concluir a atualização.")
            return

        if nova_versao:
            self._set_versao_atual(nova_versao)

        messagebox.showinfo("Atualização", "Atualização concluída com sucesso!")
        self.status_var.set("Atualização concluída com sucesso.")

    def _restaurar_ultima_versao(self):
        if not self.backup_root.exists():
            messagebox.showinfo("Versões", "Nenhuma versão anterior encontrada.")
            self.status_var.set("Nenhuma versão anterior encontrada.")
            return

        backups = sorted([p for p in self.backup_root.iterdir() if p.is_dir()], reverse=True)
        if not backups:
            messagebox.showinfo("Versões", "Nenhuma versão anterior encontrada.")
            self.status_var.set("Nenhuma versão anterior encontrada.")
            return

        backup_dir = backups[0]
        versao_backup = self._read_backup_version(backup_dir) or "anterior"

        deseja = messagebox.askyesno("Voltar versão", f"Deseja voltar para versão {versao_backup}?")
        if not deseja:
            self.status_var.set("Ação cancelada.")
            return

        self.status_var.set("Voltando para a versão anterior...")
        restored = self._restore_backup(backup_dir)

        if restored:
            if versao_backup and versao_backup != "anterior":
                self._set_versao_atual(versao_backup)

            messagebox.showinfo("Voltar versão", f"Você voltou para a versão {versao_backup}.")
            self.status_var.set(f"Você voltou para a versão {versao_backup}.")
        else:
            messagebox.showerror("Voltar versão", "Não foi possível voltar para a versão anterior.")
            self.status_var.set("Não foi possível voltar para a versão anterior.")

    # ---------------- Fonte (Local/Drive) ----------------

    def _alterar_fonte_local(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta de atualizações (LOCAL)")
        if pasta:
            self.local_source_var.set(pasta)
            self._save_settings()
            self._apply_mode_ui()
            self.status_var.set("Pasta local selecionada.")

    def _alterar_fonte_drive(self):
        link = simpledialog.askstring(
            "Google Drive",
            "Cole o link do Drive (manifest.json ou pasta /folders/...):",
            initialvalue=self.drive_source_var.get(),
        )
        if link:
            self.drive_source_var.set(link.strip())
            self._save_settings()
            self._apply_mode_ui()
            self.status_var.set("Link do Drive definido.")

    # ---------------- Backup helpers ----------------

    def _fazer_backup(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._backup_current_version(timestamp, self.versao_atual)

    def _backup_current_version(self, timestamp: str, versao_atual: str) -> Path:
        backup_dir = self.backup_root / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        (backup_dir / "BACKUP_VERSION.txt").write_text(str(versao_atual), encoding="utf-8")

        backup_pkg = backup_dir / "PAGINAS_DO_SISTEMA"
        backup_pkg.mkdir(parents=True, exist_ok=True)

        for py_file in self.base_dir.glob("*.py"):
            try:
                shutil.copy2(py_file, backup_dir / py_file.name)
            except Exception:
                pass

        for py_file in self.package_dir.glob("*.py"):
            try:
                shutil.copy2(py_file, backup_pkg / py_file.name)
            except Exception:
                pass

        return backup_dir

    def _restore_backup(self, backup_dir: Path) -> bool:
        try:
            for py_file in backup_dir.glob("*.py"):
                shutil.copy2(py_file, self.base_dir / py_file.name)

            backup_pkg = backup_dir / "PAGINAS_DO_SISTEMA"
            if backup_pkg.exists():
                for py_file in backup_pkg.glob("*.py"):
                    shutil.copy2(py_file, self.package_dir / py_file.name)

            return True
        except Exception:
            return False

    def _read_backup_version(self, backup_dir: Path) -> str | None:
        p = backup_dir / "BACKUP_VERSION.txt"
        if p.exists():
            try:
                return p.read_text(encoding="utf-8").strip() or None
            except Exception:
                return None
        return None

    # ---------------- Versão atual (state) ----------------

    def _set_versao_atual(self, versao: str):
        self.versao_atual = str(versao).strip() or self.VERSAO_PADRAO
        self._save_current_version(self.versao_atual)
        self.version_var.set(f"Versão atual: {self.versao_atual}")

    def _load_current_version(self) -> str:
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                v = str(data.get("current_version", "")).strip()
                if v:
                    return v
            except Exception:
                pass
        return self.VERSAO_PADRAO

    def _save_current_version(self, versao: str):
        try:
            self.state_path.write_text(
                json.dumps({"current_version": str(versao)}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ---------------- Manifest (Local/Drive) ----------------

    def _load_manifest_local(self, source_dir: Path) -> dict | None:
        manifest_path = source_dir / "manifest.json"
        if not manifest_path.exists():
            return None
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _load_manifest_drive(self, source: str) -> dict | None:
        # Se o usuário colar o link normal do Drive do manifest.json, converte para download
        source = self._normalize_drive_url(source)

        # Link direto do manifest.json (ou qualquer url que retorne json)
        if source.lower().endswith(".json") or "uc?export=download" in source or "/file/d/" in source:
            txt = self._download_text(source)
            if not txt:
                return None
            try:
                return json.loads(txt)
            except Exception:
                return None

        # Pasta do Drive (/folders/...) tentativa
        folder_id = self._extract_drive_folder_id(source)
        if not folder_id:
            return None

        files = self._listar_arquivos_drive(folder_id)
        mf = next((f for f in files if f.get("name") == "manifest.json" and f.get("id")), None)
        if not mf:
            return None

        txt = self._download_drive_file(mf["id"])
        if not txt:
            return None

        try:
            return json.loads(txt)
        except Exception:
            return None

    def _extract_version(self, manifest: dict) -> str | None:
        if not isinstance(manifest, dict):
            return None
        for key in ("version", "versao", "versão"):
            v = manifest.get(key)
            if v:
                return str(v).strip()
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

    # ---------------- Aplicar Local ----------------

    def _aplicar_todos_py_da_pasta_local(self, source_dir: Path) -> bool:
        arquivos = list(source_dir.glob("*.py"))
        if not arquivos:
            return False

        ok = False
        for file_path in arquivos:
            ok = self._apply_one_py(file_path) or ok
        return ok

    # ---------------- Aplicar Drive ----------------

    def _aplicar_todos_py_da_fonte_drive(self, source_url: str, manifest: dict) -> bool:
        ok = False

        # 1) Por URLs no manifest (mais confiável)
        files = None
        if isinstance(manifest, dict):
            files = manifest.get("files") or manifest.get("arquivos")

        if isinstance(files, list) and files:
            ok = self._apply_from_manifest_urls(files) or ok

        # 2) Se update_all=true (ou se não conseguiu nada), tenta baixar tudo da pasta
        update_all = False
        if isinstance(manifest, dict):
            update_all = bool(manifest.get("update_all", False))

        if update_all or not ok:
            folder_id = self._extract_drive_folder_id(source_url)
            if folder_id:
                ok = self._apply_all_py_from_drive_folder(folder_id) or ok

        return ok

    def _apply_from_manifest_urls(self, items: list) -> bool:
        ok = False
        for item in items:
            if not isinstance(item, dict):
                continue

            name = item.get("name") or item.get("destino_relativo")
            url = item.get("url")
            if not name or not url:
                continue

            # ✅ Aceita link normal do Drive e converte automaticamente
            url = self._normalize_drive_url(url)

            content = self._download_text(url)
            if content is None:
                continue

            tmp = self._tmp_dir() / Path(name).name
            tmp.parent.mkdir(parents=True, exist_ok=True)
            try:
                tmp.write_text(content, encoding="utf-8")
            except Exception:
                continue

            ok = self._apply_one_py(tmp) or ok
        return ok

    def _apply_all_py_from_drive_folder(self, folder_id: str) -> bool:
        files = self._listar_arquivos_drive(folder_id)
        py_files = [f for f in files if f.get("name", "").endswith(".py") and f.get("id")]
        if not py_files:
            return False

        ok = False
        for f in py_files:
            content = self._download_drive_file(f["id"])
            if content is None:
                continue

            tmp = self._tmp_dir() / f["name"]
            tmp.parent.mkdir(parents=True, exist_ok=True)
            try:
                tmp.write_text(content, encoding="utf-8")
            except Exception:
                continue

            ok = self._apply_one_py(tmp) or ok

        return ok

    # ---------------- Aplicar 1 arquivo ----------------

    def _apply_one_py(self, file_path: Path) -> bool:
        if not file_path.exists() or file_path.suffix.lower() != ".py":
            return False

        target = self.package_dir / file_path.name
        if not target.exists():
            target = self.base_dir / file_path.name

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, target)
            return True
        except Exception:
            return False

    # ---------------- Drive helpers ----------------

    def _normalize_drive_url(self, url: str) -> str:
        """
        Converte links comuns do Google Drive em link direto de download.
        Você pode colar no manifest o link normal (view) que isso funciona.
        """
        u = (url or "").strip()
        if not u:
            return u

        # Já é o formato direto
        if "drive.google.com/uc?" in u and "id=" in u:
            return u

        # Formato: https://drive.google.com/file/d/<ID>/view?...
        m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", u)
        if m:
            file_id = m.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"

        # Formato: https://drive.google.com/open?id=<ID>
        m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", u)
        if m:
            file_id = m.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"

        # Formato com /uc?id=<ID>&export=download (também funciona)
        # Se tiver id=..., usa
        m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", u)
        if m and "drive.google.com" in u:
            file_id = m.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"

        return u

    def _extract_drive_folder_id(self, source: str) -> str | None:
        m = re.search(r"/folders/([a-zA-Z0-9_-]+)", source or "")
        return m.group(1) if m else None

    def _download_text(self, url: str) -> str | None:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as r:
                return r.read().decode("utf-8", errors="ignore")
        except Exception:
            return None

    def _listar_arquivos_drive(self, folder_id: str) -> list[dict]:
        url = f"https://drive.google.com/drive/folders/{folder_id}"
        html = self._download_text(url)
        if not html:
            return []

        files = []
        pattern = re.compile(r'\\[\"([^\"]+?)\",\"([a-zA-Z0-9_-]{10,})\"\\]')
        for name, file_id in pattern.findall(html):
            if name.endswith(".py") or name == "manifest.json":
                files.append({"name": name, "id": file_id})
        return files

    def _download_drive_file(self, file_id: str) -> str | None:
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        return self._download_text(url)

    def _tmp_dir(self) -> Path:
        p = self.base_dir / "__tmp_update__"
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ---------------- Settings ----------------

    def _load_settings(self) -> dict:
        if self.settings_path.exists():
            try:
                return json.loads(self.settings_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_settings(self):
        data = {
            "mode": self.modo_var.get(),
            "local_source": self.local_source_var.get(),
            "drive_source": self.drive_source_var.get(),
        }
        try:
            self.settings_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass


# ---------------- IFNAME - TESTE ISOLADO ----------------
if __name__ == "__main__":
    ctk.set_appearance_mode("light")  # ou "dark"
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Teste - Atualizar Sistema")
    root.geometry("1100x750")

    page = AtualizarSistemaPage(root)
    page.pack(fill="both", expand=True)

    root.mainloop()
