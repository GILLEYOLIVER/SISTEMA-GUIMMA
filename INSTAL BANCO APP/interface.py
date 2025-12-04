# -*- coding: utf-8 -*-
import os
import sys
import time
import subprocess
from typing import Dict  # 🔥 ADICIONE ESTE IMPORT
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QListWidget, QTextEdit, QLineEdit, QDialog,
    QMessageBox, QComboBox, QGroupBox, QSplitter, QFrame, QTabWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QPalette, QColor

# ================================================================
# 🧵 Thread de execução (CORRIGIDA)
# ================================================================
# ================================================================
# 🧵 Thread de execução (COMPLETA E ATUALIZADA)
# ================================================================
# ================================================================
# 🧵 Thread de execução (COMPLETA E ATUALIZADA)
# ================================================================
class WorkerThread(QThread):
    # 🔥 SINAIS PRINCIPAIS
    finished = pyqtSignal(bool, str)  # success, message
    success_dialog = pyqtSignal(int, str, str)  # total_tabelas, message, script_type
    switch_database = pyqtSignal(str)  # database_name
    progress_update = pyqtSignal(str)  # progress_message
    log_message = pyqtSignal(str)  # log_message
    connection_test_result = pyqtSignal(bool, str)  # success, message (para teste de conexão)
    database_check_result = pyqtSignal(bool, str, int)  # exists, message, table_count (para verificação de banco)

    # 🔥 SINAIS DE ANÁLISE DETALHADA
    script_analysis_start = pyqtSignal(str)  # script_name
    table_count_update = pyqtSignal(int)  # current_table_count
    execution_step = pyqtSignal(str)  # step_description

    def __init__(self, db_manager, task_type, password, script_name=None, database=None, user=None, port=None):
        """
        Inicializa a thread de trabalho

        Args:
            db_manager: Instância do DatabaseManager
            task_type: Tipo de tarefa ("install_script", "test_connection", "check_database")
            password: Senha do PostgreSQL
            script_name: Nome do script (apenas para install_script)
            database: Banco de dados alvo
            user: Usuário do PostgreSQL
            port: Porta do PostgreSQL
        """
        super().__init__()
        self.db_manager = db_manager
        self.task_type = task_type
        self.password = password
        self.script_name = script_name
        self.database = database
        self.user = user or "postgres"
        self.port = port

        # 🔧 Estado interno
        self.is_running = False
        self.script_output = ""
        self.execution_time = 0
        self.tables_created = 0
        self.error_details = ""

        # 🔧 Configurações de timeout
        self.timeout_seconds = 300  # 5 minutos padrão

    def run(self):
        """Método principal executado na thread"""
        self.is_running = True
        start_time = time.time()

        try:
            self.log_message.emit(f"🧵 Thread iniciada para: {self.task_type}")

            if self.task_type == "install_script":
                self._execute_script_installation()

            elif self.task_type == "test_connection":
                self._execute_connection_test()

            elif self.task_type == "check_database":
                self._execute_database_check()

            elif self.task_type == "count_tables":
                self._execute_table_count()

            else:
                self.finished.emit(False, f"Tipo de tarefa desconhecido: {self.task_type}")

        except Exception as e:
            error_msg = f"❌ Erro crítico na thread: {str(e)}"
            self.log_message.emit(error_msg)
            self.finished.emit(False, error_msg)

        finally:
            self.execution_time = time.time() - start_time
            self.is_running = False
            self.log_message.emit(f"🧵 Thread finalizada em {self.execution_time:.2f}s")

    def _execute_script_installation(self):
        """Executa a instalação de um script SQL"""
        if not self.script_name:
            self.finished.emit(False, "Nome do script não fornecido")
            return

        self.script_analysis_start.emit(self.script_name)
        self.log_message.emit(f"🔄 Iniciando execução do script: {self.script_name}")
        self.progress_update.emit("Preparando ambiente")

        # 🔧 PRÉ-VALIDAÇÃO PARA SCRIPTS 2 E 3
        if self.script_name in ["2_CRIAR_SCHEMA.sql", "3_CRIAR_TABELAS.sql"]:
            self.progress_update.emit("Verificando pré-requisitos")
            self.log_message.emit("🔍 Verificando existência do banco BANCO_OPERA...")

            db_exists = self.db_manager.check_database_exists("BANCO_OPERA", self.password, self.user, self.port)
            if not db_exists:
                error_msg = "❌ Banco BANCO_OPERA não existe. Execute o script 1_CRIAR_BANCO.sql primeiro."
                self.log_message.emit(error_msg)
                self.finished.emit(False, error_msg)
                return

        # 🚀 EXECUTAR SCRIPT
        self.progress_update.emit("Executando script SQL")
        success, message = self.db_manager.execute_sql_file(
            self.script_name, self.password,
            database=self.database, user=self.user, port=self.port
        )

        # 📊 PÓS-EXECUÇÃO - CONTAGEM DE TABELAS
        table_count = 0
        if success and self.database == "BANCO_OPERA":
            self.progress_update.emit("Contando tabelas criadas")
            table_count = self.db_manager.count_tables(self.password, self.user, self.port, "BANCO_OPERA")
            self.table_count_update.emit(table_count)
            self.log_message.emit(f"📊 Tabelas encontradas no schema opera: {table_count}")

        # 🎯 PROCESSAR RESULTADO
        if success:
            self._handle_successful_execution(table_count, message)
        else:
            self._handle_failed_execution(message)

        self.finished.emit(success, message)

    def _handle_successful_execution(self, table_count, message):
        """Processa execução bem-sucedida do script"""
        script_type = self._determine_script_type()

        # 🔄 MUDANÇA AUTOMÁTICA DE BANCO APÓS SCRIPT 1
        if self.script_name == "1_CRIAR_BANCO.sql":
            self.switch_database.emit("BANCO_OPERA")
            self.log_message.emit("🔄 Banco alterado automaticamente para BANCO_OPERA")

        # 🔥 CONFIRMAÇÃO DETALHADA APENAS PARA SCRIPT 3
        if self.script_name == "3_CRIAR_TABELAS.sql":
            if hasattr(self.db_manager, 'confirm_table_creation'):
                try:
                    self.progress_update.emit("Obtendo confirmação detalhada")
                    confirmation = self.db_manager.confirm_table_creation(
                        self.password, self.user, self.port, "BANCO_OPERA"
                    )

                    if "total_tabelas" in confirmation:
                        table_count = confirmation["total_tabelas"]
                        if table_count >= 40:
                            message = f"✅ SISTEMA COMPLETO! {table_count} tabelas criadas"
                        else:
                            message = f"✅ {table_count} tabelas criadas com sucesso"

                except Exception as e:
                    self.log_message.emit(f"⚠️ Aviso na confirmação: {e}")
            else:
                self.log_message.emit("ℹ️  Método de confirmação não disponível")

        # 📨 EMITIR SINAL DE SUCESSO
        self.success_dialog.emit(table_count, message, script_type)
        self.log_message.emit(f"✅ {message}")

    def _handle_failed_execution(self, message):
        """Processa execução com falha do script"""
        self.error_details = message
        self.log_message.emit(f"❌ Falha na execução: {message}")

        # 🔧 ANÁLISE DE ERRO PARA SUGESTÕES
        error_lower = message.lower()
        if "does not exist" in error_lower and "banco_opera" in error_lower:
            self.log_message.emit("💡 SOLUÇÃO: Execute o script 1_CRIAR_BANCO.sql primeiro")
        elif "password authentication failed" in error_lower:
            self.log_message.emit("💡 SOLUÇÃO: Verifique a senha do PostgreSQL")
        elif "cannot connect" in error_lower:
            self.log_message.emit("💡 SOLUÇÃO: Verifique se o PostgreSQL está rodando")
        elif "timeout" in error_lower:
            self.log_message.emit("💡 SOLUÇÃO: Script muito longo, aumente o timeout")

    def _execute_connection_test(self):
        """Executa teste de conexão com o banco"""
        self.progress_update.emit("Testando conexão PostgreSQL")
        self.log_message.emit(f"🔍 Testando conexão com {self.database}...")

        success, message = self.db_manager.test_connection(
            self.password, database=self.database, user=self.user, port=self.port
        )

        # 📨 EMITIR RESULTADO ESPECÍFICO PARA TESTE DE CONEXÃO
        self.connection_test_result.emit(success, message)
        self.finished.emit(success, message)

    def _execute_database_check(self):
        """Verifica existência e estado do banco"""
        self.progress_update.emit("Verificando banco de dados")
        self.log_message.emit(f"📊 Verificando banco: {self.database}")

        exists = self.db_manager.check_database_exists(self.database, self.password, self.user, self.port)

        # 📊 CONTAGEM DE TABELAS SE O BANCO EXISTIR
        table_count = 0
        if exists and self.database == "BANCO_OPERA":
            table_count = self.db_manager.count_tables(self.password, self.user, self.port, "BANCO_OPERA")
            self.log_message.emit(f"📋 Tabelas no schema opera: {table_count}")

        message = f"Banco {self.database} {'existe' if exists else 'não existe'}"

        # 📨 EMITIR RESULTADO ESPECÍFICO PARA VERIFICAÇÃO
        self.database_check_result.emit(exists, message, table_count)
        self.finished.emit(exists, message)

    def _execute_table_count(self):
        """Executa apenas contagem de tabelas"""
        self.progress_update.emit("Contando tabelas")

        table_count = self.db_manager.count_tables(self.password, self.user, self.port, self.database)
        self.table_count_update.emit(table_count)

        message = f"📊 {table_count} tabelas encontradas no schema opera"
        self.finished.emit(True, message)

    def _determine_script_type(self):
        """Determina o tipo de script para mensagens personalizadas"""
        if not self.script_name:
            return "other"

        script_lower = self.script_name.lower()

        if script_lower == "1_criar_banco.sql":
            return "script_1"
        elif script_lower == "2_criar_schema.sql":
            return "script_2"
        elif script_lower == "3_criar_tabelas.sql":
            return "script_3"
        elif "apagar" in script_lower or "delete" in script_lower:
            return "cleanup"
        else:
            return "other"

    def stop_execution(self):
        """Para a execução da thread (se possível)"""
        if self.isRunning():
            self.terminate()
            self.wait(1000)  # Espera 1 segundo para terminar
            self.log_message.emit("⏹️ Execução interrompida pelo usuário")

    def get_execution_info(self):
        """Retorna informações sobre a execução atual"""
        return {
            "task_type": self.task_type,
            "script_name": self.script_name,
            "database": self.database,
            "user": self.user,
            "port": self.port,
            "is_running": self.is_running,
            "execution_time": self.execution_time,
            "tables_created": self.tables_created,
            "error_details": self.error_details
        }

    def is_script_execution(self):
        """Verifica se é uma execução de script"""
        return self.task_type == "install_script"

    def get_script_name(self):
        """Retorna o nome do script sendo executado"""
        return self.script_name


