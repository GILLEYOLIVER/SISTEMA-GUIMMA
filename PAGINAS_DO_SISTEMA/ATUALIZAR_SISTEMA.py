# -*- coding: utf-8 -*-
from __future__ import annotations

from PAGINAS_DO_SISTEMA.TEMAS import BotaoPadronizado

import json
import re
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import customtkinter as ctk


class AtualizarSistemaPage(ctk.CTkFrame):
    VERSAO_PADRAO = '1.0'

    TEXTOS_I18N = {
        'pt_BR': {
            'title': 'Atualizar Sistema',
            'current_version': 'Versão atual: {versao}',
            'ready': 'Pronto.',
            'source': 'Origem da atualização:',
            'local_mode': 'Local (pasta do computador)',
            'drive_mode': 'Online (Google Drive ZIP)',
            'choose_local_folder': 'Escolher pasta local',
            'paste_drive_link': 'Colar link do Drive',
            'scan': 'Buscar pacote',
            'install': 'Instalar pacote',
            'restore': 'Restaurar último backup',
            'package_files': 'Conteúdo do pacote',
            'no_scan': 'Nenhuma varredura realizada.',
            'local_selected': 'Pasta local selecionada.',
            'drive_selected': 'Link do Drive definido.',
            'invalid_package': 'Pacote inválido.',
            'download': 'Baixando pacote online...',
            'extract': 'Extraindo pacote...',
            'launching_updater': 'Encerrando o sistema e iniciando o atualizador externo...',
            'updater_not_found': 'Arquivo OPERA_UPDATER.py não encontrado na raiz do projeto.',
            'restore_confirm': 'Deseja restaurar o último backup disponível?',
            'install_confirm': 'Deseja instalar o pacote selecionado?\n\nVersão: {versao}',
            'restored': 'O restaurador externo foi iniciado. Abra o sistema novamente após a conclusão.',
            'updater_started': 'O atualizador externo foi iniciado. Feche e abra o sistema novamente após a conclusão.',
        },
        'en_US': {
            'title': 'Update System',
            'current_version': 'Current version: {versao}',
            'ready': 'Ready.',
            'source': 'Update source:',
            'local_mode': 'Local (computer folder)',
            'drive_mode': 'Online (Google Drive ZIP)',
            'choose_local_folder': 'Choose local folder',
            'paste_drive_link': 'Paste Drive link',
            'scan': 'Scan package',
            'install': 'Install package',
            'restore': 'Restore latest backup',
            'package_files': 'Package content',
            'no_scan': 'No scan performed.',
            'local_selected': 'Local folder selected.',
            'drive_selected': 'Drive link set.',
            'invalid_package': 'Invalid package.',
            'download': 'Downloading online package...',
            'extract': 'Extracting package...',
            'launching_updater': 'Closing the system and starting the external updater...',
            'updater_not_found': 'OPERA_UPDATER.py was not found in the project root.',
            'restore_confirm': 'Do you want to restore the latest available backup?',
            'install_confirm': 'Do you want to install the selected package?\n\nVersion: {versao}',
            'restored': 'The external restore was started. Open the system again after it finishes.',
            'updater_started': 'The external updater was started. Close and open the system again after it finishes.',
        },
        'es_ES': {
            'title': 'Actualizar Sistema',
            'current_version': 'Versión actual: {versao}',
            'ready': 'Listo.',
            'source': 'Origen de la actualización:',
            'local_mode': 'Local (carpeta del equipo)',
            'drive_mode': 'En línea (Google Drive ZIP)',
            'choose_local_folder': 'Elegir carpeta local',
            'paste_drive_link': 'Pegar enlace de Drive',
            'scan': 'Buscar paquete',
            'install': 'Instalar paquete',
            'restore': 'Restaurar último respaldo',
            'package_files': 'Contenido del paquete',
            'no_scan': 'No se realizó ningún análisis.',
            'local_selected': 'Carpeta local seleccionada.',
            'drive_selected': 'Enlace de Drive definido.',
            'invalid_package': 'Paquete inválido.',
            'download': 'Descargando paquete...',
            'extract': 'Extrayendo paquete...',
            'launching_updater': 'Cerrando el sistema e iniciando el actualizador externo...',
            'updater_not_found': 'No se encontró OPERA_UPDATER.py en la raíz del proyecto.',
            'restore_confirm': '¿Desea restaurar el último respaldo disponible?',
            'install_confirm': '¿Desea instalar el paquete seleccionado?\n\nVersión: {versao}',
            'restored': 'La restauración externa fue iniciada. Abra el sistema nuevamente al finalizar.',
            'updater_started': 'El actualizador externo fue iniciado. Cierre y abra el sistema nuevamente al finalizar.',
        },
    }

    def __init__(self, master, sistema=None, app=None, parent=None, **kwargs):
        super().__init__(master, **kwargs)
        self.app = sistema or app or parent
        self.package_dir = Path(__file__).resolve().parent
        self.base_dir = self.package_dir.parent
        self.state_path = self.base_dir / 'update_state.json'
        self.settings_path = self.base_dir / 'update_settings.json'
        self.versao_atual = self._load_current_version()
        settings = self._load_settings()
        self.modo_var = ctk.StringVar(value=settings.get('mode', 'local'))
        self.local_source_var = ctk.StringVar(value=settings.get('local_source', ''))
        self.drive_source_var = ctk.StringVar(value=settings.get('drive_source', ''))
        self.version_var = ctk.StringVar(value=self._get_text('current_version', versao=self.versao_atual))
        self.status_var = ctk.StringVar(value=self._get_text('ready'))
        self.source_title_var = ctk.StringVar(value='')
        self.source_value_var = ctk.StringVar(value='')
        self.scan_summary_var = ctk.StringVar(value=self._get_text('no_scan'))
        self.current_scan_root: Path | None = None
        self.current_manifest: dict = {}
        self.current_temp_root: Path | None = None
        self._ui_refs = {}
        self._build_ui()
        self._apply_mode_ui(initial=True)
        self.after(200, self._auto_scan_on_open)

    def _get_idioma_atual(self):
        origem = getattr(self, 'app', None)
        return getattr(origem, 'idioma_atual', 'pt_BR') if origem else 'pt_BR'

    def _get_text(self, chave, **kwargs):
        idioma = self._get_idioma_atual()
        base = self.TEXTOS_I18N.get(idioma) or self.TEXTOS_I18N['pt_BR']
        valor = base.get(chave) or self.TEXTOS_I18N['pt_BR'].get(chave) or chave
        try:
            return valor.format(**kwargs)
        except Exception:
            return valor

    def refresh_texts(self):
        self.version_var.set(self._get_text('current_version', versao=self.versao_atual))
        mapping = {
            'title': 'title', 'mode': 'source', 'local': 'local_mode', 'drive': 'drive_mode',
            'btn_local': 'choose_local_folder', 'btn_drive': 'paste_drive_link',
            'btn_scan': 'scan', 'btn_install': 'install', 'btn_restore': 'restore', 'results': 'package_files'
        }
        for ref, key in mapping.items():
            widget = self._ui_refs.get(ref)
            if widget:
                widget.configure(text=self._get_text(key))
        self._apply_mode_ui(initial=True)

    def _build_ui(self):
        self.configure(fg_color='transparent')
        header = ctk.CTkFrame(self, corner_radius=12)
        header.pack(fill='x', padx=20, pady=(20, 10))
        self._ui_refs['title'] = ctk.CTkLabel(header, text=self._get_text('title'), font=('Segoe UI', 22, 'bold'))
        self._ui_refs['title'].pack(anchor='w', padx=20, pady=(16, 4))
        ctk.CTkLabel(header, textvariable=self.version_var, font=('Segoe UI', 14)).pack(anchor='w', padx=20, pady=(0, 12))

        mode_box = ctk.CTkFrame(self, corner_radius=12)
        mode_box.pack(fill='x', padx=20, pady=10)
        self._ui_refs['mode'] = ctk.CTkLabel(mode_box, text=self._get_text('source'), font=('Segoe UI', 13, 'bold'))
        self._ui_refs['mode'].pack(anchor='w', padx=20, pady=(12, 6))
        row = ctk.CTkFrame(mode_box, corner_radius=12)
        row.pack(fill='x', padx=20, pady=(0, 12))
        self._ui_refs['local'] = ctk.CTkRadioButton(row, text=self._get_text('local_mode'), value='local', variable=self.modo_var, command=self._on_mode_changed)
        self._ui_refs['local'].pack(side='left', padx=(0, 20), pady=6)
        self._ui_refs['drive'] = ctk.CTkRadioButton(row, text=self._get_text('drive_mode'), value='drive', variable=self.modo_var, command=self._on_mode_changed)
        self._ui_refs['drive'].pack(side='left', padx=(0, 20), pady=6)

        info = ctk.CTkFrame(self, corner_radius=12)
        info.pack(fill='x', padx=20, pady=10)
        ctk.CTkLabel(info, textvariable=self.source_title_var, font=('Segoe UI', 13, 'bold')).pack(anchor='w', padx=20, pady=(12, 2))
        ctk.CTkLabel(info, textvariable=self.source_value_var, font=('Segoe UI', 12), wraplength=980, justify='left').pack(anchor='w', padx=20, pady=(0, 12))
        self.btn_row = ctk.CTkFrame(info, corner_radius=12)
        self.btn_row.pack(fill='x', padx=20, pady=(0, 12))
        self.btn_local = BotaoPadronizado.criar_botao(self.btn_row, text=self._get_text('choose_local_folder'), command=self._alterar_fonte_local, width=240)
        self.btn_drive = BotaoPadronizado.criar_botao(self.btn_row, text=self._get_text('paste_drive_link'), command=self._alterar_fonte_drive, width=240)
        self._ui_refs['btn_local'] = self.btn_local
        self._ui_refs['btn_drive'] = self.btn_drive

        actions = ctk.CTkFrame(self, corner_radius=12)
        actions.pack(fill='x', padx=20, pady=10)
        self._ui_refs['btn_scan'] = BotaoPadronizado.criar_botao(actions, text=self._get_text('scan'), command=self._scan_current_source, width=220)
        self._ui_refs['btn_scan'].pack(side='left', padx=20, pady=16)
        self._ui_refs['btn_install'] = BotaoPadronizado.criar_botao(actions, text=self._get_text('install'), command=self._install_package, width=220)
        self._ui_refs['btn_install'].pack(side='left', padx=(0, 20), pady=16)
        self._ui_refs['btn_restore'] = BotaoPadronizado.criar_botao(actions, text=self._get_text('restore'), command=self._restore_latest_backup, width=260)
        self._ui_refs['btn_restore'].pack(side='left', padx=(0, 20), pady=16)

        results = ctk.CTkFrame(self, corner_radius=12)
        results.pack(fill='both', expand=True, padx=20, pady=10)
        self._ui_refs['results'] = ctk.CTkLabel(results, text=self._get_text('package_files'), font=('Segoe UI', 13, 'bold'))
        self._ui_refs['results'].pack(anchor='w', padx=20, pady=(12, 8))

        wrap = ctk.CTkFrame(results, corner_radius=8)
        wrap.pack(fill='both', expand=True, padx=20, pady=(0, 8))
        self.tree = ttk.Treeview(wrap, columns=('tipo', 'rel'), show='tree headings', height=14)
        self.tree.heading('#0', text='Nome')
        self.tree.heading('tipo', text='Tipo')
        self.tree.heading('rel', text='Relativo')
        self.tree.column('#0', width=320, anchor='w')
        self.tree.column('tipo', width=120, anchor='center')
        self.tree.column('rel', width=650, anchor='w')
        self.tree.pack(fill='both', expand=True, side='left')
        scroll = ttk.Scrollbar(wrap, orient='vertical', command=self.tree.yview)
        scroll.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scroll.set)
        ctk.CTkLabel(results, textvariable=self.scan_summary_var, font=('Segoe UI', 12), justify='left').pack(anchor='w', padx=20, pady=(0, 12))
        ctk.CTkLabel(self, textvariable=self.status_var, font=('Segoe UI', 12)).pack(fill='x', padx=20, pady=(6, 0))

    def _load_settings(self) -> dict:
        try:
            return json.loads(self.settings_path.read_text(encoding='utf-8')) if self.settings_path.exists() else {}
        except Exception:
            return {}

    def _save_settings(self):
        data = {'mode': self.modo_var.get(), 'local_source': self.local_source_var.get(), 'drive_source': self.drive_source_var.get()}
        try:
            self.settings_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass

    def _load_current_version(self) -> str:
        try:
            if self.state_path.exists():
                data = json.loads(self.state_path.read_text(encoding='utf-8'))
                return str(data.get('current_version') or self.VERSAO_PADRAO)
        except Exception:
            pass
        return self.VERSAO_PADRAO

    def _auto_scan_on_open(self):
        if self.modo_var.get() == 'local' and self.local_source_var.get().strip():
            self._scan_current_source()
        elif self.modo_var.get() == 'drive' and self.drive_source_var.get().strip():
            self._scan_current_source()

    def _on_mode_changed(self):
        self._apply_mode_ui()
        self._save_settings()

    def _apply_mode_ui(self, initial=False):
        for w in self.btn_row.winfo_children():
            w.pack_forget()
        if self.modo_var.get() == 'local':
            self.source_title_var.set('Fonte (LOCAL):')
            self.source_value_var.set(self.local_source_var.get() or '-')
            self.btn_local.pack(side='left', padx=(0, 12), pady=6)
        else:
            self.source_title_var.set('Fonte (ONLINE - Google Drive ZIP):')
            self.source_value_var.set(self.drive_source_var.get() or '-')
            self.btn_drive.pack(side='left', padx=(0, 12), pady=6)
        if not initial:
            self.scan_summary_var.set(self._get_text('no_scan'))
            self._clear_tree()
            self.status_var.set(self._get_text('ready'))

    def _alterar_fonte_local(self):
        pasta = filedialog.askdirectory(title='Selecione a pasta de atualização')
        if pasta:
            self.local_source_var.set(pasta)
            self.source_value_var.set(pasta)
            self._save_settings()
            self.status_var.set(self._get_text('local_selected'))
            self._scan_current_source()

    def _alterar_fonte_drive(self):
        link = simpledialog.askstring('Google Drive', 'Cole o link do Drive (arquivo ZIP):', initialvalue=self.drive_source_var.get())
        if link:
            self.drive_source_var.set(link.strip())
            self.source_value_var.set(link.strip())
            self._save_settings()
            self.status_var.set(self._get_text('drive_selected'))
            self._scan_current_source()

    def _normalize_drive_url(self, url: str) -> str:
        u = (url or '').strip()
        if 'drive.google.com/uc?' in u and 'id=' in u:
            return u
        m = re.search(r'/file/d/([a-zA-Z0-9_-]+)', u)
        if m:
            return f'https://drive.google.com/uc?export=download&id={m.group(1)}'
        m = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', u)
        if m:
            return f'https://drive.google.com/uc?export=download&id={m.group(1)}'
        return u

    def _download_binary(self, url: str, target_path: Path):
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            target_path.write_bytes(response.read())

    def _prepare_source_for_scan(self) -> Path | None:
        if self.modo_var.get() == 'local':
            src = Path((self.local_source_var.get() or '').strip())
            return src if src.exists() and src.is_dir() else None
        url = (self.drive_source_var.get() or '').strip()
        if not url:
            return None
        tmp_root = Path(tempfile.mkdtemp(prefix='opera_release_'))
        self.current_temp_root = tmp_root
        zip_path = tmp_root / 'release.zip'
        self.status_var.set(self._get_text('download'))
        self._download_binary(self._normalize_drive_url(url), zip_path)
        extract_dir = tmp_root / 'package'
        extract_dir.mkdir(parents=True, exist_ok=True)
        self.status_var.set(self._get_text('extract'))
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
        for candidate in [extract_dir] + [p for p in extract_dir.iterdir() if p.is_dir()]:
            if (candidate / 'manifest.json').exists() or (candidate / 'APP').exists() or (candidate / 'PAGINAS_DO_SISTEMA').exists():
                return candidate
        return None

    def _scan_current_source(self):
        self._clear_tree()
        scan_root = self._prepare_source_for_scan()
        if scan_root is None:
            self.current_scan_root = None
            self.current_manifest = {}
            self.scan_summary_var.set(self._get_text('invalid_package'))
            self.status_var.set(self._get_text('invalid_package'))
            return
        self.current_scan_root = scan_root
        self.current_manifest = self._load_manifest_local(scan_root) or {}
        self._populate_tree_from_scan(scan_root)

    def _populate_tree_from_scan(self, root: Path):
        app_root = root / 'APP' if (root / 'APP').exists() else root
        total = 0
        for rel in ['PAGINAS_DO_SISTEMA', 'SCHEMA', 'MIGRATIONS']:
            folder = app_root / rel if rel != 'MIGRATIONS' else root / rel
            if folder.exists() and folder.is_dir():
                node = self.tree.insert('', 'end', text=rel, values=('PASTA', rel), open=True)
                for file_path in sorted(folder.rglob('*')):
                    if file_path.is_file() and file_path.suffix.lower() in {'.py', '.sql', '.json', '.txt'}:
                        shown_rel = file_path.relative_to(root).as_posix()
                        self.tree.insert(node, 'end', text=file_path.name, values=('ARQUIVO', shown_rel))
                        total += 1
        version = str(self.current_manifest.get('version') or self.current_manifest.get('versao') or 'não informada')
        notes = self.current_manifest.get('notes') or []
        if isinstance(notes, str):
            notes = [notes]
        lines = [f'Arquivos detectados: {total}', f'Versão do pacote: {version}']
        if notes:
            lines.append('Observações:')
            lines.extend([f'• {n}' for n in notes])
        self.scan_summary_var.set('\n'.join(lines))
        self.status_var.set(self._get_text('ready'))

    def _clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _load_manifest_local(self, source_dir: Path) -> dict | None:
        p = source_dir / 'manifest.json'
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            return None

    def _launch_external(self, args: list[str]):
        updater_path = self.base_dir / 'OPERA_UPDATER.py'
        if not updater_path.exists():
            messagebox.showerror('Atualização', self._get_text('updater_not_found'))
            return False
        try:
            subprocess.Popen([sys.executable, str(updater_path), *args], cwd=str(self.base_dir))
            return True
        except Exception as exc:
            messagebox.showerror('Atualização', f'Não foi possível iniciar o atualizador externo.\n\n{exc}')
            return False

    def _install_package(self):
        if self.current_scan_root is None:
            self._scan_current_source()
            if self.current_scan_root is None:
                return
        package_version = str(self.current_manifest.get('version') or self.current_manifest.get('versao') or 'não informada')
        if not messagebox.askyesno('Atualização', self._get_text('install_confirm', versao=package_version)):
            return
        self.status_var.set(self._get_text('launching_updater'))
        user_id = str(getattr(self.app, 'usuario_id', '') or '')
        user_name = str(getattr(self.app, 'usuario_nome', '') or '')
        ok = self._launch_external([
            '--apply', str(self.current_scan_root),
            '--app-root', str(self.base_dir),
            '--current-version', str(self.versao_atual),
            '--user-id', user_id,
            '--user-name', user_name,
        ])
        if ok:
            messagebox.showinfo('Atualização', self._get_text('updater_started'))
            try:
                self.app.destroy()
            except Exception:
                pass

    def _restore_latest_backup(self):
        if not messagebox.askyesno('Atualização', self._get_text('restore_confirm')):
            return
        ok = self._launch_external(['--restore-latest', '--app-root', str(self.base_dir)])
        if ok:
            messagebox.showinfo('Atualização', self._get_text('restored'))
            try:
                self.app.destroy()
            except Exception:
                pass


if __name__ == '__main__':
    ctk.set_appearance_mode('light')
    ctk.set_default_color_theme('blue')
    root = ctk.CTk()
    root.title('Teste - Atualizar Sistema')
    root.geometry('1200x840')
    page = AtualizarSistemaPage(root)
    page.pack(fill='both', expand=True)
    root.mainloop()
