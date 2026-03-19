# BACKUP.py
# Tela de backup do banco PostgreSQL - compatível com MENU_PRINCIPAL

from __future__ import annotations
import os
import sys
import subprocess
import threading
from datetime import datetime
import time
import glob
import shutil

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

# ESTADO GLOBAL DO BACKUP AUTOMÁTICO
BACKUP_AUTO = {
    "running": False,    # está ativo?
    "interval": 3600,    # em segundos
    "pasta": None,       # caminho da pasta de backups
    "thread": None,      # thread real
    "proximo": None      # timestamp do próximo backup
}


# Banco / config
try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import CONFIG, ENDPOINTS, ready_check
except Exception:
    CONFIG = {
        "defaults": {
            "dbname": "BANCO_OPERA",
            "user": "postgres",
            "password": ""
        },
        "hosts": ["localhost"],
        "ports": [5432],
    }
    ENDPOINTS = [("localhost", 5432)]


    def ready_check():
        return False


class BackupPage(ctk.CTkFrame):
    def __init__(self, master, sistema=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.master = master
        self.sistema = sistema
        self.app = sistema
        self._ui_refs = {}

        # 🎨 Tema (com fallback seguro)
        origem = sistema or master
        try:
            self.cor_fundo = getattr(origem, "cor_fundo", "#0f172a")
            self.cor_texto = getattr(origem, "cor_texto", "#e5e7eb")
            self.cor_borda = getattr(origem, "cor_borda", "#334155")
            self.cor_primaria = getattr(origem, "cor_primaria", "#1f538d")
            self.cor_hover = getattr(origem, "cor_hover", "#14375e")
            self.cor_destaque = getattr(origem, "cor_selecao", "#223649")
        except:
            self.cor_fundo = "#0f172a"
            self.cor_texto = "#e5e7eb"
            self.cor_borda = "#334155"
            self.cor_primaria = "#1f538d"
            self.cor_hover = "#14375e"
            self.cor_destaque = "#223649"

        self.configure(fg_color=self.cor_fundo)
        self.pack(fill="both", expand=True)

        # Logger
        try:
            from PAGINAS_DO_SISTEMA.LOG_SISTEMA import get_logger
            self.logger = get_logger("OPERA_SYSTEM")
        except:
            self.logger = None

        # Banco
        # Banco / config
        try:
            from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import CONFIG, ready_check
            ENDPOINTS = [(CONFIG["hosts"][0], CONFIG["ports"][0])]
        except Exception:
            # FALLBACK SE O BANCO_DE_DADOS_PG NÃO EXISTIR OU DER ERRO
            CONFIG = {
                "defaults": {
                    "dbname": "BANCO_OPERA",
                    "user": "postgres",
                    "password": ""
                },
                "hosts": ["localhost"],
                "ports": [5432],
            }
            ENDPOINTS = [("localhost", 5432)]

            def ready_check():
                return False

        self.host = CONFIG["hosts"][0]
        self.port = CONFIG["ports"][0] if CONFIG["ports"] else 5432
        self.user = CONFIG.get("defaults", {}).get("user", "postgres")
        self.database = CONFIG.get("defaults", {}).get("dbname", "BANCO_OPERA")
        self.password = self._carregar_senha_diretamente()

        senha_info = "Sim" if self.password else "Não"
        if self.logger:
            self.logger.info(
                f"[BACKUP] Configuração - Host: {self.host}, Porta: {self.port}, DB: {self.database}, Senha: {senha_info}"
            )

        # Estados internos
        self._backup_thread = None
        self._ultimo_backup = None

        self._backup_auto_thread = None
        self._backup_auto_running = False
        self._backup_auto_interval = 3600
        self._backup_auto_pasta = None
        self._proximo_backup_auto = None
        self._max_backups = 300

        # Construção da UI
        self._apply_ttk_theme()
        self._build_ui()

        # Testar banco
        self._check_db_ready()

        # Criar pasta local de backups
        self._criar_pasta_backups()

        if self.logger:
            self.logger.info(f"[PAGINA] Backup inicializada (porta={self.port}, senha={senha_info})")

        # 🔥 NOVO: sincronizar estado global do backup automático
        self.after(150, self._sincronizar_estado_automatico)

        # Sincronização da UI

    @staticmethod
    def criar_pasta_backups_externo(diretorio_base):
        """
        Função usada pelo MENU_PRINCIPAL para garantir a existência da pasta
        de backups SEM precisar abrir a página.
        """
        try:
            pasta = os.path.join(diretorio_base, "backup_banco")
            os.makedirs(pasta, exist_ok=True)
            print(f"[BACKUP] Pasta de backups garantida: {pasta}")
            return pasta

        except Exception as e:
            print(f"❌ Erro ao criar pasta de backups: {e}")
            return None

    def _sincronizar_estado_automatico(self):
        """
        Sincroniza a UI com o processo global BACKUP_AUTO que pode ter sido iniciado pelo MENU.
        Isso garante que a interface reflita corretamente o estado atual.
        """
        global BACKUP_AUTO

        try:
            # Se o backup automático foi iniciado pelo MENU, sincroniza a UI
            if BACKUP_AUTO.get("running") and not self._backup_auto_running:
                print("🔄 [BACKUP] Sincronizando UI com backup automático iniciado pelo MENU")

                # Copiar valores globais
                self._backup_auto_running = True
                self._backup_auto_interval = BACKUP_AUTO.get("interval", 3600)
                self._backup_auto_pasta = BACKUP_AUTO.get("pasta") or self.pasta_backups
                self._backup_auto_thread = BACKUP_AUTO.get("thread")

                # Atualizar UI
                self.interval_var.set(str(self._backup_auto_interval))
                self.auto_pasta_var.set(self._backup_auto_pasta)

                self.btn_iniciar_auto.configure(state="disabled")
                self.btn_parar_auto.configure(state="normal")
                self.entry_auto_pasta.configure(state="disabled")

                self.lbl_status_auto.configure(
                    text=f"Backup automático: ATIVO (próximo: {self._formatar_tempo(self._backup_auto_interval)})",
                    text_color="#4ade80"
                )

                self._log("🔧 Backup automático sincronizado com o sistema")

            elif BACKUP_AUTO.get("running") and self._backup_auto_running:
                # Já está sincronizado
                pass

            else:
                # Estado inativo
                self._backup_auto_running = False
                self.btn_iniciar_auto.configure(state="normal")
                self.btn_parar_auto.configure(state="disabled")
                self.entry_auto_pasta.configure(state="normal")
                self.lbl_status_auto.configure(
                    text=self._get_text("auto_inactive"),
                    text_color="#9ca3af"
                )

        except Exception as e:
            print(f"Erro ao sincronizar estado automático: {e}")

    @staticmethod
    def _executar_backup_auto_silencioso_static():
        """
        Executa um backup automático silencioso SOMENTE se:

        ✔ Pasta vazia  → gera imediatamente
        ✔ Último backup > 30 min → gera
        ✔ Último backup < 30 min → ignora
        ✔ Mantém 300 arquivos
        """

        try:
            global BACKUP_AUTO
            pasta = BACKUP_AUTO.get("pasta")

            if not pasta:
                print("⚠️ [AUTO] Pasta do backup não definida.")
                return

            os.makedirs(pasta, exist_ok=True)

            # Buscar arquivos de backup (manual e automático)
            padroes = [
                os.path.join(pasta, "auto_opera_*.sql"),
                os.path.join(pasta, "backup_opera_*.sql"),
            ]

            arquivos = []
            for p in padroes:
                arquivos.extend(glob.glob(p))

            arquivos = sorted(arquivos, key=os.path.getctime)

            LIMITE_SEGUNDOS = 30 * 60  # 30 minutos

            # ----------------------------------------------------
            # 🔥 REGRA 1 — PASTA VAZIA → criar imediatamente
            # ----------------------------------------------------
            if not arquivos:
                executar_backup = True
            else:
                # ----------------------------------------------------
                # 🔥 REGRA 2 — Verificar idade do último backup
                # ----------------------------------------------------
                ultimo = arquivos[-1]
                idade_ultimo = time.time() - os.path.getctime(ultimo)
                executar_backup = idade_ultimo >= LIMITE_SEGUNDOS

            if not executar_backup:
                print("⏸ [AUTO] Backup ignorado (último < 30 min).")
                return

            # ----------------------------------------------------
            # 🔥 Gerar nome do novo backup
            # ----------------------------------------------------
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"auto_opera_{timestamp}.sql"
            caminho_final = os.path.join(pasta, nome_arquivo)

            # ----------------------------------------------------
            # 🔥 Dados do banco
            # ----------------------------------------------------
            from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import CONFIG
            host = CONFIG["hosts"][0]
            port = CONFIG["ports"][0]
            user = CONFIG["defaults"].get("user", "postgres")
            database = CONFIG["defaults"].get("dbname", "BANCO_OPERA")

            # Senha
            password = ""
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
            if os.path.exists(config_path):
                try:
                    import json
                    with open(config_path, "r", encoding="utf-8") as f:
                        password = json.load(f).get("defaults", {}).get("password", "")
                except:
                    pass

            # ----------------------------------------------------
            # 🔥 Detectar pg_dump
            # ----------------------------------------------------
            pg_dump = "pg_dump"
            for path in [
                "/Library/PostgreSQL/18/bin/pg_dump",
                "/Library/PostgreSQL/17/bin/pg_dump",
                "/opt/homebrew/bin/pg_dump",
                "/usr/local/bin/pg_dump",
            ]:
                if os.path.exists(path):
                    pg_dump = path
                    break

            # Comando
            cmd = [
                pg_dump,
                "-h", host,
                "-p", str(port),
                "-U", user,
                "-F", "p",
                "-d", database,
                "-f", caminho_final
            ]

            env = os.environ.copy()
            if password:
                env["PGPASSWORD"] = password

            subprocess.run(cmd, env=env)

            print(f"🟢 [AUTO] Backup gerado: {caminho_final}")

            # ----------------------------------------------------
            # 🔥 Limpar excesso acima de 300
            # ----------------------------------------------------
            # Recontar incluindo tudo
            arquivos = []
            for p in padroes:
                arquivos.extend(glob.glob(p))

            arquivos = sorted(arquivos, key=os.path.getctime)

            if len(arquivos) > 300:
                excedente = len(arquivos) - 300
                for i in range(excedente):
                    try:
                        os.remove(arquivos[i])
                        print(f"🧹 [AUTO] Removido backup antigo: {arquivos[i]}")
                    except:
                        pass

        except Exception as e:
            print(f"❌ [AUTO] Erro no backup automático: {e}")

    def _carregar_senha_diretamente(self):
        """Carrega a senha diretamente do arquivo config.json"""
        try:
            import json
            # Caminho absoluto para o config.json
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    senha = config_data.get("defaults", {}).get("password", "")

                    if senha:
                        if self.logger:
                            self.logger.info(f"[BACKUP] Senha carregada do config.json: {len(senha)} caracteres")
                        return senha
                    else:
                        if self.logger:
                            self.logger.warning("[BACKUP] Senha vazia no config.json")
            else:
                if self.logger:
                    self.logger.error(f"[BACKUP] Arquivo config.json não encontrado: {config_path}")

        except Exception as e:
            if self.logger:
                self.logger.error(f"[BACKUP] Erro ao carregar senha: {e}")

        return ""

    def _detectar_porta_automaticamente(self):
        """Detecta automaticamente a porta do PostgreSQL"""
        portas_para_testar = [5432, 5433, 5434, 5435]  # Portas comuns do PostgreSQL

        for porta in portas_para_testar:
            if self._testar_conexao_porta(porta):
                if self.logger:
                    self.logger.info(f"[BACKUP] Porta {porta} detectada como ativa")
                return porta

        # Se nenhuma porta funcionar, usa 5432 como fallback
        if self.logger:
            self.logger.warning(f"[BACKUP] Nenhuma porta detectada, usando fallback 5432")
        return 5432

    def _testar_conexao_porta(self, porta):
        """Testa conexão em uma porta específica"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.host,
                port=porta,
                database=self.database,
                user=self.user,
                password=self.password,
                connect_timeout=3
            )
            conn.close()
            return True
        except:
            return False

    # ------------------------------------------------------------------ Idioma
    TEXTOS_I18N = {'pt_BR': {'title': '💽 Backup do Banco de Dados', 'checking_db': 'Verificando banco...', 'backup_desc': 'Gerar backup completo do banco Opera (pg_dump).', 'backup_now': '💾 Gerar backup agora', 'open_folder': '📂 Abrir pasta de backups', 'auto_title': '🔄 Backup Automático (rotação: 300 arquivos)', 'interval': 'Intervalo:', 'every_hour': '(A cada hora)', 'every_6_hours': '(A cada 6 horas)', 'every_12_hours': '(A cada 12 horas)', 'daily': '(Diariamente)', 'every_2_days': '(A cada 2 dias)', 'weekly': '(Semanalmente)', 'folder': 'Pasta:', 'auto_folder_placeholder': 'Pasta para backups automáticos...', 'start_auto': '▶ Iniciar Backup Automático', 'stop_auto': '⏹ Parar Backup Automático', 'auto_inactive': 'Backup automático: INATIVO', 'run_now': '⚡ Executar Agora', 'log_title': 'Log de backup', 'host': 'Host:', 'port': 'Porta:', 'user': 'Usuário:', 'database': 'Banco:', 'error': 'Erro', 'select_auto_folder': 'Selecionar pasta para backups automáticos', 'invalid_interval': 'Intervalo inválido. Selecione um intervalo válido.', 'cannot_access_folder': 'Não foi possível criar/acessar a pasta:\n{pasta}', 'backup_title': 'Backup', 'backup_already_running': 'Já existe um backup em execução. Aguarde terminar.', 'unknown_size': 'Tamanho desconhecido', 'cannot_open_folder': 'Não foi possível abrir a pasta:\n\n{erro}', 'backup_screen_loaded': 'Tela de backup carregada.', 'backups_info': 'Backups: {total}/{maximo} | Tamanho: {tamanho}'}, 'en_US': {'title': '💽 Database Backup', 'checking_db': 'Checking database...', 'backup_desc': 'Generate a full backup of the Opera database (pg_dump).', 'backup_now': '💾 Back up now', 'open_folder': '📂 Open backup folder', 'auto_title': '🔄 Automatic Backup (rotation: 300 files)', 'interval': 'Interval:', 'every_hour': '(Every hour)', 'every_6_hours': '(Every 6 hours)', 'every_12_hours': '(Every 12 hours)', 'daily': '(Daily)', 'every_2_days': '(Every 2 days)', 'weekly': '(Weekly)', 'folder': 'Folder:', 'auto_folder_placeholder': 'Folder for automatic backups...', 'start_auto': '▶ Start Automatic Backup', 'stop_auto': '⏹ Stop Automatic Backup', 'auto_inactive': 'Automatic backup: INACTIVE', 'run_now': '⚡ Run Now', 'log_title': 'Backup log', 'host': 'Host:', 'port': 'Port:', 'user': 'User:', 'database': 'Database:', 'error': 'Error', 'select_auto_folder': 'Select folder for automatic backups', 'invalid_interval': 'Invalid interval. Select a valid interval.', 'cannot_access_folder': 'Could not create/access the folder:\n{pasta}', 'backup_title': 'Backup', 'backup_already_running': 'A backup is already running. Wait for it to finish.', 'unknown_size': 'Unknown size', 'cannot_open_folder': 'Could not open the folder:\n\n{erro}', 'backup_screen_loaded': 'Backup screen loaded.', 'backups_info': 'Backups: {total}/{maximo} | Size: {tamanho}'}, 'es_ES': {'title': '💽 Respaldo de Base de Datos', 'checking_db': 'Verificando base de datos...', 'backup_desc': 'Generar respaldo completo de la base de datos Opera (pg_dump).', 'backup_now': '💾 Generar respaldo ahora', 'open_folder': '📂 Abrir carpeta de respaldos', 'auto_title': '🔄 Respaldo Automático (rotación: 300 archivos)', 'interval': 'Intervalo:', 'every_hour': '(Cada hora)', 'every_6_hours': '(Cada 6 horas)', 'every_12_hours': '(Cada 12 horas)', 'daily': '(Diariamente)', 'every_2_days': '(Cada 2 días)', 'weekly': '(Semanalmente)', 'folder': 'Carpeta:', 'auto_folder_placeholder': 'Carpeta para respaldos automáticos...', 'start_auto': '▶ Iniciar Respaldo Automático', 'stop_auto': '⏹ Detener Respaldo Automático', 'auto_inactive': 'Respaldo automático: INACTIVO', 'run_now': '⚡ Ejecutar ahora', 'log_title': 'Registro de respaldo', 'host': 'Host:', 'port': 'Puerto:', 'user': 'Usuario:', 'database': 'Base de datos:', 'error': 'Error', 'select_auto_folder': 'Seleccionar carpeta para respaldos automáticos', 'invalid_interval': 'Intervalo inválido. Seleccione un intervalo válido.', 'cannot_access_folder': 'No se pudo crear/acceder a la carpeta:\n{pasta}', 'backup_title': 'Respaldo', 'backup_already_running': 'Ya hay un respaldo en ejecución. Espere a que termine.', 'unknown_size': 'Tamaño desconocido', 'cannot_open_folder': 'No fue posible abrir la carpeta:\n\n{erro}', 'backup_screen_loaded': 'Pantalla de respaldo cargada.', 'backups_info': 'Respaldos: {total}/{maximo} | Tamaño: {tamanho}'}}

    def _get_idioma_atual(self):
        origem = getattr(self, "sistema", None) or getattr(self, "app", None)
        return getattr(origem, "idioma_atual", "pt_BR") if origem else "pt_BR"

    def _get_text(self, chave, **kwargs):
        idioma = self._get_idioma_atual()
        base = self.TEXTOS_I18N.get(idioma) or self.TEXTOS_I18N["pt_BR"]
        valor = base.get(chave) or self.TEXTOS_I18N["pt_BR"].get(chave) or chave
        try:
            return valor.format(**kwargs)
        except Exception:
            return valor

    def refresh_texts(self):
        if not getattr(self, "_ui_refs", None):
            return
        mapping = {"title_label":"title","desc_label":"backup_desc","btn_backup":"backup_now","btn_open_folder":"open_folder","auto_title_label":"auto_title","interval_label":"interval","folder_label":"folder","btn_iniciar_auto":"start_auto","btn_parar_auto":"stop_auto","btn_executar_agora":"run_now","log_title_label":"log_title","host_label":"host","port_label":"port","user_label":"user","db_label":"database"}
        for ref,key in mapping.items():
            widget=self._ui_refs.get(ref)
            if widget:
                widget.configure(text=self._get_text(key))
        if hasattr(self,'entry_auto_pasta'):
            self.entry_auto_pasta.configure(placeholder_text=self._get_text('auto_folder_placeholder'))
        self._atualizar_descricao_intervalo(self.interval_var.get())
        self._atualizar_info_pasta()

    # ------------------------------------------------------------------ UI
    def _apply_ttk_theme(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

    def _build_ui(self):
        # Título
        header = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        header.pack(fill="x", padx=10, pady=(10, 6))

        self._ui_refs["title_label"] = ctk.CTkLabel(
            header,
            text=self._get_text("title"),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.cor_texto,
        )
        self._ui_refs["title_label"].pack(side="left")

        # Painel de informações do banco
        info = ctk.CTkFrame(
            self,
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
            border_width=1,
            corner_radius=10,
        )
        info.pack(fill="x", padx=10, pady=(0, 10))

        grid = ctk.CTkFrame(info, fg_color=self.cor_fundo)
        grid.pack(side="left", padx=10, pady=10)

        def add_row(row, ref_key, label, value):
            lbl = ctk.CTkLabel(
                grid, text=label, text_color=self.cor_texto
            )
            lbl.grid(row=row, column=0, sticky="w", padx=(0, 5))
            self._ui_refs[ref_key] = lbl
            ctk.CTkLabel(
                grid, text=value, text_color=self.cor_texto,
                font=ctk.CTkFont(size=13, weight="bold")
            ).grid(row=row, column=1, sticky="w")

        add_row(0, "host_label", self._get_text("host"), str(self.host))
        add_row(1, "port_label", self._get_text("port"), str(self.port))
        add_row(2, "user_label", self._get_text("user"), self.user)
        add_row(3, "db_label", self._get_text("database"), self.database)

        # Status do banco
        self.lbl_status = ctk.CTkLabel(
            info,
            text=self._get_text("checking_db"),
            text_color="#e5e7eb",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_status.pack(side="right", padx=10)

        # Área de ações
        actions = ctk.CTkFrame(
            self,
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
            border_width=1,
            corner_radius=10,
        )
        actions.pack(fill="x", padx=10, pady=(0, 10))

        self._ui_refs["desc_label"] = ctk.CTkLabel(
            actions,
            text=self._get_text("backup_desc"),
            text_color=self.cor_texto,
        )
        self._ui_refs["desc_label"].pack(anchor="w", padx=10, pady=(8, 4))

        btns = ctk.CTkFrame(actions, fg_color=self.cor_fundo)
        btns.pack(fill="x", padx=10, pady=(0, 10))

        self.btn_backup = ctk.CTkButton(
            btns,
            text=self._get_text("backup_now"),
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            command=self._on_backup_clicked,
            width=180,
        )
        self._ui_refs["btn_backup"] = self.btn_backup
        self.btn_backup.pack(side="left", padx=(0, 10))

        self._ui_refs["btn_open_folder"] = ctk.CTkButton(
            btns,
            text=self._get_text("open_folder"),
            fg_color=self.cor_destaque,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            command=self._abrir_pasta_backups,
        )
        self._ui_refs["btn_open_folder"].pack(side="left", padx=(0, 10))

        # Info da pasta de backups
        self.lbl_info_pasta = ctk.CTkLabel(
            btns,
            text="",
            text_color="#9ca3af",
            font=ctk.CTkFont(size=11),
        )
        self.lbl_info_pasta.pack(side="left", padx=(20, 0))

        # Área de Backup Automático
        auto_frame = ctk.CTkFrame(
            self,
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
            border_width=1,
            corner_radius=10,
        )
        auto_frame.pack(fill="x", padx=10, pady=(0, 10))

        self._ui_refs["auto_title_label"] = ctk.CTkLabel(
            auto_frame,
            text=self._get_text("auto_title"),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.cor_texto,
        )
        self._ui_refs["auto_title_label"].pack(anchor="w", padx=10, pady=(8, 4))

        # Configuração do backup automático
        config_frame = ctk.CTkFrame(auto_frame, fg_color=self.cor_fundo)
        config_frame.pack(fill="x", padx=10, pady=(0, 10))

        # Intervalo
        self._ui_refs["interval_label"] = ctk.CTkLabel(
            config_frame,
            text=self._get_text("interval"),
            text_color=self.cor_texto,
        )
        self._ui_refs["interval_label"].grid(row=0, column=0, sticky="w", padx=(0, 5), pady=5)

        self.interval_var = ctk.StringVar(value="3600")

        # Lista de intervalos como strings simples
        intervalos = ["3600", "21600", "43200", "86400", "172800", "604800"]
        interval_combo = ctk.CTkComboBox(
            config_frame,
            values=intervalos,
            variable=self.interval_var,
            width=150
        )
        interval_combo.grid(row=0, column=1, sticky="w", padx=(0, 20), pady=5)

        # Label para mostrar a descrição do intervalo selecionado
        self.lbl_intervalo_desc = ctk.CTkLabel(
            config_frame,
            text=self._get_text("every_hour"),
            text_color="#9ca3af",
            font=ctk.CTkFont(size=11),
        )
        self.lbl_intervalo_desc.grid(row=0, column=2, sticky="w", padx=(5, 20), pady=5)

        # Atualizar descrição quando o intervalo mudar
        interval_combo.configure(command=self._atualizar_descricao_intervalo)
        self._atualizar_descricao_intervalo(self.interval_var.get())

        # Pasta de destino
        self._ui_refs["folder_label"] = ctk.CTkLabel(
            config_frame,
            text=self._get_text("folder"),
            text_color=self.cor_texto,
        )
        self._ui_refs["folder_label"].grid(row=1, column=0, sticky="w", padx=(0, 5), pady=5)

        self.auto_pasta_var = ctk.StringVar(value="")
        self.entry_auto_pasta = ctk.CTkEntry(
            config_frame,
            textvariable=self.auto_pasta_var,
            width=300,
            placeholder_text=self._get_text("auto_folder_placeholder")
        )
        self.entry_auto_pasta.grid(row=1, column=1, columnspan=2, sticky="w", padx=(0, 10), pady=5)

        ctk.CTkButton(
            config_frame,
            text="📁",
            width=40,
            command=self._selecionar_pasta_auto
        ).grid(row=1, column=3, padx=(0, 10), pady=5)

        # Botões de controle
        control_frame = ctk.CTkFrame(auto_frame, fg_color=self.cor_fundo)
        control_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.btn_iniciar_auto = ctk.CTkButton(
            control_frame,
            text=self._get_text("start_auto"),
            fg_color="#059669",
            hover_color="#047857",
            text_color=self.cor_texto,
            command=self._iniciar_backup_auto,
            width=200
        )
        self._ui_refs["btn_iniciar_auto"] = self.btn_iniciar_auto
        self.btn_iniciar_auto.pack(side="left", padx=(0, 10))

        self.btn_parar_auto = ctk.CTkButton(
            control_frame,
            text=self._get_text("stop_auto"),
            fg_color="#dc2626",
            hover_color="#b91c1c",
            text_color=self.cor_texto,
            command=self._parar_backup_auto,
            width=200,
            state="disabled"
        )
        self._ui_refs["btn_parar_auto"] = self.btn_parar_auto
        self.btn_parar_auto.pack(side="left", padx=(0, 10))

        # Status do backup automático
        self.lbl_status_auto = ctk.CTkLabel(
            control_frame,
            text=self._get_text("auto_inactive"),
            text_color="#9ca3af",
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_executar_agora = ctk.CTkButton(
            control_frame,
            text=self._get_text("run_now"),
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            text_color=self.cor_texto,
            command=self._executar_backup_auto_agora,
            width=120
        )
        self._ui_refs["btn_executar_agora"] = self.btn_executar_agora
        self.btn_executar_agora.pack(side="right", padx=(10, 0))

        self.lbl_status_auto.pack(side="right", padx=(10, 0))

        # Log de mensagens
        log_frame = ctk.CTkFrame(
            self,
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
            border_width=1,
            corner_radius=10,
        )
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._ui_refs["log_title_label"] = ctk.CTkLabel(
            log_frame, text=self._get_text("log_title"), text_color=self.cor_texto
        )
        self._ui_refs["log_title_label"].pack(anchor="w", padx=10, pady=(8, 0))

        self.txt_log = ctk.CTkTextbox(
            log_frame,
            fg_color="#020617",
            text_color="#e5e7eb",
            border_width=0,
            corner_radius=10,
            height=220,
        )
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        self._log(self._get_text("backup_screen_loaded"))
        self._log(f"🔧 Configuração: {self.user}@{self.host}:{self.port}/{self.database}")
        self._atualizar_info_pasta()

    def _atualizar_descricao_intervalo(self, valor_selecionado):
        """Atualiza a descrição do intervalo selecionado"""
        descricoes = {
            "3600": self._get_text("every_hour"),
            "21600": self._get_text("every_6_hours"),
            "43200": self._get_text("every_12_hours"),
            "86400": self._get_text("daily"),
            "172800": self._get_text("every_2_days"),
            "604800": self._get_text("weekly")
        }
        descricao = descricoes.get(valor_selecionado, "")
        self.lbl_intervalo_desc.configure(text=descricao)

    #  Gerenciamento de Pastas
    def _criar_pasta_backups(self):
        """Versão interna usada pela página BACKUP"""
        try:
            base_dir = getattr(self.sistema, 'diretorio_base',
                               os.path.dirname(os.path.abspath(__file__)))

            self.pasta_backups = BackupPage.criar_pasta_backups_externo(base_dir)

            if self.pasta_backups:
                self.auto_pasta_var.set(self.pasta_backups)
                self._log(f"Pasta de backups: {self.pasta_backups}")

            return self.pasta_backups

        except Exception as e:
            self._log(f"Erro ao criar pasta de backups: {e}")
            return None

    def _garantir_pasta_existe(self, pasta):
        """Garante que a pasta existe antes do backup"""
        try:
            if not os.path.exists(pasta):
                os.makedirs(pasta, exist_ok=True)
                self._log(f"📁 Pasta criada: {pasta}")
            return True
        except Exception as e:
            self._log(f"❌ Erro ao criar pasta {pasta}: {e}")
            return False

    def _gerar_nome_backup(self, prefixo="backup"):
        """Gera nome único para backup com timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefixo}_opera_{timestamp}.sql"

    def _limpar_backups_antigos(self):
        """Remove backups antigos se exceder o limite de 300 arquivos"""
        try:
            # Garantir que a pasta existe
            if not self._garantir_pasta_existe(self.pasta_backups):
                return

            # Encontrar todos os arquivos .sql na pasta de backups
            padrao = os.path.join(self.pasta_backups, "backup_opera_*.sql")
            arquivos = glob.glob(padrao)

            # Ordenar por data de criação (mais antigos primeiro)
            arquivos.sort(key=os.path.getctime)

            # Verificar se precisa limpar
            if len(arquivos) > self._max_backups:
                # Calcular quantos arquivos remover
                remover_count = len(arquivos) - self._max_backups
                removidos = []

                for i in range(remover_count):
                    if i < len(arquivos):
                        arquivo = arquivos[i]
                        try:
                            os.remove(arquivo)
                            removidos.append(os.path.basename(arquivo))
                            if self.logger:
                                self.logger.info(f"[BACKUP] Removido backup antigo: {arquivo}")
                        except Exception as e:
                            self._log(f"⚠️  Erro ao remover {arquivo}: {e}")

                if removidos:
                    self._log(f"🧹 Limpeza automática: {len(removidos)} backups antigos removidos")
                    self._log(f"📊 Total atual: {len(arquivos) - remover_count}/{self._max_backups} backups")

        except Exception as e:
            self._log(f"⚠️  Erro na limpeza de backups antigos: {e}")

    def _contar_backups(self):
        """Conta quantos backups existens na pasta"""
        try:
            if not os.path.exists(self.pasta_backups):
                return 0

            padrao = os.path.join(self.pasta_backups, "backup_opera_*.sql")
            arquivos = glob.glob(padrao)
            return len(arquivos)
        except:
            return 0

    def _atualizar_info_pasta(self):
        """Atualiza informações da pasta na UI"""
        try:
            total = self._contar_backups()
            tamanho_pasta = self._calcular_tamanho_pasta()
            self.lbl_info_pasta.configure(text=self._get_text("backups_info", total=total, maximo=self._max_backups, tamanho=tamanho_pasta))
        except:
            pass

    def _calcular_tamanho_pasta(self):
        """Calcula o tamanho total da pasta de backups"""
        try:
            if not os.path.exists(self.pasta_backups):
                return "0 B"

            total_size = 0
            for dirpath, dirnames, filenames in os.walk(self.pasta_backups):
                for f in filenames:
                    if f.endswith('.sql'):
                        fp = os.path.join(dirpath, f)
                        total_size += os.path.getsize(fp)

            # Formatar tamanho
            for unit in ['B', 'KB', 'MB', 'GB']:
                if total_size < 1024.0:
                    return f"{total_size:.1f} {unit}"
                total_size /= 1024.0
            return f"{total_size:.1f} TB"
        except:
            return "0 B"

    # ------------------------------------------------------------------ Backup Automático
    def _selecionar_pasta_auto(self):
        """Seleciona a pasta para backup automático"""
        pasta = filedialog.askdirectory(
            title=self._get_text("select_auto_folder")
        )
        if pasta:
            self.auto_pasta_var.set(pasta)
            self._backup_auto_pasta = pasta
            self._log(f"Pasta de backup automático definida: {pasta}")

    def _iniciar_backup_auto(self):
        """Inicia o backup automático"""
        if not self.auto_pasta_var.get():
            # Usar pasta padrão se não selecionada
            self._backup_auto_pasta = self.pasta_backups
            self.auto_pasta_var.set(self.pasta_backups)
        else:
            self._backup_auto_pasta = self.auto_pasta_var.get()

        try:
            self._backup_auto_interval = int(self.interval_var.get())
        except ValueError:
            messagebox.showerror(
                self._get_text("error"),
                self._get_text("invalid_interval")
            )
            return

        # Garantir que a pasta existe
        if not self._garantir_pasta_existe(self._backup_auto_pasta):
            messagebox.showerror(
                "Erro",
                f"Não foi possível criar/acessar a pasta:\n{self._backup_auto_pasta}"
            )
            return

        self._backup_auto_running = True

        # Sincronizar estado global (garante funcionamento mesmo iniciado pela tela)
        global BACKUP_AUTO
        BACKUP_AUTO["running"] = True
        BACKUP_AUTO["interval"] = self._backup_auto_interval
        BACKUP_AUTO["pasta"] = self._backup_auto_pasta
        BACKUP_AUTO["proximo"] = time.time() + self._backup_auto_interval

        # Atualizar UI
        self.btn_iniciar_auto.configure(state="disabled")
        self.btn_parar_auto.configure(state="normal")
        self.entry_auto_pasta.configure(state="disabled")
        self.lbl_status_auto.configure(
            text=f"Backup automático: ATIVO (próximo: {self._formatar_tempo(self._backup_auto_interval)})",
            text_color="#4ade80"
        )

        self._log(f"✅ Backup automático INICIADO - Intervalo: {self._formatar_tempo(self._backup_auto_interval)}")
        self._log(f"📁 Pasta: {self._backup_auto_pasta}")

        # Iniciar thread do backup automático (somente se necessário)
        thread_global = BACKUP_AUTO.get("thread")
        if not (thread_global and thread_global.is_alive()):
            self._backup_auto_thread = threading.Thread(
                target=self._loop_backup_auto,
                daemon=True
            )
            BACKUP_AUTO["thread"] = self._backup_auto_thread
            self._backup_auto_thread.start()
        else:
            self._backup_auto_thread = thread_global

    def _parar_backup_auto(self):
        """Para o backup automático"""
        self._backup_auto_running = False

        # Parar também no estado global para encerrar o loop iniciado no login
        global BACKUP_AUTO
        BACKUP_AUTO["running"] = False
        BACKUP_AUTO["proximo"] = None

        # Atualizar UI
        self.btn_iniciar_auto.configure(state="normal")
        self.btn_parar_auto.configure(state="disabled")
        self.entry_auto_pasta.configure(state="normal")
        self.lbl_status_auto.configure(
            text=self._get_text("auto_inactive"),
            text_color="#9ca3af"
        )

        self._log("⏹ Backup automático PARADO")

    def _executar_backup_auto_agora(self):
        """Executa um backup automático imediatamente"""
        if not self._backup_auto_pasta:
            # Usar pasta padrão
            self._backup_auto_pasta = self.pasta_backups

        # Garantir que a pasta existe
        if not self._garantir_pasta_existe(self._backup_auto_pasta):
            messagebox.showerror(
                "Erro",
                f"Não foi possível criar/acessar a pasta:\n{self._backup_auto_pasta}"
            )
            return

        if self._backup_thread and self._backup_thread.is_alive():
            messagebox.showinfo(
                self._get_text("backup_title"),
                self._get_text("backup_already_running")
            )
            return

        self._log("⚡ Executando backup automático agora...")
        self._executar_backup_automatico()

    def _loop_backup_auto(self):
        """Loop principal do backup automático - compatível com inicialização pelo MENU"""
        global BACKUP_AUTO

        while BACKUP_AUTO.get("running", False):  # Usa a variável global como controle
            try:
                # Atualizar estado interno
                self._backup_auto_running = True

                # Calcular próximo backup
                self._proximo_backup_auto = time.time() + self._backup_auto_interval
                BACKUP_AUTO["proximo"] = self._proximo_backup_auto

                # Atualizar UI com contagem regressiva (se a UI estiver ativa)
                if hasattr(self, 'lbl_status_auto') and self.lbl_status_auto.winfo_exists():
                    self._atualizar_contagem_regressiva()

                # Aguardar até o próximo backup
                tempo_restante = self._proximo_backup_auto - time.time()
                while tempo_restante > 0 and BACKUP_AUTO.get("running", False):
                    time.sleep(min(60, tempo_restante))  # Atualizar a cada minuto
                    tempo_restante = self._proximo_backup_auto - time.time()

                    # Atualizar UI apenas se estiver ativa
                    if hasattr(self, 'lbl_status_auto') and self.lbl_status_auto.winfo_exists():
                        self._atualizar_contagem_regressiva()

                if BACKUP_AUTO.get("running", False):
                    self._executar_backup_automatico()

            except Exception as e:
                print(f"❌ Erro no loop de backup automático: {e}")
                if self.logger:
                    self.logger.error(f"[BACKUP AUTO] Erro no loop: {e}")
                time.sleep(60)  # Esperar 1 minuto antes de tentar novamente

        # Atualizar estado quando sair do loop
        self._backup_auto_running = False
        BACKUP_AUTO["proximo"] = None

    def _atualizar_contagem_regressiva(self):
        """Atualiza a contagem regressiva na UI"""
        if not self._backup_auto_running or not self._proximo_backup_auto:
            return

        tempo_restante = self._proximo_backup_auto - time.time()
        if tempo_restante > 0:
            texto = f"Backup automático: ATIVO (próximo em {self._formatar_tempo(tempo_restante)})"
            self.after(0, lambda: self.lbl_status_auto.configure(text=texto))

    def _executar_backup_automatico(self):
        """Executa um backup automático"""
        if not self._backup_auto_pasta or not self._backup_auto_running:
            return

        # Verificar se já existe um backup em andamento
        if self._backup_thread and self._backup_thread.is_alive():
            self._log("⚠️  Backup automático adiado - já existe um backup em andamento")
            return

        # Garantir que a pasta existe
        if not self._garantir_pasta_existe(self._backup_auto_pasta):
            self._log("❌ Não foi possível acessar a pasta de backups automáticos")
            return

        # Gerar nome único para o backup
        nome_arquivo = self._gerar_nome_backup("auto")
        caminho_completo = os.path.join(self._backup_auto_pasta, nome_arquivo)

        self._log(f"🔄 Iniciando backup automático: {nome_arquivo}")

        # Executar backup na thread
        self._backup_thread = threading.Thread(
            target=self._executar_backup_thread,
            args=(caminho_completo, True),  # True = é automático
            daemon=True,
        )
        self._backup_thread.start()

        # Função para iniciar automático silencioso

    def iniciar_backup_automatico_silencioso(self):
        global BACKUP_AUTOMATICO_GLOBAL
        BACKUP_AUTOMATICO_GLOBAL["running"] = True
        try:
            BACKUP_AUTOMATICO_GLOBAL["interval"] = int(self.interval_var.get())
        except:
            BACKUP_AUTOMATICO_GLOBAL["interval"] = 3600
        BACKUP_AUTOMATICO_GLOBAL["pasta"] = self.pasta_backups

        self._backup_auto_running = True
        self._backup_auto_interval = BACKUP_AUTOMATICO_GLOBAL["interval"]
        self._backup_auto_pasta = BACKUP_AUTOMATICO_GLOBAL["pasta"]

        self._backup_auto_thread = threading.Thread(
            target=self._loop_backup_auto, daemon=True)
        self._backup_auto_thread.start()

    def _formatar_tempo(self, segundos):
        """Formata tempo em segundos para string legível"""
        if segundos < 60:
            return f"{int(segundos)}s"
        elif segundos < 3600:
            return f"{int(segundos / 60)}min"
        elif segundos < 86400:
            return f"{int(segundos / 3600)}h"
        else:
            return f"{int(segundos / 86400)}d"

    # ------------------------------------------------------------------ Banco / status
    def _check_db_ready(self):
        """Verifica se o banco está pronto - com detecção automática de porta"""
        ok = False
        detalhes = ""

        self._log(f"🔍 Verificando conexão na porta {self.port}...")

        try:
            # 🎯 MÉTODO 1: Ready_check nativo
            try:
                ok = bool(ready_check())
                if ok:
                    detalhes = f"✅ Banco conectado via ready_check() na porta {self.port}"
                    self._log(detalhes)
                else:
                    detalhes = f"⚠️ Ready_check retornou False na porta {self.port}"
                    self._log(detalhes)
            except Exception as ready_e:
                detalhes = f"⚠️ Ready_check falhou na porta {self.port}: {str(ready_e)}"
                self._log(detalhes)

            # 🎯 MÉTODO 2: Conexão direta universal
            if not ok:
                try:
                    import psycopg2
                    self._log(f"🔄 Tentando conexão direta em {self.host}:{self.port}...")

                    # Configuração compatível com ambos OS
                    conn = psycopg2.connect(
                        host=self.host,
                        port=self.port,
                        database=self.database,
                        user=self.user,
                        password=self.password,
                        connect_timeout=5
                    )

                    # Teste universal (funciona em qualquer OS)
                    with conn.cursor() as cur:
                        cur.execute("SELECT version();")
                        result = cur.fetchone()
                        if result:
                            ok = True
                            # Extrai info da versão do PostgreSQL
                            versao = result[0].split(',')[0] if result[0] else "PostgreSQL"
                            detalhes = f"✅ Conexão direta OK na porta {self.port} - {versao}"
                            self._log(detalhes)
                        else:
                            detalhes = f"⚠️ Conexão OK na porta {self.port} mas sem resposta"
                            self._log(detalhes)

                    conn.close()

                except psycopg2.OperationalError as op_e:
                    # Tratamento específico para erros de conexão
                    erro_str = str(op_e)
                    if "connection refused" in erro_str.lower():
                        detalhes = f"❌ Conexão recusada na porta {self.port}"
                        # 🚨 TENTA PORTAS ALTERNATIVAS AUTOMATICAMENTE
                        self._tentar_portas_alternativas()
                    elif "password authentication" in erro_str.lower() or "no password supplied" in erro_str.lower():
                        detalhes = f"❌ Erro de autenticação na porta {self.port}"
                    elif "database" in erro_str.lower() and "does not exist" in erro_str.lower():
                        detalhes = f"❌ Banco '{self.database}' não existe na porta {self.port}"
                    elif "timeout" in erro_str.lower():
                        detalhes = f"❌ Timeout na conexão da porta {self.port}"
                    else:
                        detalhes = f"❌ Erro de conexão na porta {self.port}: {erro_str}"

                    self._log(detalhes)

                except psycopg2.Error as pg_e:
                    detalhes = f"❌ Erro PostgreSQL na porta {self.port}: {str(pg_e)}"
                    self._log(detalhes)
                except Exception as direct_e:
                    detalhes = f"❌ Erro na conexão direta na porta {self.port}: {str(direct_e)}"
                    self._log(detalhes)

        except Exception as e:
            ok = False
            detalhes = f"❌ Erro geral na verificação da porta {self.port}: {str(e)}"
            self._log(detalhes)

        # 🎯 ATUALIZAÇÃO DE UI
        if ok:
            self.lbl_status.configure(
                text=f"✅ Banco: CONECTADO (porta {self.port})",
                text_color="#4ade80",
            )
            self.btn_backup.configure(state="normal")

        else:
            self.lbl_status.configure(
                text=f"⚠️ Banco: INDISPONÍVEL (porta {self.port})",
                text_color="#f97316",
            )
            self.btn_backup.configure(state="disabled")

    def _tentar_portas_alternativas(self):
        """Tenta automaticamente portas alternativas se a padrão falhar"""
        portas_alternativas = [5433, 5434, 5435, 5432]  # Ordem de tentativa

        for porta in portas_alternativas:
            if porta == self.port:  # Pula a porta que já testamos
                continue

            self._log(f"🔄 Tentando porta alternativa {porta}...")
            try:
                import psycopg2
                conn = psycopg2.connect(
                    host=self.host,
                    port=porta,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    connect_timeout=3
                )
                conn.close()

                # 🎯 ATUALIZA A PORTA CORRETA
                self.port = porta
                CONFIG["ports"] = [porta]
                global ENDPOINTS
                ENDPOINTS = [(self.host, porta)]

                self._log(f"✅ Porta {porta} funcionou! Atualizando configuração...")

                # Atualiza UI
                self.after(0, self._atualizar_ui_porta_correta)
                return True

            except:
                continue

        self._log("❌ Nenhuma porta alternativa funcionou")
        return False

    def _atualizar_ui_porta_correta(self):
        """Atualiza a UI quando uma porta alternativa é encontrada"""
        self.lbl_status.configure(
            text=f"✅ Banco: CONECTADO (porta {self.port} detectada)",
            text_color="#4ade80",
        )
        self.btn_backup.configure(state="normal")

        # Atualiza informações na UI
        if hasattr(self, 'txt_log'):
            self._log(f"🔧 Configuração atualizada: {self.user}@{self.host}:{self.port}/{self.database}")

    # ------------------------------------------------------------------ Localização do pg_dump
    def _detectar_pg_dump_universal(self):
        candidates = []

        # 1) Variável de ambiente
        env_path = os.environ.get("PG_DUMP_PATH")
        if env_path:
            candidates.append(env_path)

        # 2) Atributo no sistema (definido no MENU_PRINCIPAL)
        if self.sistema is not None:
            custom_attr = getattr(self.sistema, "pg_dump_path", None)
            if custom_attr:
                candidates.append(custom_attr)

        # 3) Caminhos específicos por SO (ordenados por versão mais nova primeiro)
        if sys.platform == "darwin":  # macOS
            candidates.extend([
                "/Library/PostgreSQL/18/bin/pg_dump",
                "/Library/PostgreSQL/17/bin/pg_dump",
                "/Library/PostgreSQL/16/bin/pg_dump",
                "/Library/PostgreSQL/15/bin/pg_dump",
                "/Library/PostgreSQL/14/bin/pg_dump",

                "/Applications/Postgres.app/Contents/Versions/latest/bin/pg_dump",
                "/Applications/Postgres.app/Contents/Versions/18/bin/pg_dump",
                "/Applications/Postgres.app/Contents/Versions/17/bin/pg_dump",
                "/Applications/Postgres.app/Contents/Versions/16/bin/pg_dump",
                "/Applications/Postgres.app/Contents/Versions/15/bin/pg_dump",
                "/Applications/Postgres.app/Contents/Versions/14/bin/pg_dump",

                "/opt/homebrew/bin/pg_dump",
                "/usr/local/bin/pg_dump",
            ])

        elif os.name == "nt":  # Windows
            drives = ["C:", "D:", "E:"]
            versions = ["18", "17", "16", "15", "14", "13", "12"]

            for drive in drives:
                for version in versions:
                    candidates.extend([
                        f"{drive}\\Program Files\\PostgreSQL\\{version}\\bin\\pg_dump.exe",
                        f"{drive}\\Program Files (x86)\\PostgreSQL\\{version}\\bin\\pg_dump.exe",
                    ])

                candidates.extend([
                    f"{drive}\\PostgreSQL\\bin\\pg_dump.exe",
                    f"{drive}\\Program Files\\PostgreSQL\\bin\\pg_dump.exe",
                ])

        else:  # Linux / outros POSIX
            candidates.extend([
                "/usr/lib/postgresql/18/bin/pg_dump",
                "/usr/lib/postgresql/17/bin/pg_dump",
                "/usr/lib/postgresql/16/bin/pg_dump",
                "/usr/lib/postgresql/15/bin/pg_dump",
                "/usr/lib/postgresql/14/bin/pg_dump",

                "/usr/bin/pg_dump",
                "/usr/local/bin/pg_dump",
                "/bin/pg_dump",
            ])

        # 4) Fallback - pg_dump no PATH
        candidates.append("pg_dump")

        # Testar cada candidato
        for path in candidates:
            if self._testar_pg_dump(path):
                return path

        return "pg_dump"

    def _testar_pg_dump(self, path):
        try:
            if os.path.isabs(path) and not os.path.exists(path):
                return False

            result = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                shell=(os.name == 'nt')
            )

            return result.returncode == 0

        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError, Exception):
            return False

    def _get_pg_dump_executable(self):
        pg_dump_path = self._detectar_pg_dump_universal()
        self._pg_dump_candidates_last = self._obter_todos_caminhos_candidatos()

        if self.logger:
            versao = self._obter_versao_pg_dump(pg_dump_path)
            self.logger.info(f"[BACKUP] pg_dump detectado: {pg_dump_path} ({versao})")

        return pg_dump_path

    def _obter_todos_caminhos_candidatos(self):
        candidates = []
        if sys.platform == "darwin":
            candidates.extend([
                "/Library/PostgreSQL/18/bin/pg_dump",
                "/Library/PostgreSQL/17/bin/pg_dump",
                "/Library/PostgreSQL/16/bin/pg_dump",
                "/Applications/Postgres.app/Contents/Versions/latest/bin/pg_dump",
                "/opt/homebrew/bin/pg_dump",
                "/usr/local/bin/pg_dump",
            ])
        elif os.name == "nt":
            candidates.extend([
                "C:\\Program Files\\PostgreSQL\\18\\bin\\pg_dump.exe",
                "C:\\Program Files\\PostgreSQL\\17\\bin\\pg_dump.exe",
                "C:\\Program Files\\PostgreSQL\\16\\bin\\pg_dump.exe",
            ])
        else:
            candidates.extend([
                "/usr/lib/postgresql/18/bin/pg_dump",
                "/usr/lib/postgresql/17/bin/pg_dump",
                "/usr/bin/pg_dump",
            ])

        candidates.append("pg_dump")
        return candidates

    def _obter_versao_pg_dump(self, path):
        try:
            result = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                shell=(os.name == 'nt')
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "Versão desconhecida"

    # ------------------------------------------------------------------ Handlers
    def _on_backup_clicked(self):
        if self._backup_thread and self._backup_thread.is_alive():
            messagebox.showinfo(
                self._get_text("backup_title"),
                self._get_text("backup_already_running"),
            )
            return

        # Garantir que a pasta existe
        if not self._garantir_pasta_existe(self.pasta_backups):
            messagebox.showerror(
                "Erro",
                f"Não foi possível criar/acessar a pasta de backups:\n{self.pasta_backups}"
            )
            return

        # Gerar nome único para o backup
        nome_arquivo = self._gerar_nome_backup()
        caminho_completo = os.path.join(self.pasta_backups, nome_arquivo)

        self._log(f"Iniciando backup: {nome_arquivo}")
        self.btn_backup.configure(state="disabled", text="Gerando backup...")

        self._backup_thread = threading.Thread(
            target=self._executar_backup_thread,
            args=(caminho_completo, False),
            daemon=True,
        )
        self._backup_thread.start()

    # ------------------------------------------------------------------ Execução do backup
    # ------------------------------------------------------------------ Execução do backup
    def _executar_backup_thread(self, dest_path: str, is_automatico: bool = False):
        """
        Executa pg_dump em uma thread separada para não travar a interface.
        Compatível com macOS, Windows e Linux.
        Força o host=localhost para evitar erros de hostname inválido (".", "::1", "*", etc.).
        """
        # Verificar novamente se a pasta existe antes do backup
        pasta_destino = os.path.dirname(dest_path)
        if not self._garantir_pasta_existe(pasta_destino):
            erro_msg = f"Não foi possível criar/acessar a pasta: {pasta_destino}"
            self._log(f"❌ {erro_msg}")
            if not is_automatico:
                self.after(0, lambda: messagebox.showerror("Erro", erro_msg))
            return

        # Detectar pg_dump
        pg_dump_exe = self._get_pg_dump_executable()
        versao = self._obter_versao_pg_dump(pg_dump_exe)

        if not is_automatico:
            self._log(f"Usando pg_dump: {pg_dump_exe}")
            self._log(f"Versão: {versao}")

        if self.logger:
            self.logger.info(f"[BACKUP] Usando pg_dump: {pg_dump_exe} ({versao})")

        # 🔥 CORREÇÃO ABSOLUTA
        # Força host = localhost pois pg_dump falha com ".", "*" ou "::1"
        host_final = "localhost"

        # Montar comando do pg_dump
        cmd = [
            pg_dump_exe,
            "-h", host_final,
            "-p", str(self.port),  # Porta detectada automaticamente
            "-U", str(self.user),
            "-F", "p",  # formato plain text
            "-d", str(self.database),
            "-f", dest_path,
            "--verbose",
        ]

        # Variáveis de ambiente (senha)
        env = os.environ.copy()
        if self.password:
            env["PGPASSWORD"] = str(self.password)

        # Log seguro sem mostrar senha
        if self.logger and not is_automatico:
            cmd_log = cmd.copy()
            try:
                cmd_log[cmd_log.index("-U") + 1] = "***"
            except:
                pass
            self.logger.info(f"[BACKUP] Comando: {' '.join(cmd_log)}")

        try:
            use_shell = os.name == "nt"

            self._log(f"🔧 Executando backup na porta {self.port}...")

            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                shell=use_shell,
                timeout=300
            )

            if proc.returncode == 0:
                tamanho = self._formatar_tamanho_arquivo(dest_path)

                if is_automatico:
                    self._log(f"✅ Backup automático concluído: {os.path.basename(dest_path)} ({tamanho})")
                else:
                    self._log(f"✅ Backup concluído: {os.path.basename(dest_path)} ({tamanho})")

                if self.logger:
                    self.logger.info(f"[BACKUP] Backup gerado: {dest_path} ({tamanho})")

                self._ultimo_backup = dest_path

                self._limpar_backups_antigos()
                self.after(0, self._atualizar_info_pasta)

                if not is_automatico:
                    total = self._contar_backups()
                    self.after(
                        0,
                        lambda: messagebox.showinfo(
                            "Backup Concluído",
                            (
                                "✅ Backup concluído com sucesso!\n\n"
                                f"📁 Arquivo: {os.path.basename(dest_path)}\n"
                                f"📊 Tamanho: {tamanho}\n"
                                f"🔧 Porta usada: {self.port}\n"
                                f"📈 Total de backups: {total}/{self._max_backups}\n\n"
                                f"📍 Local: {dest_path}"
                            ),
                        ),
                    )

                return

            # ❌ erro no pg_dump
            msg = (proc.stderr or "Erro desconhecido ao executar pg_dump.").strip()

            if is_automatico:
                self._log(f"❌ ERRO no backup automático: {msg}")
            else:
                self._log(f"❌ ERRO no backup: {msg}")

            if self.logger:
                self.logger.error(f"[BACKUP] Erro no pg_dump: {msg}")

            if (
                    not is_automatico
                    and "connection" in msg.lower()
                    and "refused" in msg.lower()
            ):
                self._log("🔄 Tentando porta alternativa...")
                original = self.port
                if self._tentar_portas_alternativas():
                    self._log(f"🟢 Porta corrigida para {self.port}. Execute novamente.")
                    self.after(
                        0,
                        lambda: messagebox.showwarning(
                            "Porta Corrigida",
                            f"Porta corrigida automaticamente!\nAnterior: {original}\nAtual: {self.port}",
                        ),
                    )
                    return

            if not is_automatico:
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        "Erro no Backup",
                        f"❌ Falha ao executar pg_dump:\n\n{msg}\n\n"
                        f"Verifique:\n"
                        f"• Porta do PostgreSQL ({self.port})\n"
                        f"• Usuário e senha\n"
                        f"• Host: localhost\n"
                        f"• Permissões\n"
                        f"• Espaço em disco",
                    ),
                )

        except subprocess.TimeoutExpired:
            erro = "Backup expirou (timeout de 5 minutos)"

            if is_automatico:
                self._log(f"❌ {erro}")
            else:
                self._log(f"❌ {erro}")

            if self.logger:
                self.logger.error(f"[BACKUP] {erro}")

            if not is_automatico:
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        "Timeout",
                        "O backup demorou muito e foi cancelado.\n\n"
                        f"Porta usada: {self.port}"
                    ),
                )

        except FileNotFoundError:
            caminhos = "\n".join(self._pg_dump_candidates_last or ["pg_dump"])
            msg = (
                "pg_dump não encontrado.\n\n"
                "Caminhos verificados:\n"
                f"{caminhos}\n\n"
                "Soluções:\n"
                "• Instalar PostgreSQL Client\n"
                "• Colocar pg_dump no PATH\n"
                "• Configurar PG_DUMP_PATH\n"
            )

            if is_automatico:
                self._log("❌ pg_dump não encontrado")
            else:
                self._log(msg)

            if self.logger:
                self.logger.error("[BACKUP] pg_dump não encontrado")

            if not is_automatico:
                self.after(0, lambda: messagebox.showerror("pg_dump não encontrado", msg))

        except Exception as e:
            import traceback
            tb = traceback.format_exc()

            if is_automatico:
                self._log(f"❌ Exceção: {e}")
            else:
                self._log(f"❌ Exceção: {e}")

            if self.logger:
                self.logger.error(f"[BACKUP] Exceção: {e}\n{tb}")

            if not is_automatico:
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        "Erro inesperado",
                        f"Ocorreu um erro inesperado:\n\n{str(e)}"
                    ),
                )

        finally:
            if not is_automatico:
                self.after(
                    0,
                    lambda: self.btn_backup.configure(
                        state="normal",
                        text=self._get_text("backup_now"),
                    ),
                )

    def _formatar_tamanho_arquivo(self, filepath):
        try:
            size = os.path.getsize(filepath)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        except:
            return self._get_text("unknown_size")

    # ------------------------------------------------------------------ Utilidades
    def _abrir_pasta_backups(self):
        """Abre a pasta de backups"""
        try:
            # Garantir que a pasta existe
            self._garantir_pasta_existe(self.pasta_backups)

            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", self.pasta_backups])
            elif os.name == "nt":  # Windows
                subprocess.run(["explorer", self.pasta_backups])
            else:  # Linux / outros
                subprocess.run(["xdg-open", self.pasta_backups])

            self._log(f"📂 Pasta de backups aberta: {self.pasta_backups}")
        except Exception as e:
            messagebox.showerror(
                "Erro",
                f"Não foi possível abrir a pasta:\n\n{str(e)}",
            )

    def _log(self, msg):
        """Adiciona mensagem ao log da interface"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_log.insert("end", f"[{timestamp}] {msg}\n")
        self.txt_log.see("end")

        if self.logger:
            self.logger.info(f"[BACKUP] {msg}")

    # ------------------------------------------------------------------ Cleanup
    def destroy(self):
        """Cleanup ao fechar a página"""
        self._backup_auto_running = False
        super().destroy()

# ------------------------------------------------------------------ Teste isolado
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Backup - Teste")
    root.geometry("900x700")

    class SistemaMock:
        def __init__(self):
            self.cor_fundo = "#0f172a"
            self.cor_texto = "#e5e7eb"
            self.cor_borda = "#334155"
            self.cor_primaria = "#1f538d"
            self.cor_hover = "#14375e"
            self.cor_selecao = "#223649"
            self.diretorio_base = os.path.dirname(os.path.abspath(__file__))

    sistema_mock = SistemaMock()
    pagina = BackupPage(root, sistema=sistema_mock)

    root.mainloop()

#teste saber se esta igual