# ================================================================
# ✅ Diálogo de sucesso (COMPLETO E ATUALIZADO)
# ================================================================
# ================================================================
# ✅ Diálogo de sucesso (ÚNICO E CORRIGIDO)
# ================================================================
class SuccessDialog(QDialog):
    def __init__(self, parent=None, total_tabelas=0, message="", script_type=""):
        super().__init__(parent)
        self.setWindowTitle("🎉 SISTEMA OPERA CRIADO COM SUCESSO!")
        self.setFixedSize(800, 600)
        self.total_tabelas = total_tabelas
        self.message = message
        self.script_type = script_type
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        self.setStyleSheet("""
            QDialog {
                background: #0f1419;
                color: #ffffff;
                border: 3px solid #007bff;
                border-radius: 15px;
            }
            QLabel {
                color: #ffffff;
                background: transparent;
            }
            QPushButton {
                background: #007bff;
                color: #ffffff;
                border-radius: 10px;
                font-weight: bold;
                padding: 12px 25px;
                font-size: 14pt;
                min-width: 120px;
            }
            QPushButton:hover {
                background: #3399ff;
            }
        """)

        # Ícone de sucesso
        lbl_icon = QLabel("🎉")
        lbl_icon.setAlignment(Qt.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 50pt; margin: 10px;")
        layout.addWidget(lbl_icon)

        lbl_title = QLabel("SISTEMA OPERA CRIADO COM SUCESSO!")
        lbl_title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #007bff;")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Banco de dados configurado e pronto para uso")
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet("font-size: 12pt; color: #cccccc; margin-bottom: 10px;")
        layout.addWidget(lbl_sub)

        # Estatísticas - MENSAGEM DINÂMICA POR SCRIPT
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background: #1a1f25;
                border: 1px solid #2a2f35;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        stats_layout = QVBoxLayout(stats_frame)

        # 🔥 MENSAGEM DINÂMICA BASEADA NO TIPO DE SCRIPT
        if self.script_type == "script_1":
            lbl_achievement = QLabel("✅ BANCO BANCO_OPERA CRIADO COM SUCESSO!")
            lbl_achievement.setAlignment(Qt.AlignCenter)
            lbl_achievement.setStyleSheet("font-size: 16pt; font-weight: bold; color: #66b3ff;")
            stats_layout.addWidget(lbl_achievement)

            lbl_next_step = QLabel("➡️ PRÓXIMO PASSO: Execute o script 2_CRIAR_SCHEMA.sql")
            lbl_next_step.setAlignment(Qt.AlignCenter)
            lbl_next_step.setStyleSheet("font-size: 12pt; color: #99ccff; margin-top: 10px;")
            stats_layout.addWidget(lbl_next_step)

        elif self.script_type == "script_2":
            lbl_achievement = QLabel("✅ SCHEMA OPERA CONFIGURADO COM SUCESSO!")
            lbl_achievement.setAlignment(Qt.AlignCenter)
            lbl_achievement.setStyleSheet("font-size: 16pt; font-weight: bold; color: #66b3ff;")
            stats_layout.addWidget(lbl_achievement)

            if self.total_tabelas > 0:
                lbl_tables = QLabel(f"📊 TABELAS EXISTENTES: {self.total_tabelas}")
                lbl_tables.setAlignment(Qt.AlignCenter)
                lbl_tables.setStyleSheet("font-size: 14pt; color: #66b3ff; margin-top: 10px;")
                stats_layout.addWidget(lbl_tables)

            lbl_next_step = QLabel("➡️ PRÓXIMO PASSO: Execute o script 3_CRIAR_TABELAS.sql")
            lbl_next_step.setAlignment(Qt.AlignCenter)
            lbl_next_step.setStyleSheet("font-size: 12pt; color: #99ccff; margin-top: 10px;")
            stats_layout.addWidget(lbl_next_step)

        elif self.script_type == "script_3":
            lbl_achievement = QLabel("✅ SISTEMA OPERA CONFIGURADO COM SUCESSO!")
            lbl_achievement.setAlignment(Qt.AlignCenter)
            lbl_achievement.setStyleSheet("font-size: 16pt; font-weight: bold; color: #66b3ff;")
            stats_layout.addWidget(lbl_achievement)

            lbl_tables = QLabel(f"📊 TOTAL DE TABELAS CRIADAS: {self.total_tabelas}")
            lbl_tables.setAlignment(Qt.AlignCenter)
            lbl_tables.setStyleSheet("font-size: 16pt; font-weight: bold; color: #66b3ff; margin-top: 10px;")
            stats_layout.addWidget(lbl_tables)

            # Status baseado na quantidade de tabelas
            if self.total_tabelas >= 40:
                status_msg = "🚀 SISTEMA COMPLETO - PRONTO PARA PRODUÇÃO!"
                status_color = "#00ff88"
            elif self.total_tabelas >= 20:
                status_msg = "⚠️ SISTEMA PARCIAL - ALGUMAS TABELAS CRIADAS"
                status_color = "#ffaa00"
            elif self.total_tabelas > 0:
                status_msg = "🔧 SISTEMA BÁSICO - POUCAS TABELAS CRIADAS"
                status_color = "#ffcc00"
            else:
                status_msg = "❌ NENHUMA TABELA CRIADA - VERIFIQUE O SCRIPT"
                status_color = "#ff5555"

            lbl_status = QLabel(status_msg)
            lbl_status.setAlignment(Qt.AlignCenter)
            lbl_status.setStyleSheet(f"font-size: 14pt; color: {status_color}; margin-top: 10px; font-weight: bold;")
            stats_layout.addWidget(lbl_status)

        else:
            # Para outros scripts (APAGAR_TUDO, etc.)
            lbl_achievement = QLabel("✅ SCRIPT EXECUTADO COM SUCESSO!")
            lbl_achievement.setAlignment(Qt.AlignCenter)
            lbl_achievement.setStyleSheet("font-size: 16pt; font-weight: bold; color: #66b3ff;")
            stats_layout.addWidget(lbl_achievement)

            if self.total_tabelas > 0:
                lbl_tables = QLabel(f"📊 TABELAS NO SCHEMA OPERA: {self.total_tabelas}")
                lbl_tables.setAlignment(Qt.AlignCenter)
                lbl_tables.setStyleSheet("font-size: 14pt; color: #66b3ff; margin-top: 10px;")
                stats_layout.addWidget(lbl_tables)

        # Informações de configuração (sempre visíveis)
        lbl_info = QLabel("✅ Schema: opera\n✅ Usuário: GIL DE OLIVEIRA\n✅ Senha: 2580")
        lbl_info.setAlignment(Qt.AlignCenter)
        lbl_info.setStyleSheet("font-size: 11pt; color: #cccccc; margin-top: 15px;")
        stats_layout.addWidget(lbl_info)

        layout.addWidget(stats_frame)

        # Mensagem adicional do log (LIMPA E FILTRADA)
        if self.message:
            clean_message = self.clean_success_message(self.message, self.script_type)
            if clean_message:
                lbl_msg = QLabel(clean_message)
                lbl_msg.setWordWrap(True)
                lbl_msg.setAlignment(Qt.AlignCenter)
                lbl_msg.setStyleSheet(
                    "font-size: 10pt; color: #99ccff; background: #1a2f4a; padding: 10px; border-radius: 5px;")
                layout.addWidget(lbl_msg)

        layout.addStretch()

        # Botões
        btn_layout = QHBoxLayout()

        btn_ok = QPushButton("🎯 Fechar")
        btn_ok.clicked.connect(self.accept)
        btn_ok.setStyleSheet("font-size: 12pt;")

        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def clean_success_message(self, message, script_type):
        """Limpa e formata a mensagem de sucesso para evitar duplicação"""
        if not message:
            return ""

        # Remover mensagens genéricas duplicadas
        if "executado com sucesso" in message.lower():
            if script_type == "script_1":
                return "Banco BANCO_OPERA criado/preparado com sucesso!"
            elif script_type == "script_2":
                return "Schema opera configurado com sucesso!"
            elif script_type == "script_3":
                return f"{self.total_tabelas} tabelas criadas com sucesso!"
            else:
                return "Operação concluída com sucesso!"

        return message


# ================================================================
# 🔧 Métodos do DatabaseManager (COMPLETOS)
# ================================================================
def count_tables(self, password: str = None, user: str = "postgres",
                 port: str = None, database: str = "BANCO_OPERA") -> int:
    """Conta tabelas de forma mais robusta e precisa"""
    try:
        if not port:
            port = self._auto_detect_port()
            if not port:
                return 0

        psql_path = self._find_psql_path()
        if not psql_path:
            return 0

        if not password:
            config = self.get_connection_config()
            password = config.get("defaults", {}).get("password", "gil25802580")

        env = os.environ.copy()
        env["PGPASSWORD"] = password

        # 🔥 QUERY MAIS ROBUSTA PARA CONTAR TABELAS
        query = """
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_schema = 'opera' 
        AND table_type = 'BASE TABLE'
        AND table_name NOT LIKE 'pg_%'
        AND table_name NOT LIKE 'sql_%';
        """

        cmd = [
            psql_path, "-h", "localhost", "-U", user,
            "-p", str(port), "-d", database, "-c", query,
            "-t", "--quiet", "-A"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)

        if result.returncode == 0 and result.stdout.strip().isdigit():
            count = int(result.stdout.strip())
            print(f"📊 Contagem dinâmica de tabelas: {count} tabelas encontradas")
            return count
        return 0

    except Exception as e:
        print(f"❌ Erro ao contar tabelas: {e}")
        return 0


def confirm_table_creation(self, password: str = None, user: str = "postgres",
                           port: str = None, database: str = "BANCO_OPERA") -> Dict:
    """Confirmação final detalhada da criação das tabelas"""
    try:
        if not port:
            port = self._auto_detect_port()
            if not port:
                return {"error": "Porta não encontrada"}

        psql_path = self._find_psql_path()
        if not psql_path:
            return {"error": "psql não encontrado"}

        if not password:
            config = self.get_connection_config()
            password = config.get("defaults", {}).get("password", "gil25802580")

        env = os.environ.copy()
        env["PGPASSWORD"] = password

        # Query de confirmação final
        query = """
        SELECT 
            current_database() AS banco_atual,
            COUNT(*) as total_tabelas,
            string_agg(table_name, ', ' ORDER BY table_name) AS tabelas_criadas
        FROM information_schema.tables 
        WHERE table_schema = 'opera'
        AND table_type = 'BASE TABLE';
        """

        cmd = [
            psql_path, "-h", "localhost", "-U", user,
            "-p", str(port), "-d", database, "-c", query,
            "-t", "--quiet", "-A", "-F", "|"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)

        if result.returncode == 0:
            lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            if lines and '|' in lines[0]:
                parts = lines[0].split('|')
                if len(parts) >= 3:
                    return {
                        "banco_atual": parts[0],
                        "total_tabelas": int(parts[1]),
                        "tabelas_criadas": parts[2][:100] + "..." if len(parts[2]) > 100 else parts[2],
                        "status": f"✅ {parts[1]} TABELAS CRIADAS COM SUCESSO!"
                    }

        return {"error": "Não foi possível obter confirmação"}

    except Exception as e:
        return {"error": f"Erro na confirmação: {str(e)}"}


# ================================================================
# 🎯 Método execute_script (COMPLETO)
# ================================================================
def execute_script(self):
    """Executa o script SQL selecionado com banco automático correto"""
    selected = self.scripts_list.currentItem()
    if not selected:
        QMessageBox.warning(self, "⚠️ Aviso", "Nenhum script selecionado!")
        return

    script = selected.text()
    password = self.password_input.text().strip()
    user = self.user_input.text().strip()
    port = self.port_input.text().strip() or None

    # 🔥 CORREÇÃO CRÍTICA: Determinar o banco CORRETO para cada script
    # IGNORA a seleção atual do usuário e força o banco adequado
    if script == "1_CRIAR_BANCO.sql":
        database = "postgres"  # Script 1 SEMPRE no postgres
        self.log_html("💡 Script 1: Executando no banco POSTGRES (criação do BANCO_OPERA)")
    elif script == "2_CRIAR_SCHEMA.sql":
        database = "BANCO_OPERA"  # Script 2 SEMPRE no BANCO_OPERA
        self.log_html("💡 Script 2: Executando no banco BANCO_OPERA (configuração do schema)")
    elif script == "3_CRIAR_TABELAS.sql":
        database = "BANCO_OPERA"  # Script 3 SEMPRE no BANCO_OPERA
        self.log_html("💡 Script 3: Executando no banco BANCO_OPERA (criação de tabelas)")
    else:
        # Para outros scripts, usa BANCO_OPERA por padrão
        database = "BANCO_OPERA"
        self.log_html(f"💡 Script personalizado: Executando no banco BANCO_OPERA")

    # 🔄 ATUALIZAR VISUALMENTE o combobox para refletir o banco correto
    current_displayed_db = self.db_combo.currentText()
    if current_displayed_db != database:
        self.db_combo.setCurrentText(database)
        self.log_html(f"🔄 Banco alterado automaticamente: {current_displayed_db} → {database}")

    self.log_html(f"🚀 INICIANDO EXECUÇÃO: {script}")
    self.log_html(f"📁 Banco definido: {database}")
    self.log_html(f"👤 Usuário: {user}")
    self.log_html(f"🔌 Porta: {port or 'auto-detecção'}")

    # Feedback específico e detalhado por script
    if script == "1_CRIAR_BANCO.sql":
        self.log_html("🎯 OBJETIVO: Criar banco de dados BANCO_OPERA")
        self.log_html("💡 AÇÃO: Executando CREATE DATABASE no PostgreSQL")
    elif script == "2_CRIAR_SCHEMA.sql":
        self.log_html("🎯 OBJETIVO: Configurar schema OPERA no banco BANCO_OPERA")
        self.log_html("💡 AÇÃO: Criar extensões, schema, usuários e permissões")
    elif script == "3_CRIAR_TABELAS.sql":
        self.log_html("🎯 OBJETIVO: Criar tabelas do sistema Opera Fashion")
        self.log_html("💡 AÇÃO: Executar CREATE TABLE para todas as tabelas do sistema")
    else:
        self.log_html(f"🎯 OBJETIVO: Executar script personalizado {script}")

    # Mostrar barra de progresso indeterminada
    self.progress.setVisible(True)
    self.progress.setRange(0, 0)  # Progresso indeterminado
    self.progress.setFormat(f"Executando {script}... %p%")

    # 🔧 VERIFICAÇÃO PRÉ-EXECUÇÃO para scripts 2 e 3
    if script in ["2_CRIAR_SCHEMA.sql", "3_CRIAR_TABELAS.sql"]:
        self.log_html("🔍 Verificando pré-requisitos...")
        # Verificar se o banco BANCO_OPERA existe
        db_exists = self.db_manager.check_database_exists("BANCO_OPERA", password, user, port)
        if not db_exists:
            error_msg = f"❌ ERRO CRÍTICO: Banco BANCO_OPERA não existe!\n\nExecute o script 1_CRIAR_BANCO.sql primeiro."
            self.log_html(error_msg)
            self.progress.setVisible(False)
            QMessageBox.critical(self, "❌ Banco Não Encontrado", error_msg)
            return

    # 🧵 CRIAR E CONFIGURAR THREAD DE EXECUÇÃO
    self.worker = WorkerThread(
        db_manager=self.db_manager,
        task_type="install_script",
        password=password,
        script_name=script,
        database=database,  # 🔥 Banco CORRETO forçado
        user=user,
        port=port
    )

    # 🔗 CONECTAR SINAIS DA THREAD (ATUALIZADO)
    self.worker.finished.connect(self.on_exec_finished)
    self.worker.success_dialog.connect(self.show_success_dialog)
    self.worker.switch_database.connect(self.switch_to_banco_opera)
    self.worker.log_message.connect(self.log_html)
    self.worker.progress_update.connect(self.on_progress_update)

    # 🚀 INICIAR EXECUÇÃO
    self.log_html("⏳ Iniciando processo de execução...")

    # Desabilitar botões durante execução
    self.set_buttons_enabled(False)

    self.worker.start()

    # Timer para timeout (segurança)
    self.execution_timer = QTimer()
    self.execution_timer.setSingleShot(True)
    self.execution_timer.timeout.connect(self.on_execution_timeout)
    self.execution_timer.start(300000)  # 5 minutos timeout


def show_success_dialog(self, total_tabelas, message, script_type=""):
    """Mostra diálogo de sucesso para criação de tabelas"""
    dlg = SuccessDialog(self, total_tabelas, message, script_type)
    dlg.exec_()


# ================================================================
# ✅ Diálogo de sucesso (CORRIGIDO)
# ================================================================
class SuccessDialog(QDialog):
    def __init__(self, parent=None, total_tabelas=0, message="", script_type=""):
        super().__init__(parent)
        self.setWindowTitle("🎉 SISTEMA OPERA CRIADO COM SUCESSO!")
        self.setFixedSize(800, 600)
        self.total_tabelas = total_tabelas
        self.message = message
        self.script_type = script_type
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        self.setStyleSheet("""
            QDialog {
                background: #0f1419;
                color: #ffffff;
                border: 3px solid #007bff;
                border-radius: 15px;
            }
            QLabel {
                color: #ffffff;
                background: transparent;
            }
            QPushButton {
                background: #007bff;
                color: #ffffff;
                border-radius: 10px;
                font-weight: bold;
                padding: 12px 25px;
                font-size: 14pt;
                min-width: 120px;
            }
            QPushButton:hover {
                background: #3399ff;
            }
        """)

        # Ícone de sucesso
        lbl_icon = QLabel("🎉")
        lbl_icon.setAlignment(Qt.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 50pt; margin: 10px;")
        layout.addWidget(lbl_icon)

        lbl_title = QLabel("SISTEMA OPERA CRIADO COM SUCESSO!")
        lbl_title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #007bff;")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Banco de dados configurado e pronto para uso")
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet("font-size: 12pt; color: #cccccc; margin-bottom: 10px;")
        layout.addWidget(lbl_sub)

        # Estatísticas - MENSAGEM DINÂMICA POR SCRIPT
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background: #1a1f25;
                border: 1px solid #2a2f35;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        stats_layout = QVBoxLayout(stats_frame)

        # 🔥 MENSAGEM DINÂMICA BASEADA NO TIPO DE SCRIPT
        if self.script_type == "script_1":
            lbl_achievement = QLabel("✅ BANCO BANCO_OPERA CRIADO COM SUCESSO!")
            lbl_achievement.setAlignment(Qt.AlignCenter)
            lbl_achievement.setStyleSheet("font-size: 16pt; font-weight: bold; color: #66b3ff;")
            stats_layout.addWidget(lbl_achievement)

            lbl_next_step = QLabel("➡️ PRÓXIMO PASSO: Execute o script 2_CRIAR_SCHEMA.sql")
            lbl_next_step.setAlignment(Qt.AlignCenter)
            lbl_next_step.setStyleSheet("font-size: 12pt; color: #99ccff; margin-top: 10px;")
            stats_layout.addWidget(lbl_next_step)

        elif self.script_type == "script_2":
            lbl_achievement = QLabel("✅ SCHEMA OPERA CONFIGURADO COM SUCESSO!")
            lbl_achievement.setAlignment(Qt.AlignCenter)
            lbl_achievement.setStyleSheet("font-size: 16pt; font-weight: bold; color: #66b3ff;")
            stats_layout.addWidget(lbl_achievement)

            if self.total_tabelas > 0:
                lbl_tables = QLabel(f"📊 TABELAS EXISTENTES: {self.total_tabelas}")
                lbl_tables.setAlignment(Qt.AlignCenter)
                lbl_tables.setStyleSheet("font-size: 14pt; color: #66b3ff; margin-top: 10px;")
                stats_layout.addWidget(lbl_tables)

            lbl_next_step = QLabel("➡️ PRÓXIMO PASSO: Execute o script 3_CRIAR_TABELAS.sql")
            lbl_next_step.setAlignment(Qt.AlignCenter)
            lbl_next_step.setStyleSheet("font-size: 12pt; color: #99ccff; margin-top: 10px;")
            stats_layout.addWidget(lbl_next_step)

        elif self.script_type == "script_3":
            lbl_achievement = QLabel("✅ TODAS AS TABELAS CRIADAS COM SUCESSO!")
            lbl_achievement.setAlignment(Qt.AlignCenter)
            lbl_achievement.setStyleSheet("font-size: 16pt; font-weight: bold; color: #66b3ff;")
            stats_layout.addWidget(lbl_achievement)

            lbl_tables = QLabel(f"📊 TOTAL DE TABELAS CRIADAS: {self.total_tabelas}")
            lbl_tables.setAlignment(Qt.AlignCenter)
            lbl_tables.setStyleSheet("font-size: 16pt; font-weight: bold; color: #66b3ff; margin-top: 10px;")
            stats_layout.addWidget(lbl_tables)

            lbl_complete = QLabel("🚀 SISTEMA OPERA FASHION PRONTO PARA USO!")
            lbl_complete.setAlignment(Qt.AlignCenter)
            lbl_complete.setStyleSheet("font-size: 14pt; color: #99ccff; margin-top: 10px;")
            stats_layout.addWidget(lbl_complete)

        else:
            # Mensagem genérica para outros scripts
            lbl_tables = QLabel(f"📊 TABELAS NO SCHEMA OPERA: {self.total_tabelas}")
            lbl_tables.setAlignment(Qt.AlignCenter)
            lbl_tables.setStyleSheet("font-size: 16pt; font-weight: bold; color: #66b3ff;")
            stats_layout.addWidget(lbl_tables)

        # Informações de configuração (sempre visíveis)
        lbl_info = QLabel("✅ Schema: opera\n✅ Usuário: GIL DE OLIVEIRA\n✅ Senha: 2580")
        lbl_info.setAlignment(Qt.AlignCenter)
        lbl_info.setStyleSheet("font-size: 11pt; color: #cccccc; margin-top: 15px;")
        stats_layout.addWidget(lbl_info)

        layout.addWidget(stats_frame)

        # Mensagem adicional do log
        if self.message:
            # Limpar a mensagem para remover duplicatas
            clean_message = self.message
            if "Script" in clean_message and "executado com sucesso" in clean_message:
                # Manter apenas a parte importante da mensagem
                if "Banco BANCO_OPERA criado" in clean_message:
                    clean_message = "Banco BANCO_OPERA criado/preparado com sucesso!"
                elif "Schema opera configurado" in clean_message:
                    clean_message = "Schema opera configurado com sucesso!"
                elif "46 tabelas criadas" in clean_message:
                    clean_message = "46 tabelas criadas com sucesso!"

            lbl_msg = QLabel(clean_message)
            lbl_msg.setWordWrap(True)
            lbl_msg.setAlignment(Qt.AlignCenter)
            lbl_msg.setStyleSheet(
                "font-size: 10pt; color: #99ccff; background: #1a2f4a; padding: 10px; border-radius: 5px;")
            layout.addWidget(lbl_msg)

        layout.addStretch()

        # Botões
        btn_layout = QHBoxLayout()

        btn_ok = QPushButton("🎯 Fechar")
        btn_ok.clicked.connect(self.accept)
        btn_ok.setStyleSheet("font-size: 12pt;")

        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)


class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Configurações Avançadas")
        self.setFixedSize(500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        self.setStyleSheet("""
            QDialog {
                background: #0f1419;
                color: #ffffff;
                border: 2px solid #007bff;
                border-radius: 10px;
            }
            QLabel {
                color: #ffffff;
                font-weight: bold;
            }
            QLineEdit, QComboBox {
                background: #1a1f25;
                color: #ffffff;
                border: 1px solid #2a2f35;
                border-radius: 5px;
                padding: 8px;
                font-size: 10pt;
            }
            QPushButton {
                background: #007bff;
                color: #ffffff;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #3399ff;
            }
        """)

        lbl_title = QLabel("Configurações Avançadas do PostgreSQL")
        lbl_title.setStyleSheet("font-size: 14pt; color: #007bff; margin-bottom: 10px;")
        layout.addWidget(lbl_title)

        # Caminho do psql
        lbl_psql = QLabel("Caminho do psql:")
        layout.addWidget(lbl_psql)

        self.psql_input = QLineEdit()
        self.psql_input.setPlaceholderText("Deixe em branco para detecção automática")
        layout.addWidget(self.psql_input)

        # Portas para verificar
        lbl_ports = QLabel("Portas para verificar (separadas por vírgula):")
        layout.addWidget(lbl_ports)

        self.ports_input = QLineEdit("5433,5432,5434")
        layout.addWidget(self.ports_input)

        # Timeout
        lbl_timeout = QLabel("Timeout de execução (segundos):")
        layout.addWidget(lbl_timeout)

        self.timeout_input = QLineEdit("300")
        layout.addWidget(self.timeout_input)

        layout.addStretch()

        # Botões
        btn_layout = QHBoxLayout()

        btn_save = QPushButton("💾 Salvar")
        btn_save.clicked.connect(self.save_config)

        btn_cancel = QPushButton("❌ Cancelar")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def save_config(self):
        # Aqui você implementaria a lógica para salvar as configurações
        QMessageBox.information(self, "✅ Sucesso", "Configurações salvas com sucesso!")
        self.accept()



class InstallerApp(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.setWindowTitle("🚀 INSTALADOR BANCO OPERA 2025")

        # 🔹 Tamanho mínimo e tamanho inicial
        self.setMinimumSize(1280, 800)   # mínimo
        self.resize(1400, 900)           # tamanho ao abrir

        self.init_ui()
        self.setup_auto_refresh()

        # 🔹 Centraliza automaticamente depois que a janela é mostrada
        QTimer.singleShot(0, self.center_on_screen)

    def center_on_screen(self):
        """Centraliza a janela principal no centro da tela."""
        frame_gm = self.frameGeometry()
        screen_center = QApplication.desktop().availableGeometry(self).center()
        frame_gm.moveCenter(screen_center)
        self.move(frame_gm.topLeft())

    def setup_auto_refresh(self):
        """Configura atualização automática do status do banco."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_database_status)
        self.timer.start(1000)  # Atualiza a cada 1 segundos

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # 🔹 Menos espaço "morto" em volta
        main_layout.setContentsMargins(15, 8, 15, 2)  # left, top, right, bottom
        main_layout.setSpacing(1)  # espaço entre cabeçalho e restante

        # ================== CABEÇALHO ÚNICO ==================
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: #0066cc;
                border-radius: 10px;
                padding: 10px;
            }
        """)

        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(5, 4, 5, 4)
        header_layout.setSpacing(3)

        # 🔹 Título principal
        title = QLabel("🚀 INSTALADOR BANCO OPERA 2025")
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: white; margin: 2px;")
        header_layout.addWidget(title)

        # 🔹 Subtítulo
        subtitle = QLabel("Sistema de Gerenciamento de Banco de Dados PostgreSQL")
        subtitle.setFont(QFont("Arial", 11))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #e0f7f4; margin-bottom: 4px;")
        header_layout.addWidget(subtitle)

        main_layout.addWidget(header_frame)

        # ============================
        # 🎨 Estilo geral da interface
        # ============================
        self.setStyleSheet("""
            QMainWindow {
                background: #0f1419;
                color: #ffffff;
            }
            QWidget {
                background: transparent;
                color: #ffffff;
                font-family: 'Arial', sans-serif;
                font-size: 10pt;
            }
            QGroupBox {
                border: 1px solid #2a2f35;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
                color: #007bff;
                background: #1a1f25;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #007bff;
            }
            QPushButton {
                background: #007bff;
                color: #ffffff;
                border-radius: 6px;
                font-weight: bold;
                padding: 8px 12px;
                border: none;
            }
            QPushButton:hover {
                background: #3399ff;
            }
            QPushButton:disabled {
                background: #2a2f35;
                color: #666666;
            }
            QLineEdit, QComboBox {
                background: #1a1f25;
                color: #ffffff;
                border: 1px solid #2a2f35;
                border-radius: 5px;
                padding: 6px;
                font-size: 10pt;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #007bff;
            }
            QListWidget {
                background: #1a1f25;
                color: #66b3ff;
                border: 1px solid #2a2f35;
                border-radius: 5px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #2a2f35;
            }
            QListWidget::item:selected {
                background: #007bff;
                color: #ffffff;
                border-radius: 3px;
            }
            QTextEdit {
                background: #000000;
                color: #66b3ff;
                border: 1px solid #2a2f35;
                border-radius: 5px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9pt;
            }
            QProgressBar {
                border: 1px solid #2a2f35;
                border-radius: 5px;
                background: #1a1f25;
                color: #ffffff;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #0056b3;
                border-radius: 4px;
            }
            QTabWidget::pane {
                border: 1px solid #2a2f35;
                border-radius: 5px;
                background: #1a1f25;
            }
            QTabBar::tab {
                background: #2a2f35;
                color: #cccccc;
                padding: 8px 15px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #007bff;
                color: #ffffff;
                font-weight: bold;
            }
        """)

        # ============================
        # 📊 ÁREA PRINCIPAL
        # ============================
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Painel esquerdo - Controles
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        splitter.addWidget(left_panel)

        # Painel direito - Logs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        splitter.addWidget(right_panel)

        splitter.setSizes([400, 600])

        # ============================
        # ⚙️ CONFIGURAÇÃO DE CONEXÃO
        # ============================
        cfg_group = QGroupBox("⚙️ Configuração de Conexão PostgreSQL")
        cfg_layout = QVBoxLayout(cfg_group)

        def add_field(label_text, widget):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #ffffff; font-weight: bold; margin-top: 8px;")
            cfg_layout.addWidget(lbl)
            cfg_layout.addWidget(widget)

        self.user_input = QLineEdit("postgres")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Senha (deixe em branco para padrão)")
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("5432 (deixe em branco para auto-detecção)")
        self.db_combo = QComboBox()
        self.db_combo.addItems(["postgres", "BANCO_OPERA"])

        add_field("👤 Usuário:", self.user_input)
        add_field("🔑 Senha:", self.password_input)
        add_field("🔌 Porta:", self.port_input)
        add_field("🗄️ Banco:", self.db_combo)

        # Indicador visual do banco atual
        self.db_status_label = QLabel("🔵 Banco atual: postgres")
        self.db_status_label.setStyleSheet("""
            QLabel {
                color: #3399ff; 
                font-weight: bold; 
                padding: 8px;
                background: #1a2f4a;
                border-radius: 5px;
                margin-top: 8px;
            }
        """)
        cfg_layout.addWidget(self.db_status_label)

        left_layout.addWidget(cfg_group)

        # ============================
        # 📜 LISTA DE SCRIPTS
        # ============================
        scripts_group = QGroupBox("📜 Scripts SQL Disponíveis")
        scripts_layout = QVBoxLayout(scripts_group)

        self.scripts_list = QListWidget()
        self.scripts_list.itemDoubleClicked.connect(self.execute_script)
        scripts_layout.addWidget(self.scripts_list)

        left_layout.addWidget(scripts_group)

        # ============================
        # 🎯 BOTÕES DE AÇÃO
        # ============================
        btn_group = QGroupBox("🎯 Ações")
        btn_layout = QVBoxLayout(btn_group)

        # Linha 1 de botões
        btn_row1 = QHBoxLayout()
        self.btn_test = QPushButton("🔍 Testar Conexão")
        self.btn_exec = QPushButton("🚀 Executar Script")
        btn_row1.addWidget(self.btn_test)
        btn_row1.addWidget(self.btn_exec)

        # Linha 2 de botões
        btn_row2 = QHBoxLayout()
        self.btn_check_db = QPushButton("📊 Verificar Banco")
        self.btn_config = QPushButton("⚙️ Configurações")
        self.btn_clear = QPushButton("🧹 Limpar Log")
        btn_row2.addWidget(self.btn_check_db)
        btn_row2.addWidget(self.btn_config)
        btn_row2.addWidget(self.btn_clear)

        btn_layout.addLayout(btn_row1)
        btn_layout.addLayout(btn_row2)
        left_layout.addWidget(btn_group)

        # ============================
        # 📈 INFORMAÇÕES DO SISTEMA
        # ============================
        info_group = QGroupBox("📈 Status do Sistema")
        info_layout = QVBoxLayout(info_group)

        self.system_info = QTextEdit()
        self.system_info.setMaximumHeight(120)
        self.system_info.setReadOnly(True)
        info_layout.addWidget(self.system_info)

        left_layout.addWidget(info_group)

        # ============================
        # 📊 PROGRESSO E LOGS (PAINEL DIREITO)
        # ============================
        # Barra de progresso
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        right_layout.addWidget(self.progress)

        # Abas para logs
        tab_widget = QTabWidget()
        right_layout.addWidget(tab_widget)

        # Aba de Log Principal
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        tab_widget.addTab(self.log_area, "📝 Log de Execução")

        # Aba de Detalhes Técnicos
        self.tech_log = QTextEdit()
        self.tech_log.setReadOnly(True)
        self.tech_log.setStyleSheet("color: #cccccc; background: #000000;")
        tab_widget.addTab(self.tech_log, "🔧 Detalhes Técnicos")

        # ============================
        # 🔗 CONEXÕES
        # ============================
        self.btn_exec.clicked.connect(self.execute_script)
        self.btn_test.clicked.connect(self.test_connection)
        self.btn_check_db.clicked.connect(self.check_database)
        self.btn_config.clicked.connect(self.show_config)
        self.btn_clear.clicked.connect(self.clear_logs)
        self.db_combo.currentTextChanged.connect(self.on_database_changed)
        self.scripts_list.currentItemChanged.connect(self.on_script_selected)

        # ============================
        # 🚀 INICIALIZAÇÃO
        # ============================
        self.load_scripts()
        self.update_system_info()
        self.log_html("✅ Aplicação iniciada com sucesso!")
        self.log_html("💡 Dica: Deixe a porta em branco para auto-detecção")
        self.log_html("🔄 O banco será alterado automaticamente após o script 1")

    # ================================================================
    # 📜 MÉTODOS DE SUPORTE
    # ================================================================
    def load_scripts(self):
        """Carrega a lista de scripts disponíveis"""
        scripts = self.db_manager.get_available_scripts()
        self.scripts_list.clear()
        for s in scripts:
            self.scripts_list.addItem(s["filename"])

    def log_html(self, msg: str):
        """Adiciona log colorido baseado no emoji inicial."""
        if msg.startswith("✅"):
            color = "#66b3ff"
        elif msg.startswith("⚠️"):
            color = "#ffaa00"
        elif msg.startswith("❌"):
            color = "#ff5555"
        elif msg.startswith("🔄"):
            color = "#3399ff"
        elif msg.startswith("🔍"):
            color = "#ffcc00"
        elif msg.startswith("🚀"):
            color = "#ff66cc"
        elif msg.startswith("📊"):
            color = "#66b3ff"
        elif msg.startswith("💡"):
            color = "#99ccff"
        else:
            color = "#cccccc"

        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"<span style='color:{color}'>[{timestamp}] {msg}</span>"
        self.log_area.append(formatted_msg)
        self.log_area.moveCursor(QTextCursor.End)
        self.log_area.ensureCursorVisible()

    def log_tech(self, msg: str):
        """Adiciona log na aba técnica"""
        self.tech_log.append(msg)
        self.tech_log.moveCursor(QTextCursor.End)

    def update_database_status(self):
        """Atualiza o indicador visual do banco atual"""
        current_db = self.db_combo.currentText()
        if current_db == "BANCO_OPERA":
            self.db_status_label.setText("🔵 Banco atual: BANCO_OPERA (Pronto para tabelas)")
            self.db_status_label.setStyleSheet("""
                QLabel {
                    color: #66b3ff; 
                    font-weight: bold; 
                    padding: 8px;
                    background: #1a2f4a;
                    border-radius: 5px;
                    margin-top: 8px;
                }
            """)
        else:
            self.db_status_label.setText("🔵 Banco atual: postgres (Para scripts iniciais)")
            self.db_status_label.setStyleSheet("""
                QLabel {
                    color: #3399ff; 
                    font-weight: bold; 
                    padding: 8px;
                    background: #1a2f4a;
                    border-radius: 5px;
                    margin-top: 8px;
                }
            """)

    def update_system_info(self):
        """Atualiza informações do sistema"""
        info_text = f"""
📍 PostgreSQL: {self.get_postgres_version()}
📁 Diretório: {os.getcwd()}
📜 Scripts: {self.scripts_list.count()} encontrados
🕒 Iniciado: {self.get_current_time()}
        """.strip()

        self.system_info.setPlainText(info_text)

    def get_postgres_version(self):
        """Obtém versão do PostgreSQL"""
        try:
            success, msg = self.db_manager.test_connection()
            if success:
                return "Conectado ✅"
            return "Desconectado ❌"
        except:
            return "Indisponível ❌"

    def get_current_time(self):
        from datetime import datetime
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    def on_database_changed(self):
        """Quando o usuário muda manualmente o banco"""
        self.update_database_status()
        self.log_html(f"🔄 Banco alterado para: {self.db_combo.currentText()}")

    def on_script_selected(self, current, previous):
        """Quando um script é selecionado"""
        if current:
            script_name = current.text()
            target_db = self.db_manager._get_correct_database_for_script(script_name)
            self.log_html(f"📄 Script selecionado: {script_name} (Banco: {target_db})")

    # ================================================================
    # 🎯 MÉTODOS DE AÇÃO
    # ================================================================
    def test_connection(self):
        """Testa a conexão com o banco de dados"""
        password = self.password_input.text().strip()
        user = self.user_input.text().strip()
        port = self.port_input.text().strip() or None
        database = self.db_combo.currentText()

        self.log_html(f"🔍 Testando conexão com {database} ({user}@localhost)...")
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Progresso indeterminado

        self.worker = WorkerThread(self.db_manager, "test_connection", password,
                                   database=database, user=user, port=port)
        self.worker.finished.connect(self.on_test_finished)
        self.worker.log_message.connect(self.log_html)
        self.worker.start()

    def on_test_finished(self, success, message):
        """Callback do teste de conexão"""
        self.progress.setVisible(False)
        self.log_html(message)

        if success:
            QMessageBox.information(self, "✅ Sucesso", message)
        else:
            QMessageBox.critical(self, "❌ Erro de Conexão", message)

    def check_database(self):
        """Verifica se o banco existe"""
        password = self.password_input.text().strip()
        user = self.user_input.text().strip()
        port = self.port_input.text().strip() or None
        database = self.db_combo.currentText()

        self.log_html(f"📊 Verificando existência do banco {database}...")

        self.worker = WorkerThread(self.db_manager, "check_database", password,
                                   database=database, user=user, port=port)
        self.worker.finished.connect(self.on_check_finished)
        self.worker.start()

    def on_check_finished(self, success, message):
        """Callback da verificação de banco"""
        self.log_html(message)

        if success:
            # Se o banco existe, mostra quantas tabelas tem
            table_count = self.db_manager.count_tables()
            if table_count > 0:
                self.log_html(f"📊 O banco possui {table_count} tabelas no schema opera")
            QMessageBox.information(self, "✅ Banco Encontrado",
                                    f"{message}\n\nTabelas no schema opera: {table_count}")
        else:
            QMessageBox.warning(self, "⚠️ Banco Não Encontrado", message)

    def execute_script(self):
        """Executa o script SQL selecionado com banco automático correto"""
        selected = self.scripts_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "⚠️ Aviso", "Nenhum script selecionado!")
            return

        script = selected.text()
        password = self.password_input.text().strip()
        user = self.user_input.text().strip()
        port = self.port_input.text().strip() or None

        # 🔥 CORREÇÃO CRÍTICA: Determinar o banco CORRETO para cada script
        # IGNORA a seleção atual do usuário e força o banco adequado
        if script == "1_CRIAR_BANCO.sql":
            database = "postgres"  # Script 1 SEMPRE no postgres
            self.log_html("💡 Script 1: Executando no banco POSTGRES (criação do BANCO_OPERA)")
        elif script == "2_CRIAR_SCHEMA.sql":
            database = "BANCO_OPERA"  # Script 2 SEMPRE no BANCO_OPERA
            self.log_html("💡 Script 2: Executando no banco BANCO_OPERA (configuração do schema)")
        elif script == "3_CRIAR_TABELAS.sql":
            database = "BANCO_OPERA"  # Script 3 SEMPRE no BANCO_OPERA
            self.log_html("💡 Script 3: Executando no banco BANCO_OPERA (criação de tabelas)")
        else:
            # Para outros scripts, usa BANCO_OPERA por padrão
            database = "BANCO_OPERA"
            self.log_html(f"💡 Script personalizado: Executando no banco BANCO_OPERA")

        # 🔄 ATUALIZAR VISUALMENTE o combobox para refletir o banco correto
        current_displayed_db = self.db_combo.currentText()
        if current_displayed_db != database:
            self.db_combo.setCurrentText(database)
            self.log_html(f"🔄 Banco alterado automaticamente: {current_displayed_db} → {database}")

        self.log_html(f"🚀 INICIANDO EXECUÇÃO: {script}")
        self.log_html(f"📁 Banco definido: {database}")
        self.log_html(f"👤 Usuário: {user}")
        self.log_html(f"🔌 Porta: {port or 'auto-detecção'}")

        # Feedback específico e detalhado por script
        if script == "1_CRIAR_BANCO.sql":
            self.log_html("🎯 OBJETIVO: Criar banco de dados BANCO_OPERA")
            self.log_html("💡 AÇÃO: Executando CREATE DATABASE no PostgreSQL")
        elif script == "2_CRIAR_SCHEMA.sql":
            self.log_html("🎯 OBJETIVO: Configurar schema OPERA no banco BANCO_OPERA")
            self.log_html("💡 AÇÃO: Criar extensões, schema, usuários e permissões")
        elif script == "3_CRIAR_TABELAS.sql":
            self.log_html("🎯 OBJETIVO: Criar 46 tabelas do sistema Opera Fashion")
            self.log_html("💡 AÇÃO: Executar CREATE TABLE para todas as tabelas do sistema")
        else:
            self.log_html(f"🎯 OBJETIVO: Executar script personalizado {script}")

        # Mostrar barra de progresso indeterminada
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Progresso indeterminado
        self.progress.setFormat(f"Executando {script}... %p%")

        # 🔧 VERIFICAÇÃO PRÉ-EXECUÇÃO para scripts 2 e 3
        if script in ["2_CRIAR_SCHEMA.sql", "3_CRIAR_TABELAS.sql"]:
            self.log_html("🔍 Verificando pré-requisitos...")
            # Verificar se o banco BANCO_OPERA existe
            db_exists = self.db_manager.check_database_exists("BANCO_OPERA", password, user, port)
            if not db_exists:
                error_msg = f"❌ ERRO CRÍTICO: Banco BANCO_OPERA não existe!\n\nExecute o script 1_CRIAR_BANCO.sql primeiro."
                self.log_html(error_msg)
                self.progress.setVisible(False)
                QMessageBox.critical(self, "❌ Banco Não Encontrado", error_msg)
                return

        # 🧵 CRIAR E CONFIGURAR THREAD DE EXECUÇÃO
        self.worker = WorkerThread(
            db_manager=self.db_manager,
            task_type="install_script",
            password=password,
            script_name=script,
            database=database,  # 🔥 Banco CORRETO forçado
            user=user,
            port=port
        )

        # 🔗 CONECTAR SINAIS DA THREAD (ATUALIZADO)
        self.worker.finished.connect(self.on_exec_finished)
        self.worker.success_dialog.connect(self.show_success_dialog)
        self.worker.switch_database.connect(self.switch_to_banco_opera)
        self.worker.log_message.connect(self.log_html)
        self.worker.progress_update.connect(self.on_progress_update)

        # 🚀 INICIAR EXECUÇÃO
        self.log_html("⏳ Iniciando processo de execução...")

        # Desabilitar botões durante execução
        self.set_buttons_enabled(False)

        self.worker.start()

        # Timer para timeout (segurança)
        self.execution_timer = QTimer()
        self.execution_timer.setSingleShot(True)
        self.execution_timer.timeout.connect(self.on_execution_timeout)
        self.execution_timer.start(300000)  # 5 minutos timeout

    def switch_to_banco_opera(self):
        """Muda automaticamente para o banco BANCO_OPERA e atualiza UI"""
        current_db = self.db_combo.currentText()
        if current_db != "BANCO_OPERA":
            self.db_combo.setCurrentText("BANCO_OPERA")
            self.log_html("🔄 Banco alterado automaticamente para BANCO_OPERA")
            self.log_html("💡 Agora você pode executar os scripts 2 e 3")

        # Forçar atualização do status
        self.update_database_status()

    def set_buttons_enabled(self, enabled: bool):
        """Habilita ou desabilita botões durante execução"""
        self.btn_exec.setEnabled(enabled)
        self.btn_test.setEnabled(enabled)
        self.btn_check_db.setEnabled(enabled)
        self.btn_config.setEnabled(enabled)
        self.scripts_list.setEnabled(enabled)
        self.db_combo.setEnabled(enabled)

    def on_progress_update(self, message: str):
        """Atualiza mensagem de progresso"""
        self.progress.setFormat(f"{message}... %p%")

    def on_execution_timeout(self):
        """Timeout de segurança para execução muito longa"""
        if self.worker.isRunning():
            self.log_html("⏰ AVISO: Execução está demorando mais que o esperado...")
            self.log_html("💡 Dica: Processos grandes podem levar alguns minutos")

    def on_exec_finished(self, success: bool, message: str):
        """Callback chamado quando a execução do script termina"""
        # Parar timer de timeout
        if hasattr(self, 'execution_timer'):
            self.execution_timer.stop()

        # Ocultar barra de progresso
        self.progress.setVisible(False)

        # Reabilitar botões
        self.set_buttons_enabled(True)

        # Log do resultado
        if success:
            self.log_html("✅ EXECUÇÃO CONCLUÍDA COM SUCESSO!")
            self.log_html(f"📋 Resultado: {message}")

            # Ações pós-execução específicas por script
            script_name = ""
            if hasattr(self.worker, 'script_name'):
                script_name = self.worker.script_name

            if script_name == "1_CRIAR_BANCO.sql":
                self.log_html("🎉 Banco BANCO_OPERA criado com sucesso!")
                self.log_html("➡️ Próximo passo: Execute o script 2_CRIAR_SCHEMA.sql")
                # Mudar automaticamente para BANCO_OPERA após script 1
                self.switch_to_banco_opera()

            elif script_name == "2_CRIAR_SCHEMA.sql":
                self.log_html("🎉 Schema OPERA configurado com sucesso!")
                self.log_html("➡️ Próximo passo: Execute o script 3_CRIAR_TABELAS.sql")

            elif script_name == "3_CRIAR_TABELAS.sql":
                self.log_html("🎉 Todas as tabelas criadas com sucesso!")
                self.log_html("🚀 Sistema Opera Fashion pronto para uso!")

            # Mostrar mensagem de sucesso
            QMessageBox.information(self, "✅ Sucesso", f"Script executado com sucesso!\n\n{message}")

        else:
            self.log_html("❌ EXECUÇÃO FALHOU!")
            self.log_html(f"📋 Erro: {message}")

            # Análise de erro mais detalhada
            if "does not exist" in message and "BANCO_OPERA" in message:
                self.log_html("💡 SOLUÇÃO: Execute o script 1_CRIAR_BANCO.sql primeiro")
            elif "password authentication failed" in message:
                self.log_html("💡 SOLUÇÃO: Verifique a senha do PostgreSQL")
            elif "cannot connect" in message:
                self.log_html("💡 SOLUÇÃO: Verifique se o PostgreSQL está rodando")

            # Mostrar mensagem de erro
            QMessageBox.critical(self, "❌ Erro na Execução", message)

        # Atualizar informações do sistema
        self.update_system_info()
        self.log_html("=" * 50)  # Separador visual

    def show_success_dialog(self, total_tabelas, message):
        """Mostra diálogo de sucesso para criação de tabelas"""
        dlg = SuccessDialog(self, total_tabelas, message)
        dlg.exec_()

    def show_config(self):
        """Mostra diálogo de configurações"""
        dlg = ConfigDialog(self)
        dlg.exec_()

    def clear_logs(self):
        """Limpa todas as áreas de log"""
        self.log_area.clear()
        self.tech_log.clear()
        self.log_html("🧹 Logs limpos com sucesso!")



if __name__ == "__main__":
    # Adiciona o diretório atual ao path
    import sys
    import os

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        from database_manager import DatabaseManager

        # Configuração da aplicação
        app = QApplication(sys.argv)
        app.setApplicationName("Instalador Opera Fashion")
        app.setApplicationVersion("2.0")
        app.setStyle('Fusion')

        # Cria e exibe a janela principal
        scripts_path = os.path.join(os.getcwd(), "scripts")
        db_manager = DatabaseManager(scripts_path)
        window = InstallerApp(db_manager)
        window.show()

        print("✅ Interface iniciada com sucesso!")

        # Executa a aplicação
        sys.exit(app.exec_())

    except ImportError as e:
        print(f"❌ Erro ao importar módulos: {e}")
        input("Pressione Enter para sair...")
    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        input("Pressione Enter para sair...")