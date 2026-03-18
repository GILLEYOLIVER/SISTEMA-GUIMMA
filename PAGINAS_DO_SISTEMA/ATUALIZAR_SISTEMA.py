# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
import json
import re
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, Menu, ttk

import customtkinter as ctk


class AtualizarSistemaPage(ctk.CTkFrame):
    VERSAO_PADRAO = "1.0"

    def __init__(self, master, sistema=None, app=None, parent=None, **kwargs):
        super().__init__(master, **kwargs)

        self.app = sistema or app or parent

        self.package_dir = Path(__file__).resolve().parent      # PAGINAS_DO_SISTEMA
        self.base_dir = self.package_dir.parent                 # raiz do projeto

        self.backup_root = self.base_dir / "backup_versoes"
        self.state_path = self.base_dir / "update_state.json"
        self.settings_path = self.base_dir / "update_settings.json"

        self.versao_atual = self._load_current_version()

        settings = self._load_settings()
        self.modo_var = ctk.StringVar(value=settings.get("mode", "local"))
        self.local_source_var = ctk.StringVar(value=settings.get("local_source", ""))
        self.drive_source_var = ctk.StringVar(value=settings.get("drive_source", ""))

        self.version_var = ctk.StringVar(value=self._get_text("current_version", versao=self.versao_atual))
        self.source_title_var = ctk.StringVar(value="")
        self.source_value_var = ctk.StringVar(value="")
        self.status_var = ctk.StringVar(value=self._get_text("ready"))

        self.current_scan_root: Path | None = None
        self.current_manifest: dict = {}
        self.current_temp_root: Path | None = None

        self._popup_target_kind = ""
        self._popup_target_rel = ""
        self._popup_target_name = ""
        self._ui_refs = {}

        self._build_ui()
        self._apply_mode_ui(initial=True)

        self.after(300, self._auto_scan_on_open)


    # =========================================================
    # Idioma
    # =========================================================
    TEXTOS_I18N = {'pt_BR': {'title': 'Atualizar Sistema', 'current_version': 'Versão atual: {versao}', 'ready': 'Pronto.', 'update_source': 'Origem da atualização:', 'local_mode': 'Local (pasta do computador)', 'online_mode': 'Online (Google Drive ZIP)', 'choose_local_folder': 'Escolher pasta local', 'paste_drive_link': 'Colar link do Drive', 'search_updates': '🔍 Buscar Atualizações', 'update_all': '🔄 Atualizar Tudo', 'restore_previous': '↩️ Voltar para versão anterior', 'files_in_package': 'Arquivos encontrados no pacote', 'tree_name': 'Nome', 'tree_type': 'Tipo', 'tree_source': 'Origem', 'tree_relative': 'Relativo', 'tree_kind': 'Kind', 'popup_update_selected': 'Atualizar item selecionado', 'no_scan': 'Nenhuma varredura realizada.', 'source_local_title': 'Fonte (LOCAL):', 'source_drive_title': 'Fonte (ONLINE - Google Drive ZIP):', 'no_folder_selected': 'Nenhuma pasta selecionada.', 'no_link_informed': 'Nenhum link informado.', 'local_hint': 'Selecione uma pasta com:\n• PAGINAS_DO_SISTEMA/ (opcional)\n• SCHEMA/ (opcional)\n• manifest.json (opcional)', 'drive_hint': 'Cole um link de arquivo ZIP do Google Drive.\nDentro do ZIP deve existir:\n• PAGINAS_DO_SISTEMA/\n• SCHEMA/\n• manifest.json (opcional)', 'local_folder_selected': 'Pasta local selecionada.', 'drive_link_set': 'Link do Drive definido.', 'scan_failed': 'Falha na varredura.', 'scan_error': 'Erro ao analisar o pacote: {erro}', 'no_local_source_selected': 'Nenhuma fonte local selecionada.', 'invalid_local_folder': 'A pasta selecionada não é válida.', 'no_online_source': 'Nenhuma fonte online informada.', 'invalid_package': 'Pacote inválido.', 'missing_pages_folder': 'Não foi encontrada a pasta PAGINAS_DO_SISTEMA.', 'missing_schema_folder': 'Não foi encontrada a pasta SCHEMA.', 'folder_pages': 'PAGINAS_DO_SISTEMA', 'folder_schema': 'SCHEMA', 'folder': 'PASTA', 'package': 'PACOTE', 'file': 'ARQUIVO', 'info': 'INFO', 'none_py_found': '(nenhum .py encontrado)', 'no_updates_found': 'Nenhuma atualização encontrada.', 'package_scanned_ok': 'Pacote analisado com sucesso.', 'summary_no_both': 'Não foram encontradas as pastas PAGINAS_DO_SISTEMA e SCHEMA.', 'summary_no_py': 'Nenhum arquivo .py de atualização foi encontrado.', 'summary_found_files': 'Foram encontrados {total} arquivo(s) de atualização.', 'summary_package_version': 'Versão do pacote: {version}', 'summary_description': 'Descrição: {description}', 'summary_created_at': 'Gerado em: {created_at}', 'summary_schema_yes': 'Atualização de banco: SIM', 'summary_schema_no': 'Atualização de banco: NÃO', 'summary_notes': 'Observações:', 'summary_double_click': 'Duplo clique em um arquivo para atualizar só ele.', 'summary_right_click': 'Clique com o botão direito em uma pasta para atualizar a pasta completa.', 'update_file': 'Atualizar arquivo', 'update_folder': 'Atualizar pasta', 'confirm_update_file': 'Deseja atualizar este arquivo?\n\n{rel}', 'confirm_update_folder': 'Deseja atualizar a pasta completa?\n\n{rel}', 'update_all_title': 'Atualizar Tudo', 'confirm_update_all': 'Deseja atualizar todo o pacote?\n\nVersão: {version}', 'not_informed': 'não informada', 'update_cancelled': 'Atualização cancelada.', 'updating': 'Atualizando: {source_label}...', 'warning_title': 'Atualização', 'no_package_scanned': 'Nenhum pacote analisado.', 'pages_not_updated': 'Nenhum arquivo de página foi atualizado.', 'schema_not_updated': 'Nenhum arquivo de schema foi atualizado.', 'pages_folder_not_found': 'A pasta PAGINAS_DO_SISTEMA não foi encontrada no pacote.', 'schema_folder_not_found': 'A pasta SCHEMA não foi encontrada no pacote.', 'applying_migrations': 'Aplicando migrações do banco...', 'migration_failed_restore': 'Falha na migração. Arquivos restaurados.', 'migration_failed_message': 'Os arquivos foram atualizados, mas a migração do banco falhou.\n\nO sistema restaurou automaticamente os arquivos do backup.\n\nDetalhes:\n{detalhes}', 'updated_pages': 'páginas', 'updated_schema': 'schema', 'updated_files': 'arquivos', 'update_completed': 'Atualização concluída: {source_label}', 'update_completed_message': 'Atualização concluída com sucesso:\n\n{source_label}\n\nItens atualizados: {tipo_txt}{versao_linha}\n\nFeche e reabra o sistema para carregar as alterações.', 'version_installed': '\nNova versão instalada: {version}', 'download_online_package': 'Baixando pacote online...', 'extracting_package': 'Extraindo pacote...', 'drive_download_failed': 'Não foi possível baixar o arquivo do Drive.', 'zip_structure_missing': 'O ZIP foi baixado, mas não encontrei a estrutura esperada.\nEsperado: PAGINAS_DO_SISTEMA/ e/ou SCHEMA/.'}, 'en_US': {'title': 'Update System', 'current_version': 'Current version: {versao}', 'ready': 'Ready.', 'update_source': 'Update source:', 'local_mode': 'Local (computer folder)', 'online_mode': 'Online (Google Drive ZIP)', 'choose_local_folder': 'Choose local folder', 'paste_drive_link': 'Paste Drive link', 'search_updates': '🔍 Check for Updates', 'update_all': '🔄 Update All', 'restore_previous': '↩️ Restore previous version', 'files_in_package': 'Files found in package', 'tree_name': 'Name', 'tree_type': 'Type', 'tree_source': 'Source', 'tree_relative': 'Relative', 'tree_kind': 'Kind', 'popup_update_selected': 'Update selected item', 'no_scan': 'No scan performed.', 'source_local_title': 'Source (LOCAL):', 'source_drive_title': 'Source (ONLINE - Google Drive ZIP):', 'no_folder_selected': 'No folder selected.', 'no_link_informed': 'No link provided.', 'local_hint': 'Select a folder containing:\n• PAGINAS_DO_SISTEMA/ (optional)\n• SCHEMA/ (optional)\n• manifest.json (optional)', 'drive_hint': 'Paste a Google Drive ZIP file link.\nThe ZIP should contain:\n• PAGINAS_DO_SISTEMA/\n• SCHEMA/\n• manifest.json (optional)', 'local_folder_selected': 'Local folder selected.', 'drive_link_set': 'Drive link set.', 'scan_failed': 'Scan failed.', 'scan_error': 'Error analyzing package: {erro}', 'no_local_source_selected': 'No local source selected.', 'invalid_local_folder': 'The selected folder is not valid.', 'no_online_source': 'No online source provided.', 'invalid_package': 'Invalid package.', 'missing_pages_folder': 'PAGINAS_DO_SISTEMA folder was not found.', 'missing_schema_folder': 'SCHEMA folder was not found.', 'folder_pages': 'PAGINAS_DO_SISTEMA', 'folder_schema': 'SCHEMA', 'folder': 'FOLDER', 'package': 'PACKAGE', 'file': 'FILE', 'info': 'INFO', 'none_py_found': '(no .py files found)', 'no_updates_found': 'No updates found.', 'package_scanned_ok': 'Package scanned successfully.', 'summary_no_both': 'PAGINAS_DO_SISTEMA and SCHEMA folders were not found.', 'summary_no_py': 'No .py update files were found.', 'summary_found_files': '{total} update file(s) were found.', 'summary_package_version': 'Package version: {version}', 'summary_description': 'Description: {description}', 'summary_created_at': 'Created at: {created_at}', 'summary_schema_yes': 'Database update: YES', 'summary_schema_no': 'Database update: NO', 'summary_notes': 'Notes:', 'summary_double_click': 'Double-click a file to update only it.', 'summary_right_click': 'Right-click a folder to update the whole folder.', 'update_file': 'Update file', 'update_folder': 'Update folder', 'confirm_update_file': 'Do you want to update this file?\n\n{rel}', 'confirm_update_folder': 'Do you want to update the whole folder?\n\n{rel}', 'update_all_title': 'Update All', 'confirm_update_all': 'Do you want to update the entire package?\n\nVersion: {version}', 'not_informed': 'not informed', 'update_cancelled': 'Update canceled.', 'updating': 'Updating: {source_label}...', 'warning_title': 'Update', 'no_package_scanned': 'No package scanned.', 'pages_not_updated': 'No page file was updated.', 'schema_not_updated': 'No schema file was updated.', 'pages_folder_not_found': 'PAGINAS_DO_SISTEMA folder was not found in the package.', 'schema_folder_not_found': 'SCHEMA folder was not found in the package.', 'applying_migrations': 'Applying database migrations...', 'migration_failed_restore': 'Migration failed. Files restored.', 'migration_failed_message': 'The files were updated, but the database migration failed.\n\nThe system automatically restored the backup files.\n\nDetails:\n{detalhes}', 'updated_pages': 'pages', 'updated_schema': 'schema', 'updated_files': 'files', 'update_completed': 'Update completed: {source_label}', 'update_completed_message': 'Update completed successfully:\n\n{source_label}\n\nUpdated items: {tipo_txt}{versao_linha}\n\nClose and reopen the system to load the changes.', 'version_installed': '\nNew installed version: {version}', 'download_online_package': 'Downloading online package...', 'extracting_package': 'Extracting package...', 'drive_download_failed': 'Could not download the Drive file.', 'zip_structure_missing': 'The ZIP was downloaded, but the expected structure was not found.\nExpected: PAGINAS_DO_SISTEMA/ and/or SCHEMA/.'}, 'es_ES': {'title': 'Actualizar Sistema', 'current_version': 'Versión actual: {versao}', 'ready': 'Listo.', 'update_source': 'Origen de la actualización:', 'local_mode': 'Local (carpeta del equipo)', 'online_mode': 'En línea (Google Drive ZIP)', 'choose_local_folder': 'Elegir carpeta local', 'paste_drive_link': 'Pegar enlace de Drive', 'search_updates': '🔍 Buscar actualizaciones', 'update_all': '🔄 Actualizar todo', 'restore_previous': '↩️ Volver a la versión anterior', 'files_in_package': 'Archivos encontrados en el paquete', 'tree_name': 'Nombre', 'tree_type': 'Tipo', 'tree_source': 'Origen', 'tree_relative': 'Relativo', 'tree_kind': 'Kind', 'popup_update_selected': 'Actualizar elemento seleccionado', 'no_scan': 'No se realizó ningún análisis.', 'source_local_title': 'Fuente (LOCAL):', 'source_drive_title': 'Fuente (EN LÍNEA - Google Drive ZIP):', 'no_folder_selected': 'Ninguna carpeta seleccionada.', 'no_link_informed': 'Ningún enlace informado.', 'local_hint': 'Seleccione una carpeta con:\n• PAGINAS_DO_SISTEMA/ (opcional)\n• SCHEMA/ (opcional)\n• manifest.json (opcional)', 'drive_hint': 'Pegue un enlace de archivo ZIP de Google Drive.\nDentro del ZIP debe existir:\n• PAGINAS_DO_SISTEMA/\n• SCHEMA/\n• manifest.json (opcional)', 'local_folder_selected': 'Carpeta local seleccionada.', 'drive_link_set': 'Enlace de Drive definido.', 'scan_failed': 'Falló el análisis.', 'scan_error': 'Error al analizar el paquete: {erro}', 'no_local_source_selected': 'No se seleccionó ninguna fuente local.', 'invalid_local_folder': 'La carpeta seleccionada no es válida.', 'no_online_source': 'No se informó ninguna fuente en línea.', 'invalid_package': 'Paquete inválido.', 'missing_pages_folder': 'No se encontró la carpeta PAGINAS_DO_SISTEMA.', 'missing_schema_folder': 'No se encontró la carpeta SCHEMA.', 'folder_pages': 'PAGINAS_DO_SISTEMA', 'folder_schema': 'SCHEMA', 'folder': 'CARPETA', 'package': 'PAQUETE', 'file': 'ARCHIVO', 'info': 'INFO', 'none_py_found': '(no se encontraron archivos .py)', 'no_updates_found': 'No se encontraron actualizaciones.', 'package_scanned_ok': 'Paquete analizado con éxito.', 'summary_no_both': 'No se encontraron las carpetas PAGINAS_DO_SISTEMA y SCHEMA.', 'summary_no_py': 'No se encontraron archivos .py de actualización.', 'summary_found_files': 'Se encontraron {total} archivo(s) de actualización.', 'summary_package_version': 'Versión del paquete: {version}', 'summary_description': 'Descripción: {description}', 'summary_created_at': 'Generado en: {created_at}', 'summary_schema_yes': 'Actualización de base de datos: SÍ', 'summary_schema_no': 'Actualización de base de datos: NO', 'summary_notes': 'Observaciones:', 'summary_double_click': 'Doble clic en un archivo para actualizar solo ese archivo.', 'summary_right_click': 'Clic derecho en una carpeta para actualizar la carpeta completa.', 'update_file': 'Actualizar archivo', 'update_folder': 'Actualizar carpeta', 'confirm_update_file': '¿Desea actualizar este archivo?\n\n{rel}', 'confirm_update_folder': '¿Desea actualizar la carpeta completa?\n\n{rel}', 'update_all_title': 'Actualizar todo', 'confirm_update_all': '¿Desea actualizar todo el paquete?\n\nVersión: {version}', 'not_informed': 'no informada', 'update_cancelled': 'Actualización cancelada.', 'updating': 'Actualizando: {source_label}...', 'warning_title': 'Actualización', 'no_package_scanned': 'Ningún paquete analizado.', 'pages_not_updated': 'No se actualizó ningún archivo de página.', 'schema_not_updated': 'No se actualizó ningún archivo de schema.', 'pages_folder_not_found': 'No se encontró la carpeta PAGINAS_DO_SISTEMA en el paquete.', 'schema_folder_not_found': 'No se encontró la carpeta SCHEMA en el paquete.', 'applying_migrations': 'Aplicando migraciones de la base de datos...', 'migration_failed_restore': 'Falló la migración. Archivos restaurados.', 'migration_failed_message': 'Los archivos fueron actualizados, pero la migración de la base de datos falló.\n\nEl sistema restauró automáticamente los archivos del respaldo.\n\nDetalles:\n{detalhes}', 'updated_pages': 'páginas', 'updated_schema': 'schema', 'updated_files': 'archivos', 'update_completed': 'Actualización completada: {source_label}', 'update_completed_message': 'Actualización completada con éxito:\n\n{source_label}\n\nElementos actualizados: {tipo_txt}{versao_linha}\n\nCierre y vuelva a abrir el sistema para cargar los cambios.', 'version_installed': '\nNueva versión instalada: {version}', 'download_online_package': 'Descargando paquete en línea...', 'extracting_package': 'Extrayendo paquete...', 'drive_download_failed': 'No fue posible descargar el archivo de Drive.', 'zip_structure_missing': 'Se descargó el ZIP, pero no se encontró la estructura esperada.\nEsperado: PAGINAS_DO_SISTEMA/ y/o SCHEMA/.'}}

    def _get_idioma_atual(self):
        origem = getattr(self, "app", None)
        return getattr(origem, "idioma_atual", "pt_BR") if origem else "pt_BR"

    def _get_text(self, chave, **kwargs):
        idioma = self._get_idioma_atual()
        base = self.TEXTOS_I18N.get(idioma) or self.TEXTOS_I18N["pt_BR"]
        valor = base.get(chave) or self.TEXTOS_I18N["pt_BR"].get(chave) or chave
        try:
            return valor.format(**kwargs)
        except Exception:
            return valor

    def _set_status(self, chave, **kwargs):
        self.status_var.set(self._get_text(chave, **kwargs))

    def _set_scan_summary(self, texto=None, chave=None, **kwargs):
        if chave:
            self.scan_summary_var.set(self._get_text(chave, **kwargs))
        else:
            self.scan_summary_var.set(texto or "")

    def refresh_texts(self):
        if hasattr(self, "version_var"):
            self.version_var.set(self._get_text("current_version", versao=self.versao_atual))
        if not getattr(self, "_ui_refs", None):
            return
        mapping = {"title_label": "title", "mode_label": "update_source", "radio_local": "local_mode", "radio_drive": "online_mode", "btn_local": "choose_local_folder", "btn_drive": "paste_drive_link", "btn_scan": "search_updates", "btn_update_all": "update_all", "btn_restore": "restore_previous", "results_label": "files_in_package"}
        for ref, key in mapping.items():
            widget = self._ui_refs.get(ref)
            if widget:
                widget.configure(text=self._get_text(key))
        try:
            self.tree.heading("#0", text=self._get_text("tree_name"))
            self.tree.heading("tipo", text=self._get_text("tree_type"))
            self.tree.heading("origem", text=self._get_text("tree_source"))
            self.tree.heading("rel", text=self._get_text("tree_relative"))
            self.tree.heading("kind", text=self._get_text("tree_kind"))
        except Exception:
            pass
        try:
            self.popup_menu.entryconfigure(0, label=self._get_text("popup_update_selected"))
        except Exception:
            pass
        self._apply_mode_ui(initial=True)

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):
        self.configure(fg_color="transparent")

        header = ctk.CTkFrame(self, corner_radius=12)
        header.pack(fill="x", padx=20, pady=(20, 10))

        self._ui_refs["title_label"] = ctk.CTkLabel(
            header,
            text=self._get_text("title"),
            font=("Segoe UI", 22, "bold"),
        )
        self._ui_refs["title_label"].pack(anchor="w", padx=20, pady=(16, 4))

        ctk.CTkLabel(
            header,
            textvariable=self.version_var,
            font=("Segoe UI", 14),
        ).pack(anchor="w", padx=20, pady=(0, 12))

        mode_box = ctk.CTkFrame(self, corner_radius=12)
        mode_box.pack(fill="x", padx=20, pady=10)

        self._ui_refs["mode_label"] = ctk.CTkLabel(
            mode_box,
            text=self._get_text("update_source"),
            font=("Segoe UI", 13, "bold"),
        )
        self._ui_refs["mode_label"].pack(anchor="w", padx=20, pady=(12, 6))

        row = ctk.CTkFrame(mode_box, corner_radius=12)
        row.pack(fill="x", padx=20, pady=(0, 12))

        self._ui_refs["radio_local"] = ctk.CTkRadioButton(
            row,
            text=self._get_text("local_mode"),
            value="local",
            variable=self.modo_var,
            command=self._on_mode_changed,
        )
        self._ui_refs["radio_local"].pack(side="left", padx=(0, 20), pady=6)

        self._ui_refs["radio_drive"] = ctk.CTkRadioButton(
            row,
            text=self._get_text("online_mode"),
            value="drive",
            variable=self.modo_var,
            command=self._on_mode_changed,
        )
        self._ui_refs["radio_drive"].pack(side="left", padx=(0, 20), pady=6)

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
            wraplength=980,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 12))

        self.btn_row = ctk.CTkFrame(info, corner_radius=12)
        self.btn_row.pack(fill="x", padx=20, pady=(0, 12))

        self.btn_local = ctk.CTkButton(
            self.btn_row,
            text=self._get_text("choose_local_folder"),
            command=self._alterar_fonte_local,
            width=240,
        )
        self._ui_refs["btn_local"] = self.btn_local

        self.btn_drive = ctk.CTkButton(
            self.btn_row,
            text=self._get_text("paste_drive_link"),
            command=self._alterar_fonte_drive,
            width=240,
        )
        self._ui_refs["btn_drive"] = self.btn_drive

        self.dica_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            info,
            textvariable=self.dica_var,
            font=("Segoe UI", 12),
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 12))

        actions = ctk.CTkFrame(self, corner_radius=12)
        actions.pack(fill="x", padx=20, pady=10)

        self._ui_refs["btn_scan"] = ctk.CTkButton(
            actions,
            text=self._get_text("search_updates"),
            command=self._scan_current_source,
            width=220,
        )
        self._ui_refs["btn_scan"].pack(side="left", padx=20, pady=16)

        self._ui_refs["btn_update_all"] = ctk.CTkButton(
            actions,
            text=self._get_text("update_all"),
            command=self._atualizar_tudo_do_pacote,
            width=220,
        )
        self._ui_refs["btn_update_all"].pack(side="left", padx=(0, 20), pady=16)

        self._ui_refs["btn_restore"] = ctk.CTkButton(
            actions,
            text=self._get_text("restore_previous"),
            command=self._restaurar_ultima_versao,
            width=260,
        )
        self._ui_refs["btn_restore"].pack(side="left", padx=(0, 20), pady=16)

        results_box = ctk.CTkFrame(self, corner_radius=12)
        results_box.pack(fill="both", expand=True, padx=20, pady=10)

        self._ui_refs["results_label"] = ctk.CTkLabel(
            results_box,
            text=self._get_text("files_in_package"),
            font=("Segoe UI", 13, "bold"),
        )
        self._ui_refs["results_label"].pack(anchor="w", padx=20, pady=(12, 8))

        tree_wrap = ctk.CTkFrame(results_box, corner_radius=8)
        tree_wrap.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        self.tree = ttk.Treeview(
            tree_wrap,
            columns=("tipo", "origem", "rel", "kind"),
            show="tree headings",
            height=14,
        )
        self.tree.heading("#0", text=self._get_text("tree_name"))
        self.tree.heading("tipo", text=self._get_text("tree_type"))
        self.tree.heading("origem", text=self._get_text("tree_source"))
        self.tree.heading("rel", text=self._get_text("tree_relative"))
        self.tree.heading("kind", text="Kind")

        self.tree.column("#0", width=280, anchor="w")
        self.tree.column("tipo", width=95, anchor="center")
        self.tree.column("origem", width=110, anchor="center")
        self.tree.column("rel", width=430, anchor="w")
        self.tree.column("kind", width=1, anchor="center", stretch=False)

        self.tree.pack(fill="both", expand=True, side="left")

        scroll = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-3>", self._on_tree_right_click)

        self.popup_menu = Menu(self, tearoff=0)
        self.popup_menu.add_command(label=self._get_text("popup_update_selected"), command=self._popup_update_selected)

        self.scan_summary_var = ctk.StringVar(value=self._get_text("no_scan"))
        ctk.CTkLabel(
            results_box,
            textvariable=self.scan_summary_var,
            font=("Segoe UI", 12),
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 12))

        ctk.CTkLabel(
            self,
            textvariable=self.status_var,
            font=("Segoe UI", 12),
            justify="left",
        ).pack(fill="x", padx=20, pady=(6, 0))

    # =========================================================
    # Modo
    # =========================================================
    def _on_mode_changed(self):
        self._apply_mode_ui()
        self._save_settings()

    def _apply_mode_ui(self, initial=False):
        for w in self.btn_row.winfo_children():
            w.pack_forget()

        mode = self.modo_var.get()

        if mode == "local":
            self.source_title_var.set(self._get_text("source_local_title"))
            self.source_value_var.set(self.local_source_var.get() or self._get_text("no_folder_selected"))
            self.dica_var.set(
                "Selecione uma pasta com:\n"
                "• PAGINAS_DO_SISTEMA/ (opcional)\n"
                "• SCHEMA/ (opcional)\n"
                "• manifest.json (opcional)"
            )
            self.btn_local.pack(side="left", padx=(0, 12), pady=6)
        else:
            self.source_title_var.set(self._get_text("source_drive_title"))
            self.source_value_var.set(self.drive_source_var.get() or self._get_text("no_link_informed"))
            self.dica_var.set(
                "Cole um link de arquivo ZIP do Google Drive.\n"
                "Dentro do ZIP deve existir:\n"
                "• PAGINAS_DO_SISTEMA/\n"
                "• SCHEMA/\n"
                "• manifest.json (opcional)"
            )
            self.btn_drive.pack(side="left", padx=(0, 12), pady=6)

        if not initial:
            self._set_status("ready")
            self._clear_tree()
            self._set_scan_summary(chave="no_scan")

    # =========================================================
    # Seleção de fonte
    # =========================================================
    def _alterar_fonte_local(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta de atualização")
        if pasta:
            self.local_source_var.set(pasta)
            self.source_value_var.set(pasta)
            self._save_settings()
            self._set_status("local_folder_selected")
            self._scan_current_source()

    def _alterar_fonte_drive(self):
        link = simpledialog.askstring(
            "Google Drive",
            "Cole o link do Drive (arquivo ZIP):",
            initialvalue=self.drive_source_var.get(),
        )
        if link:
            self.drive_source_var.set(link.strip())
            self.source_value_var.set(link.strip())
            self._save_settings()
            self._set_status("drive_link_set")
            self._scan_current_source()

    # =========================================================
    # Auto scan ao abrir
    # =========================================================
    def _auto_scan_on_open(self):
        try:
            has_saved = False
            if self.modo_var.get() == "local" and (self.local_source_var.get() or "").strip():
                has_saved = True
            if self.modo_var.get() == "drive" and (self.drive_source_var.get() or "").strip():
                has_saved = True

            if has_saved:
                self._scan_current_source()
        except Exception:
            pass

    # =========================================================
    # Scan
    # =========================================================
    def _scan_current_source(self):
        try:
            scan_root = self._prepare_source_for_scan()
            if scan_root is None:
                return

            self.current_scan_root = scan_root
            self.current_manifest = self._load_manifest_local(scan_root) or {}

            self._populate_tree_from_scan(scan_root)

        except Exception as e:
            self._set_status("scan_failed")
            self._clear_tree()
            self._set_scan_summary(chave="scan_error", erro=e)

    def _prepare_source_for_scan(self) -> Path | None:
        if self.modo_var.get() == "local":
            source = (self.local_source_var.get() or "").strip()
            if not source:
                self.status_var.set("Nenhuma pasta local selecionada.")
                self._clear_tree()
                self.scan_summary_var.set(self._get_text("no_local_source_selected"))
                return None

            source_path = Path(source)
            if not source_path.exists() or not source_path.is_dir():
                self.status_var.set("Pasta local inválida.")
                self._clear_tree()
                self.scan_summary_var.set(self._get_text("invalid_local_folder"))
                return None

            return source_path

        source_url = (self.drive_source_var.get() or "").strip()
        if not source_url:
            self.status_var.set("Nenhum link do Drive informado.")
            self._clear_tree()
            self.scan_summary_var.set(self._get_text("no_online_source"))
            return None

        return self._prepare_drive_source(source_url)

    def _populate_tree_from_scan(self, root: Path):
        """
        Analisa a pasta de atualização e preenche a Treeview.
        Regras:
        - Se não existir PAGINAS_DO_SISTEMA e nem SCHEMA -> avisa pacote inválido
        - Se existir só uma das pastas -> avisa que a outra não foi encontrada
        - Lista todos os .py encontrados nas pastas existentes
        """
        self._clear_tree()

        src_pages = root / "PAGINAS_DO_SISTEMA"
        src_schema = root / "SCHEMA"

        has_pages = src_pages.exists() and src_pages.is_dir()
        has_schema = src_schema.exists() and src_schema.is_dir()

        pages_files = sorted(src_pages.glob("*.py")) if has_pages else []
        schema_files = sorted(src_schema.glob("*.py")) if has_schema else []

        total = 0
        avisos = []

        if not has_pages and not has_schema:
            self.scan_summary_var.set(
                self._get_text("summary_no_both")
            )
            self.status_var.set(self._get_text("invalid_package"))
            return

        if not has_pages:
            avisos.append(self._get_text("missing_pages_folder"))

        if not has_schema:
            avisos.append(self._get_text("missing_schema_folder"))

        if has_pages:
            node_pages = self.tree.insert(
                "",
                "end",
                text="PAGINAS_DO_SISTEMA",
                values=(self._get_text("folder"), self._get_text("package"), "PAGINAS_DO_SISTEMA", "folder_pages"),
                open=True,
            )

            if pages_files:
                for f in pages_files:
                    rel = f"PAGINAS_DO_SISTEMA/{f.name}"
                    self.tree.insert(
                        node_pages,
                        "end",
                        text=f.name,
                        values=(self._get_text("file"), self._get_text("package"), rel, "file_pages"),
                    )
                    total += 1
            else:
                self.tree.insert(
                    node_pages,
                    "end",
                    text=self._get_text("none_py_found"),
                    values=(self._get_text("info"), self._get_text("package"), "PAGINAS_DO_SISTEMA", "info"),
                )

        if has_schema:
            node_schema = self.tree.insert(
                "",
                "end",
                text="SCHEMA",
                values=(self._get_text("folder"), self._get_text("package"), "SCHEMA", "folder_schema"),
                open=True,
            )

            if schema_files:
                for f in schema_files:
                    rel = f"SCHEMA/{f.name}"
                    self.tree.insert(
                        node_schema,
                        "end",
                        text=f.name,
                        values=(self._get_text("file"), self._get_text("package"), rel, "file_schema"),
                    )
                    total += 1
            else:
                self.tree.insert(
                    node_schema,
                    "end",
                    text=self._get_text("none_py_found"),
                    values=(self._get_text("info"), self._get_text("package"), "SCHEMA", "info"),
                )

        if total == 0:
            self.scan_summary_var.set(
                self._montar_resumo_manifest(total_encontrado=0, avisos=avisos)
            )
            self.status_var.set(self._get_text("no_updates_found"))
        else:
            self.scan_summary_var.set(
                self._montar_resumo_manifest(total_encontrado=total, avisos=avisos)
            )
            self.status_var.set(self._get_text("package_scanned_ok"))

    def _montar_resumo_manifest(self, total_encontrado: int, avisos: list[str] | None = None) -> str:
        avisos = avisos or []
        manifest = self.current_manifest or {}

        version = ""
        description = ""
        created_at = ""
        requires_schema = None
        notes = []

        if isinstance(manifest, dict):
            version = str(
                manifest.get("version")
                or manifest.get("versao")
                or manifest.get("versão")
                or ""
            ).strip()

            description = str(manifest.get("description") or "").strip()
            created_at = str(manifest.get("created_at") or "").strip()

            if "requires_schema" in manifest:
                requires_schema = bool(manifest.get("requires_schema"))

            raw_notes = manifest.get("notes")
            if isinstance(raw_notes, list):
                notes = [str(n).strip() for n in raw_notes if str(n).strip()]
            elif isinstance(raw_notes, str) and raw_notes.strip():
                notes = [raw_notes.strip()]

        linhas = []

        if avisos:
            linhas.extend(avisos)
            linhas.append("")

        if total_encontrado <= 0:
            linhas.append(self._get_text("summary_no_py"))
        else:
            linhas.append(self._get_text("summary_found_files", total=total_encontrado))

        if version:
            linhas.append(self._get_text("summary_package_version", version=version))

        if description:
            linhas.append(self._get_text("summary_description", description=description))

        if created_at:
            linhas.append(self._get_text("summary_created_at", created_at=created_at))

        if requires_schema is True:
            linhas.append(self._get_text("summary_schema_yes"))
        elif requires_schema is False:
            linhas.append(self._get_text("summary_schema_no"))

        if notes:
            linhas.append(self._get_text("summary_notes"))
            for n in notes:
                linhas.append(f"• {n}")

        if total_encontrado > 0:
            linhas.append("")
            linhas.append(self._get_text("summary_double_click"))
            linhas.append(self._get_text("summary_right_click"))

        return "\n".join(linhas).strip()

    def _clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    # =========================================================
    # Tree events
    # =========================================================
    def _on_tree_double_click(self, _event=None):
        item_id = self.tree.focus()
        if not item_id:
            return

        vals = self.tree.item(item_id, "values")
        if not vals:
            return

        kind = vals[3] if len(vals) >= 4 else ""

        if kind in ("file_pages", "file_schema"):
            rel = vals[2]
            nome = self.tree.item(item_id, "text")
            deseja = messagebox.askyesno(
                self._get_text("update_file"),
                f"Deseja atualizar este arquivo?\n\n{rel}"
            )
            if deseja:
                self._update_single_item(kind=kind, rel_path=rel, display_name=nome)

    def _on_tree_right_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        self.tree.selection_set(item_id)
        self.tree.focus(item_id)

        vals = self.tree.item(item_id, "values")
        if not vals:
            return

        kind = vals[3] if len(vals) >= 4 else ""
        self._popup_target_kind = kind
        self._popup_target_rel = vals[2]
        self._popup_target_name = self.tree.item(item_id, "text")

        if kind in ("folder_pages", "folder_schema", "file_pages", "file_schema"):
            self.popup_menu.tk_popup(event.x_root, event.y_root)

    def _popup_update_selected(self):
        kind = self._popup_target_kind
        rel = self._popup_target_rel
        name = self._popup_target_name

        if kind in ("folder_pages", "folder_schema"):
            deseja = messagebox.askyesno(
                self._get_text("update_folder"),
                f"Deseja atualizar a pasta completa?\n\n{rel}"
            )
            if deseja:
                self._update_folder(kind=kind, rel_path=rel, display_name=name)

        elif kind in ("file_pages", "file_schema"):
            deseja = messagebox.askyesno(
                self._get_text("update_file"),
                f"Deseja atualizar este arquivo?\n\n{rel}"
            )
            if deseja:
                self._update_single_item(kind=kind, rel_path=rel, display_name=name)

    # =========================================================
    # Atualizações
    # =========================================================
    def _atualizar_tudo_do_pacote(self):
        if self.current_scan_root is None:
            self._scan_current_source()
            if self.current_scan_root is None:
                return

        version = self._extract_version(self.current_manifest)
        deseja = messagebox.askyesno(
            self._get_text("update_all_title"),
            f"Deseja atualizar todo o pacote?\n\nVersão: {version or self._get_text("not_informed")}"
        )
        if not deseja:
            self.status_var.set(self._get_text("update_cancelled"))
            return

        self._perform_update(
            update_pages=True,
            update_schema=True,
            specific_file=None,
            source_label="pacote completo",
            set_version_if_full=True,
        )

    def _update_single_item(self, kind: str, rel_path: str, display_name: str):
        update_pages = kind == "file_pages"
        update_schema = kind == "file_schema"

        self._perform_update(
            update_pages=update_pages,
            update_schema=update_schema,
            specific_file=Path(rel_path).name,
            source_label=display_name,
            set_version_if_full=False,
        )

    def _update_folder(self, kind: str, rel_path: str, display_name: str):
        update_pages = kind == "folder_pages"
        update_schema = kind == "folder_schema"

        self._perform_update(
            update_pages=update_pages,
            update_schema=update_schema,
            specific_file=None,
            source_label=display_name,
            set_version_if_full=False,
        )

    def _perform_update(
            self,
            update_pages: bool,
            update_schema: bool,
            specific_file: str | None,
            source_label: str,
            set_version_if_full: bool = True,
    ):
        """
        Executa a atualização dos arquivos selecionados.

        Regras:
        - Se update_pages=True, atualiza arquivos em PAGINAS_DO_SISTEMA
        - Se update_schema=True, atualiza arquivos em SCHEMA
        - Se houver atualização de schema, roda SCHEMA_MANAGER
        - Se houver version no manifest e a atualização der certo, SEMPRE grava a nova versão
        - Se algo falhar, restaura o backup automaticamente
        """
        if self.current_scan_root is None:
            messagebox.showwarning(self._get_text("warning_title"), self._get_text("no_package_scanned"))
            return

        backup_dir = self._fazer_backup()

        try:
            self.status_var.set(self._get_text("updating", source_label=source_label))

            schema_updated = False
            pages_updated = False

            # -------------------------------------------------
            # Atualizar páginas
            # -------------------------------------------------
            if update_pages:
                src_pages = self.current_scan_root / "PAGINAS_DO_SISTEMA"
                if src_pages.exists() and src_pages.is_dir():
                    ok_pages = self._copiar_py_de_pasta(
                        origem=src_pages,
                        destino=self.package_dir,
                        only_name=specific_file if (specific_file and not update_schema) else None,
                    )
                    if not ok_pages:
                        raise RuntimeError(self._get_text("pages_not_updated"))
                    pages_updated = True
                else:
                    raise RuntimeError(self._get_text("pages_folder_not_found"))

            # -------------------------------------------------
            # Atualizar schema
            # -------------------------------------------------
            if update_schema:
                src_schema = self.current_scan_root / "SCHEMA"
                if src_schema.exists() and src_schema.is_dir():
                    dst_schema = self.base_dir / "SCHEMA"
                    dst_schema.mkdir(parents=True, exist_ok=True)

                    ok_schema = self._copiar_py_de_pasta(
                        origem=src_schema,
                        destino=dst_schema,
                        only_name=specific_file if (specific_file and not update_pages) else None,
                    )
                    if not ok_schema:
                        raise RuntimeError(self._get_text("schema_not_updated"))

                    schema_updated = True
                else:
                    raise RuntimeError(self._get_text("schema_folder_not_found"))

            # -------------------------------------------------
            # Rodar migração se schema foi atualizado
            # -------------------------------------------------
            if schema_updated:
                self.status_var.set(self._get_text("applying_migrations"))
                mig_ok, mig_msg = self._aplicar_migracoes_pos_update()

                if not mig_ok:
                    self._restore_backup(backup_dir)
                    self.status_var.set(self._get_text("migration_failed_restore"))
                    messagebox.showerror(
                        "Atualização",
                        "Os arquivos foram atualizados, mas a migração do banco falhou.\n\n"
                        "O sistema restaurou automaticamente os arquivos do backup.\n\n"
                        f"Detalhes:\n{mig_msg}"
                    )
                    return

            # -------------------------------------------------
            # Atualizar versão SEMPRE que houver version no manifest
            # -------------------------------------------------
            version = self._extract_version(self.current_manifest)
            if version:
                self._set_versao_atual(version)

            # -------------------------------------------------
            # Mensagem final
            # -------------------------------------------------
            tipos = []
            if pages_updated:
                tipos.append(self._get_text("updated_pages"))
            if schema_updated:
                tipos.append(self._get_text("updated_schema"))

            tipo_txt = " e ".join(tipos) if tipos else self._get_text("updated_files")

            self.status_var.set(self._get_text("update_completed", source_label=source_label))

            msg = (
                f"Atualização concluída com sucesso:\n\n"
                f"{source_label}\n\n"
                f"Itens atualizados: {tipo_txt}"
            )

            if version:
                msg += f"\nNova versão instalada: {version}"

            msg += "\n\nFeche e reabra o sistema para carregar as alterações."

            messagebox.showinfo("Atualização", msg)

        except Exception as e:
            self._restore_backup(backup_dir)
            self.status_var.set("Falha na atualização. Backup restaurado.")
            messagebox.showerror(
                "Atualização",
                "Não foi possível concluir a atualização.\n\n"
                "O sistema restaurou automaticamente os arquivos do backup.\n\n"
                f"Detalhes:\n{e}"
            )

    def _aplicar_migracoes_pos_update(self) -> tuple[bool, str]:
        candidates = [
            "SCHEMA.SCHEMA_MANAGER",
            "SCHEMA_MANAGER",
        ]

        errors = []

        base_dir_str = str(self.base_dir)
        if base_dir_str not in sys.path:
            sys.path.insert(0, base_dir_str)

        for mod_name in candidates:
            try:
                if mod_name in sys.modules:
                    module = importlib.reload(sys.modules[mod_name])
                else:
                    module = importlib.import_module(mod_name)

                fn = getattr(module, "aplicar_migracoes_pendentes", None)
                if not callable(fn):
                    errors.append(f"{mod_name}: função aplicar_migracoes_pendentes não encontrada.")
                    continue

                # Não passa versão e não passa DSN
                fn()
                return True, f"Migração aplicada por {mod_name}."

            except Exception as e:
                errors.append(f"{mod_name}: Falha em aplicar_migracoes_pendentes: {e}")

        return False, "\n".join(errors) if errors else "Nenhum módulo de migração encontrado."

    # =========================================================
    # Local / Drive
    # =========================================================
    def _prepare_drive_source(self, source_url: str) -> Path | None:
        if not source_url:
            self.scan_summary_var.set("Nenhum link do Drive informado.")
            return None

        norm_url = self._normalize_drive_url(source_url)

        tmp_root = Path(tempfile.mkdtemp(prefix="opera_update_"))
        self.current_temp_root = tmp_root
        zip_path = tmp_root / "update.zip"

        self.status_var.set(self._get_text("download_online_package"))
        self._download_binary(norm_url, zip_path)

        if not zip_path.exists() or zip_path.stat().st_size == 0:
            raise RuntimeError(self._get_text("drive_download_failed"))

        self.status_var.set(self._get_text("extracting_package"))
        extract_dir = tmp_root / "package"
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        candidate = self._find_update_root(extract_dir)
        if candidate is None:
            raise RuntimeError(
                "O ZIP foi baixado, mas não encontrei a estrutura esperada.\n"
                "Esperado: PAGINAS_DO_SISTEMA/ e/ou SCHEMA/."
            )

        return candidate

    def _find_update_root(self, root: Path) -> Path | None:
        if self._looks_like_update_root(root):
            return root

        for item in root.iterdir():
            if item.is_dir() and self._looks_like_update_root(item):
                return item

        return None

    def _looks_like_update_root(self, p: Path) -> bool:
        return (
            (p / "PAGINAS_DO_SISTEMA").exists() or
            (p / "SCHEMA").exists() or
            (p / "manifest.json").exists()
        )

    def _normalize_drive_url(self, url: str) -> str:
        u = (url or "").strip()
        if not u:
            return u

        if "drive.google.com/uc?" in u and "id=" in u:
            return u

        m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", u)
        if m:
            file_id = m.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"

        m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", u)
        if m:
            file_id = m.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"

        return u

    def _download_binary(self, url: str, target_path: Path):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            data = response.read()
        target_path.write_bytes(data)

    # =========================================================
    # Cópia
    # =========================================================
    def _copiar_py_de_pasta(self, origem: Path, destino: Path, only_name: str | None = None) -> bool:
        arquivos = list(origem.glob("*.py"))
        if only_name:
            arquivos = [p for p in arquivos if p.name == only_name]

        if not arquivos:
            return False

        destino.mkdir(parents=True, exist_ok=True)
        copied = False

        for file_path in arquivos:
            try:
                shutil.copy2(file_path, destino / file_path.name)
                copied = True
            except Exception:
                pass

        return copied

    # =========================================================
    # Backup / restore
    # =========================================================
    def _fazer_backup(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self._backup_current_version(timestamp, self.versao_atual)

    def _backup_current_version(self, timestamp: str, versao_atual: str) -> Path:
        backup_dir = self.backup_root / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        (backup_dir / "BACKUP_VERSION.txt").write_text(str(versao_atual), encoding="utf-8")

        # raiz
        for py_file in self.base_dir.glob("*.py"):
            try:
                shutil.copy2(py_file, backup_dir / py_file.name)
            except Exception:
                pass

        # páginas
        backup_pages = backup_dir / "PAGINAS_DO_SISTEMA"
        backup_pages.mkdir(parents=True, exist_ok=True)
        for py_file in self.package_dir.glob("*.py"):
            try:
                shutil.copy2(py_file, backup_pages / py_file.name)
            except Exception:
                pass

        # schema
        src_schema = self.base_dir / "SCHEMA"
        if src_schema.exists() and src_schema.is_dir():
            backup_schema = backup_dir / "SCHEMA"
            backup_schema.mkdir(parents=True, exist_ok=True)
            for py_file in src_schema.glob("*.py"):
                try:
                    shutil.copy2(py_file, backup_schema / py_file.name)
                except Exception:
                    pass

        return backup_dir

    def _restore_backup(self, backup_dir: Path) -> bool:
        try:
            for py_file in backup_dir.glob("*.py"):
                shutil.copy2(py_file, self.base_dir / py_file.name)

            backup_pages = backup_dir / "PAGINAS_DO_SISTEMA"
            if backup_pages.exists():
                for py_file in backup_pages.glob("*.py"):
                    shutil.copy2(py_file, self.package_dir / py_file.name)

            backup_schema = backup_dir / "SCHEMA"
            if backup_schema.exists():
                dst_schema = self.base_dir / "SCHEMA"
                dst_schema.mkdir(parents=True, exist_ok=True)
                for py_file in backup_schema.glob("*.py"):
                    shutil.copy2(py_file, dst_schema / py_file.name)

            return True
        except Exception:
            return False

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

        restored = self._restore_backup(backup_dir)
        if restored:
            if versao_backup and versao_backup != "anterior":
                self._set_versao_atual(versao_backup)
            messagebox.showinfo("Voltar versão", f"Você voltou para a versão {versao_backup}.")
            self.status_var.set(f"Você voltou para a versão {versao_backup}.")
        else:
            messagebox.showerror("Voltar versão", "Não foi possível voltar para a versão anterior.")
            self.status_var.set("Não foi possível voltar para a versão anterior.")

    def _read_backup_version(self, backup_dir: Path) -> str | None:
        p = backup_dir / "BACKUP_VERSION.txt"
        if p.exists():
            try:
                return p.read_text(encoding="utf-8").strip() or None
            except Exception:
                return None
        return None

    # =========================================================
    # Manifest / versão
    # =========================================================
    def _load_manifest_local(self, source_dir: Path) -> dict | None:
        manifest_path = source_dir / "manifest.json"
        if not manifest_path.exists():
            return None
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
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

    def _set_versao_atual(self, versao: str):
        self.versao_atual = str(versao).strip() or self.VERSAO_PADRAO
        self._save_current_version(self.versao_atual)
        self.version_var.set(self._get_text("current_version", versao=self.versao_atual))

    # =========================================================
    # Settings
    # =========================================================
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
            self.settings_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass


if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Teste - Atualizar Sistema")
    root.geometry("1200x840")

    page = AtualizarSistemaPage(root)
    page.pack(fill="both", expand=True)

    root.mainloop()