#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import socket
import shutil
import json
import platform
from typing import Tuple, List, Dict


class DatabaseManager:
    def __init__(self, scripts_path: str):
        """
        Inicializa o gerenciador de banco de dados

        Args:
            scripts_path (str): Caminho para a pasta contendo os scripts SQL
        """
        self.scripts_path = scripts_path

        # 🔧 Configurações padrão
        self.default_config = {
            "defaults": {
                "user": "postgres",
                "password": "gil25802580",
                "dbname": "postgres"
            },
            "ports": [5433, 5432, 5434],
            "timeout": 300,
            "encoding": "UTF8"
        }

        # 📊 Cache para melhor performance
        self._psql_path_cache = None
        self._port_cache = None
        self._config_cache = None

        # 🎯 Validação inicial
        self._validate_initial_setup()

    def _validate_initial_setup(self):
        """Valida configuração inicial do gerenciador"""
        try:
            # Verificar se o caminho dos scripts existe
            if not os.path.exists(self.scripts_path):
                print(f"⚠️ Aviso: Pasta de scripts não encontrada: {self.scripts_path}")
                # Tentar criar a pasta
                try:
                    os.makedirs(self.scripts_path, exist_ok=True)
                    print(f"✅ Pasta de scripts criada: {self.scripts_path}")
                except Exception as e:
                    print(f"❌ Não foi possível criar pasta de scripts: {e}")

            # Verificar scripts disponíveis
            scripts = self.get_available_scripts()
            print(f"📁 Scripts encontrados: {len(scripts)}")

            # Verificar acesso ao PostgreSQL
            psql_path = self._find_psql_path()
            if psql_path:
                print(f"✅ PostgreSQL detectado: {psql_path}")
            else:
                print("❌ PostgreSQL não encontrado. Verifique a instalação.")

            # Verificar portas disponíveis
            available_ports = []
            config = self.get_connection_config()
            for port in config.get("ports", [5433, 5432, 5434]):
                if self._is_port_open(str(port)):
                    available_ports.append(port)

            if available_ports:
                print(f"✅ Portas PostgreSQL disponíveis: {available_ports}")
            else:
                print("❌ Nenhuma porta PostgreSQL encontrada")

            # Carregar configurações personalizadas se existirem
            config_path = os.path.join(os.path.dirname(self.scripts_path), "config.json")
            if os.path.exists(config_path):
                print(f"✅ Configurações personalizadas carregadas: {config_path}")

        except Exception as e:
            print(f"❌ Erro na validação inicial: {e}")

    def get_connection_config(self) -> dict:
        """
        Obtém configurações de conexão do arquivo config.json ou usa padrões

        Returns:
            dict: Configurações de conexão
        """
        # 🔥 Usar cache para melhor performance
        if self._config_cache is not None:
            return self._config_cache

        try:
            config_path = os.path.join(os.path.dirname(self.scripts_path), "config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)

                # 🔧 Mesclar configurações padrão com personalizadas
                merged_config = self._merge_configs(self.default_config, user_config)
                self._config_cache = merged_config
                return merged_config

        except Exception as e:
            print(f"⚠️ Erro ao ler config.json, usando padrões: {e}")

        self._config_cache = self.default_config
        return self.default_config

    def _merge_configs(self, default: dict, user: dict) -> dict:
        """
        Mescla configurações padrão com personalizadas de forma recursiva

        Args:
            default (dict): Configurações padrão
            user (dict): Configurações do usuário

        Returns:
            dict: Configurações mescladas
        """
        result = default.copy()

        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Mesclar recursivamente dicionários aninhados
                result[key] = self._merge_configs(result[key], value)
            else:
                # Substituir ou adicionar valor
                result[key] = value

        return result

    def _find_psql_path(self) -> str:
        """Detecta o executável psql no macOS, Windows ou Linux."""

        # 🔥 Usar cache para melhor performance
        if self._psql_path_cache:
            return self._psql_path_cache

        # 1️⃣ Verifica se o caminho está definido no config.json
        config_path = os.path.join(os.path.dirname(self.scripts_path), "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "psql_path" in data and os.path.exists(data["psql_path"]):
                        print(f"📍 psql definido manualmente no config.json: {data['psql_path']}")
                        self._psql_path_cache = data["psql_path"]
                        return self._psql_path_cache
            except Exception as e:
                print(f"⚠️ Erro ao ler config.json: {e}")

        # 2️⃣ Detecta automaticamente conforme o sistema
        system = platform.system().lower()

        # Busca no PATH
        psql_path = shutil.which("psql")
        if psql_path and os.path.exists(psql_path):
            print(f"📍 psql detectado automaticamente via PATH: {psql_path}")
            self._psql_path_cache = psql_path
            return self._psql_path_cache

        # Caminhos típicos de cada sistema
        mac_paths = [
            "/Library/PostgreSQL/18/bin/psql",
            "/Library/PostgreSQL/17/bin/psql",
            "/Library/PostgreSQL/16/bin/psql",
            "/Library/PostgreSQL/15/bin/psql",
            "/usr/local/bin/psql",
            "/opt/homebrew/bin/psql",  # Apple Silicon
            "/usr/bin/psql",
        ]
        win_paths = [
            r"C:\Program Files\PostgreSQL\18\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\17\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\16\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\15\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\14\bin\psql.exe",
        ]
        linux_paths = [
            "/usr/bin/psql",
            "/usr/local/bin/psql",
            "/opt/local/bin/psql",
        ]

        search_paths = mac_paths if "darwin" in system else (win_paths if "windows" in system else linux_paths)
        for path in search_paths:
            if os.path.exists(path):
                print(f"📍 psql encontrado em: {path}")
                self._psql_path_cache = path
                return self._psql_path_cache

        print("❌ psql não encontrado automaticamente.")
        return ""

    def _is_port_open(self, port: str, host: str = "localhost") -> bool:
        """Verifica se uma porta está aberta em um host (TCP)."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((host, int(port)))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _auto_detect_port(self, host: str = "localhost") -> str:
        """Detecta automaticamente a porta do PostgreSQL em um host."""

        # 🔥 Cache somente para localhost (evita cache errado em host remoto)
        if host in ("localhost", "127.0.0.1") and self._port_cache is not None:
            return self._port_cache

        config = self.get_connection_config()
        ports = config.get("ports", [5433, 5432, 5434])

        for port in ports:
            if self._is_port_open(str(port), host=host):
                print(f"📍 Porta {port} detectada como ativa em {host}")
                if host in ("localhost", "127.0.0.1"):
                    self._port_cache = str(port)
                    return self._port_cache
                return str(port)

        return ""

    def clear_cache(self):
        """Limpa o cache interno para forçar nova detecção"""
        self._psql_path_cache = None
        self._port_cache = None
        self._config_cache = None
        print("🧹 Cache limpo - nova detecção será realizada")

    def get_system_info(self) -> dict:
        """Retorna informações do sistema para diagnóstico"""

        psql_path = self._find_psql_path()
        port = self._auto_detect_port()
        scripts_count = len(self.get_available_scripts())

        return {
            "sistema_operacional": platform.system(),
            "plataforma": platform.platform(),
            "python_version": platform.python_version(),
            "psql_encontrado": bool(psql_path),
            "psql_caminho": psql_path,
            "porta_detectada": port,
            "scripts_disponiveis": scripts_count,
            "caminho_scripts": self.scripts_path,
            "postgres_rodando": bool(port)
        }

    def get_available_scripts(self) -> List[Dict[str, str]]:
        scripts = []
        if not os.path.exists(self.scripts_path):
            print(f"❌ Pasta scripts não encontrada: {self.scripts_path}")
            return scripts

        import time
        print(f"📁 Lendo scripts diretamente do disco: {self.scripts_path}")

        for file in os.listdir(self.scripts_path):
            file_path = os.path.join(self.scripts_path, file)
            if file.endswith(".sql") and os.path.isfile(file_path):
                stat = os.stat(file_path)
                print(f"   📄 {file} - {stat.st_size} bytes - Modificado: {time.ctime(stat.st_mtime)}")

                category = "danger" if "APAGAR" in file.upper() or "DELETE" in file.upper() else "normal"
                scripts.append({
                    "filename": file,
                    "display_name": file.replace("_", " "),
                    "category": category
                })

        print(f"✅ Encontrados {len(scripts)} scripts no disco")
        return sorted(scripts, key=lambda x: x["filename"])

    def execute_sql_file(self, script_name: str, password: str = None,
                         database: str = None, user: str = "postgres",
                         port: str = None, host: str = "localhost") -> Tuple[bool, str]:
        try:
            sql_path = os.path.join(self.scripts_path, script_name)
            if not os.path.exists(sql_path):
                return False, f"Arquivo {script_name} não encontrado"

            # 🔄 DETERMINAÇÃO AUTOMÁTICA DO BANCO
            target_database = database or self._get_correct_database_for_script(script_name)
            print(f"🎯 Banco determinado: {target_database}")

            if not port:
                port = self._auto_detect_port()
                if not port:
                    return False, "Nenhuma porta PostgreSQL ativa encontrada"

            if not password:
                config = self.get_connection_config()
                password = config.get("defaults", {}).get("password", "gil25802580")

            print(f"🚀 Executando: {script_name} no banco {target_database} (porta {port})")

            psql_path = self._find_psql_path()
            if not psql_path:
                return False, "psql não encontrado (verifique instalação do PostgreSQL)"

            if not self._is_port_open(port, host=host):
                return False, f"Porta {port} não está ativa"

            env = os.environ.copy()
            env["PGPASSWORD"] = password
            env["PGCLIENTENCODING"] = "UTF8"

            # Para scripts que criam banco, não usar transaction
            if script_name == "1_CRIAR_BANCO.sql":
                cmd = [
                    psql_path,
                    "-h", host,
                    "-U", user,
                    "-p", str(port),
                    "-d", "postgres",  # Sempre usar postgres para criar banco
                    "-f", sql_path,
                    "--echo-all"
                ]
            else:
                cmd = [
                    psql_path,
                    "-h", host,
                    "-U", user,
                    "-p", str(port),
                    "-d", target_database,
                    "-f", sql_path,
                    "-v", "ON_ERROR_STOP=1",
                    "--echo-all"
                ]

            print(f"🔧 Comando: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, capture_output=True, text=True, env=env,
                timeout=300, encoding="utf-8", errors="replace"
            )

            print(f"📊 Resultado exitcode: {result.returncode}")

            # Log reduzido para não poluir
            if result.stdout:
                print(f"📤 STDOUT (primeiras linhas):")
                for i, line in enumerate(result.stdout.split('\n')[:10]):
                    if line.strip():
                        print(f"   {i + 1}: {line}")

            if result.stderr:
                print(f"📤 STDERR (primeiras linhas):")
                for i, line in enumerate(result.stderr.split('\n')[:10]):
                    if line.strip():
                        print(f"   {i + 1}: {line}")

            if result.returncode == 0:
                # 🔥 CORREÇÃO CRÍTICA: MENSAGENS SIMPLES E NÃO DUPLICADAS
                success_msg = self._get_success_message(script_name, result.stdout, target_database)

                # 🔥 REMOVER mensagens específicas que causam duplicação no diálogo
                # O diálogo agora terá sua própria lógica de mensagem

                return True, success_msg
            else:
                error_msg = result.stderr.strip() or "Erro desconhecido durante a execução"

                # Tratamento de erros específicos
                if "already exists" in error_msg.lower():
                    if "database" in error_msg.lower():
                        return True, "Banco BANCO_OPERA já existe"
                    else:
                        return True, "Objeto já existe"
                elif "does not exist" in error_msg and target_database == "banco_opera":
                    error_msg += "\n💡 DICA: O banco 'BANCO_OPERA' pode não existir. Execute o script 1_CRIAR_BANCO.sql primeiro"
                elif "cannot run inside a transaction block" in error_msg:
                    error_msg += "\n💡 DICA: Script ajustado para executar fora de transação"

                return False, f"Erro em {script_name} (banco: {target_database}): {error_msg}"

        except subprocess.TimeoutExpired:
            return False, f"Timeout em {script_name}: comando demorou muito"
        except Exception as e:
            return False, f"Erro inesperado em {script_name}: {str(e)}"

    def _get_success_message(self, script_name: str, stdout: str, database: str) -> str:
        """Gera mensagens de sucesso limpas e específicas para cada script"""

        script_lower = script_name.lower()

        # 🔥 MENSAGENS SIMPLES E DIRETAS - SEM CONTAGEM DUPLICADA
        if script_lower == "1_criar_banco.sql":
            return "Banco BANCO_OPERA criado/preparado com sucesso"

        elif script_lower == "2_criar_schema.sql":
            return "Schema opera configurado com sucesso"

        elif script_lower == "3_criar_tabelas.sql":
            # 🔥 REMOVER contagem do output - usar apenas contagem real do banco
            return "Estrutura de tabelas criada com sucesso"

        elif "apagar" in script_lower or "delete" in script_lower:
            return "Operação de limpeza concluída com sucesso"

        else:
            return f"Script {script_name} executado com sucesso"

    def _count_tables_from_output(self, stdout: str) -> int:
        """Conta tabelas MENCIONADAS no output - APENAS PARA FEEDBACK, NÃO CONTA REAL"""
        try:
            # Padrão para detectar criação REAL de tabelas (evitar duplicatas)
            import re
            table_creations = set()

            # Procura por "CREATE TABLE opera.nome_da_tabela"
            pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?opera\.([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(pattern, stdout, re.IGNORECASE)

            for match in matches:
                table_creations.add(match.lower())

            # Também procura por mensagens de sucesso específicas
            success_patterns = [
                "CREATE TABLE",
                "TABLE CREATED",
                "TABELA CRIADA"
            ]

            additional_count = 0
            for line in stdout.split('\n'):
                line_upper = line.upper()
                # Só conta se for uma linha de criação real, não mensagens genéricas
                if any(pattern in line_upper for pattern in success_patterns):
                    if "OPERATION COMPLETED" not in line_upper and "SUCCESS" not in line_upper:
                        additional_count += 1

            # Retorna o maior valor entre os dois métodos, mas com limite razoável
            total_mentioned = max(len(table_creations), additional_count)

            # 🔥 LIMITE MÁXIMO: não retorna mais que 46 (número esperado)
            return min(total_mentioned, 46)

        except Exception as e:
            print(f"⚠️ Erro na contagem do output: {e}")
            return 0

    def _get_correct_database_for_script(self, script_name: str) -> str:
        """Determina automaticamente o banco correto para cada script"""
        script_lower = script_name.lower()

        # Script 1 deve rodar no banco postgres
        if script_lower == "1_criar_banco.sql":
            return "postgres"
        # Scripts 2 e 3 devem rodar no banco BANCO_OPERA
        elif script_lower in ["2_criar_schema.sql", "3_criar_tabelas.sql"]:
            return "BANCO_OPERA"
        else:
            # Para outros scripts, usa BANCO_OPERA por padrão
            return "BANCO_OPERA"

    def confirm_table_creation(self, password: str = None, user: str = "postgres",
                               port: str = None, database: str = "BANCO_OPERA", host: str = "localhost") -> Dict:
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
                psql_path, "-h", host, "-U", user,
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

    # ==========================================================
    # 🔗 TESTE DE CONEXÃO
    # ==========================================================
    def test_connection(self, password: str = None, database: str = "postgres",
                        user: str = "postgres", port: str = None, host: str = "localhost") -> Tuple[bool, str]:
        try:
            if not port:
                port = self._auto_detect_port()
                if not port:
                    return False, "Nenhuma porta PostgreSQL ativa encontrada"

            if not password:
                config = self.get_connection_config()
                password = config.get("defaults", {}).get("password", "gil25802580")

            print(f"🔍 Testando conexão com {database} ({user}@{host}:{port})")

            psql_path = self._find_psql_path()
            if not psql_path:
                return False, "psql não encontrado"

            if not self._is_port_open(port, host=host):
                return False, f"Porta {port} não está ativa"

            env = os.environ.copy()
            env["PGPASSWORD"] = password

            sql_test = "SELECT current_database(), version();"

            cmd = [
                psql_path,
                "-h", host,
                "-U", user,
                "-p", str(port),
                "-d", database,
                "-c", sql_test,
                "--quiet"
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, env=env,
                timeout=10, encoding="utf-8", errors="replace"
            )

            if result.returncode == 0:
                return True, f"✅ Conexão estabelecida com sucesso na porta {port} (Banco: {database})"
            else:
                err = result.stderr.strip()
                if "password authentication failed" in err:
                    return False, f"❌ Falha na autenticação para usuário {user}"
                elif "does not exist" in err and database == "banco_opera":
                    return False, f"❌ Banco {database} não existe. Execute o script 1_CRIAR_BANCO.sql primeiro"
                else:
                    return False, f"❌ Erro de conexão com {database}: {err}"

        except Exception as e:
            return False, f"❌ Erro inesperado: {str(e)}"

    # ==========================================================
    # 🧮 OUTRAS FUNÇÕES (LISTAR / CONTAR)
    # ==========================================================
    def get_databases(self, password: str = None, user: str = "postgres",
                      port: str = None, host: str = "localhost") -> List[str]:
        try:
            if not port:
                port = self._auto_detect_port()
                if not port:
                    return []

            if not password:
                cfg = self.get_connection_config()
                password = cfg.get("defaults", {}).get("password", "gil25802580")

            psql_path = self._find_psql_path()
            if not psql_path:
                return []

            env = os.environ.copy()
            env["PGPASSWORD"] = password

            cmd = [
                psql_path,
                "-h", host,
                "-U", user,
                "-p", str(port),
                "-d", "postgres",
                "-c", "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;",
                "-t", "--quiet"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)
            if result.returncode == 0:
                return [x.strip() for x in result.stdout.split("\n") if x.strip()]
            return []
        except Exception:
            return []

    def debug_script_content(self, script_name: str):
        sql_path = os.path.join(self.scripts_path, script_name)
        if not os.path.exists(sql_path):
            print(f"❌ ARQUIVO NÃO EXISTE: {sql_path}")
            return
        print(f"🔍 DEBUG CONTEÚDO DE {script_name}:")
        print("=" * 80)
        try:
            with open(sql_path, "r", encoding="utf-8") as f:
                content = f.read()
                print(f"Tamanho: {len(content)} chars")
                print(content[:500] + "...\n")
        except Exception as e:
            print(f"❌ Erro ao ler arquivo: {e}")
        print("=" * 80)

    def count_tables(self, password: str = None, user: str = "postgres",
                     port: str = None, database: str = "BANCO_OPERA", host: str = "localhost") -> int:
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

            query = """SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='opera' AND table_type='BASE TABLE';"""

            cmd = [
                psql_path, "-h", host, "-U", user,
                "-p", str(port), "-d", database, "-c", query,
                "-t", "--quiet", "-A"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)

            if result.returncode == 0 and result.stdout.strip().isdigit():
                return int(result.stdout.strip())
            return 0

        except Exception as e:
            print(f"❌ Erro ao contar tabelas: {e}")
            return 0

    def list_tables(self, password: str = None, user: str = "postgres",
                    port: str = None, database: str = "BANCO_OPERA", host: str = "localhost") -> List[str]:
        try:
            if not port:
                port = self._auto_detect_port()
                if not port:
                    return []

            psql_path = self._find_psql_path()
            if not psql_path:
                return []

            if not password:
                config = self.get_connection_config()
                password = config.get("defaults", {}).get("password", "gil25802580")

            env = os.environ.copy()
            env["PGPASSWORD"] = password

            query = """SELECT table_name FROM information_schema.tables WHERE table_schema='opera' AND table_type='BASE TABLE' ORDER BY table_name;"""

            cmd = [
                psql_path, "-h", host, "-U", user,
                "-p", str(port), "-d", database, "-c", query,
                "-t", "--quiet", "-A"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)

            if result.returncode == 0:
                return [x.strip() for x in result.stdout.split("\n") if x.strip()]
            return []

        except Exception as e:
            print(f"❌ Erro ao listar tabelas: {e}")
            return []

    def get_database_info(self, password: str = None, user: str = "postgres",
                          port: str = None, database: str = "BANCO_OPERA", host: str = "localhost") -> Dict:
        """Retorna informações detalhadas sobre o banco"""
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

            # Query para informações do banco
            queries = {
                "tables_count": "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='opera';",
                "size": "SELECT pg_size_pretty(pg_database_size('BANCO_OPERA'));",
                "version": "SELECT version();",
                "created": "SELECT datname, datcreated FROM pg_database WHERE datname='banco_opera';"
            }

            info = {}
            for key, query in queries.items():
                cmd = [psql_path, "-h", host, "-U", user, "-p", str(port),
                       "-d", database, "-c", query, "-t", "--quiet", "-A"]

                result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)
                if result.returncode == 0:
                    info[key] = result.stdout.strip()

            return info

        except Exception as e:
            return {"error": f"Erro ao obter informações: {str(e)}"}

    def check_database_exists(self, database: str = "BANCO_OPERA",
                              password: str = None, user: str = "postgres",
                              port: str = None, host: str = "localhost") -> bool:
        """Verifica se um banco de dados existe (respeitando maiúsculas do BANCO_OPERA)"""
        try:
            if not port:
                port = self._auto_detect_port()
                if not port:
                    return False

            psql_path = self._find_psql_path()
            if not psql_path:
                return False

            if not password:
                config = self.get_connection_config()
                password = config.get("defaults", {}).get("password", "gil25802580")

            env = os.environ.copy()
            env["PGPASSWORD"] = password

            # 🔥 NÃO usar .lower() aqui, porque o script 1 cria "BANCO_OPERA" (maiúsculo e com aspas)
            # Para ficar tolerante, checamos as duas formas:
            query = (
                f"SELECT 1 "
                f"FROM pg_database "
                f"WHERE datname = '{database}' "
                f"   OR datname = '{database.lower()}';"
            )

            cmd = [
                psql_path, "-h", host, "-U", user,
                "-p", str(port), "-d", "postgres", "-c", query,
                "-t", "--quiet", "-A"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)

            # Se existir, o SELECT devolve "1"
            return result.returncode == 0 and result.stdout.strip() == "1"

        except Exception:
            return False

    def backup_database(self, backup_path: str, password: str = None,
                        user: str = "postgres", port: str = None, host: str = "localhost") -> Tuple[bool, str]:
        """Faz backup do banco BANCO_OPERA"""
        try:
            if not port:
                port = self._auto_detect_port()
                if not port:
                    return False, "Nenhuma porta PostgreSQL ativa encontrada"

            if not password:
                config = self.get_connection_config()
                password = config.get("defaults", {}).get("password", "gil25802580")

            psql_path = self._find_psql_path()
            if not psql_path:
                return False, "psql não encontrado"

            env = os.environ.copy()
            env["PGPASSWORD"] = password

            cmd = [
                psql_path.replace("psql", "pg_dump"),  # Usa pg_dump para backup
                "-h", host,
                "-U", user,
                "-p", str(port),
                "-d", "BANCO_OPERA",
                "-f", backup_path,
                "--verbose"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)

            if result.returncode == 0:
                return True, f"✅ Backup criado com sucesso: {backup_path}"
            else:
                return False, f"❌ Erro no backup: {result.stderr}"

        except Exception as e:
            return False, f"❌ Erro inesperado no backup: {str(e)}"

    def execute_sql_file_with_log(self, filename, password, database="postgres", user="postgres", port=None):
        """
        Executa arquivo SQL e retorna log completo
        """
        try:
            # Encontrar o caminho completo do script
            script_path = os.path.join(self.scripts_path, filename)

            if not os.path.exists(script_path):
                return False, f"Arquivo não encontrado: {filename}", ""

            # Construir comando psql
            cmd = self.build_psql_command(password, database, user, port)
            cmd.extend(["-f", script_path])

            # Executar e capturar stdout e stderr
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            # Combinar stdout e stderr para log completo
            full_log = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"

            success = (result.returncode == 0)
            message = "Script executado com sucesso" if success else f"Erro na execução: {result.stderr}"

            return success, message, full_log

        except subprocess.TimeoutExpired:
            return False, "Timeout: script executou por mais de 5 minutos", ""
        except Exception as e:
            return False, f"Erro inesperado: {str(e)}", ""

    def build_psql_command(self, password: str, database: str, user: str, port: str, host: str = "localhost") -> List[str]:
        """Constrói comando psql base"""
        if not port:
            port = self._auto_detect_port()
            if not port:
                raise Exception("Nenhuma porta PostgreSQL ativa encontrada")

        psql_path = self._find_psql_path()
        if not psql_path:
            raise Exception("psql não encontrado")

        if not password:
            config = self.get_connection_config()
            password = config.get("defaults", {}).get("password", "gil25802580")

        env = os.environ.copy()
        env["PGPASSWORD"] = password

        return [
            psql_path,
            "-h", host,
            "-U", user,
            "-p", str(port),
            "-d", database
        ]

    def analyze_script_execution_log(self, log_output, script_name):
        """
        Analisa o log de execução para contar tabelas criadas com sucesso
        """
        if script_name != "3_CRIAR_TABELAS.sql":
            return None

        try:
            # Padrões para detectar criação de tabelas
            success_patterns = [
                "CREATE TABLE",
                "CREATE TABLE IF NOT EXISTS"
            ]

            error_patterns = [
                "ERROR:",
                "FATAL:",
                "relation .* already exists",
                "duplicate key",
                "already exists"
            ]

            lines = log_output.split('\n')
            tables_created = 0
            tables_failed = 0
            table_names = []

            i = 0
            while i < len(lines):
                line = lines[i]
                line_upper = line.upper()

                # Verificar se é uma linha de criação de tabela
                is_table_creation = any(pattern in line_upper for pattern in success_patterns)

                if is_table_creation:
                    table_name = self.extract_table_name(line)
                    if table_name:
                        # Verificar se há erro nas próximas linhas
                        has_error = False
                        check_lines = min(5, len(lines) - i)

                        for j in range(i, i + check_lines):
                            if any(error_pattern in lines[j].upper() for error_pattern in error_patterns):
                                has_error = True
                                break

                        if has_error:
                            tables_failed += 1
                        else:
                            tables_created += 1
                            table_names.append(table_name)

                i += 1

            total_attempted = tables_created + tables_failed
            success_rate = (tables_created / total_attempted * 100) if total_attempted > 0 else 0

            return {
                'total_created': tables_created,
                'total_failed': tables_failed,
                'total_attempted': total_attempted,
                'table_names': table_names,
                'success_rate': success_rate
            }

        except Exception as e:
            print(f"Erro na análise do log: {e}")
            return None

    def extract_table_name(self, create_statement):
        """
        Extrai o nome da tabela de uma instrução CREATE TABLE
        """
        try:
            import re

            # Padrão para opera.nome_da_tabela
            pattern_opera = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?opera\.([a-zA-Z_][a-zA-Z0-9_]*)'
            match_opera = re.search(pattern_opera, create_statement, re.IGNORECASE)
            if match_opera:
                return match_opera.group(1)

            # Padrão para nome_da_tabela simples
            pattern_simple = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)'
            match_simple = re.search(pattern_simple, create_statement, re.IGNORECASE)
            if match_simple:
                return match_simple.group(1)

            return None
        except Exception as e:
            print(f"Erro ao extrair nome da tabela: {e}")
            return None

    def count_tables_after_script(self, password, user, port, database):
        """
        Conta tabelas no schema opera após execução do script
        """
        try:
            cmd = self.build_psql_command(password, database, user, port)
            cmd.extend(["-c", "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'opera';"])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                # Extrair número do resultado
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip().isdigit():
                        return int(line.strip())
            return 0
        except:
            return 0


# ==========================================================
# 🧪 TESTE DO MÓDULO
# ==========================================================
if __name__ == "__main__":
    print("🧪 Teste do DatabaseManager")
    scripts_path = os.path.join(os.getcwd(), "scripts")

    if not os.path.exists(scripts_path):
        print(f"❌ Pasta scripts não encontrada: {scripts_path}")
        exit(1)

    dbm = DatabaseManager(scripts_path)

    # Teste de detecção
    port = dbm._auto_detect_port()
    print(f"📍 Porta detectada: {port}")

    psql_path = dbm._find_psql_path()
    print(f"📍 Caminho do psql: {psql_path}")

    # Teste de conexão
    ok, msg = dbm.test_connection(database="postgres")
    print("Teste postgres:", ok, msg)

    # Verificar se BANCO_OPERA existe
    exists = dbm.check_database_exists("BANCO_OPERA")
    print(f"BANCO_OPERA existe: {exists}")

    # Listar scripts disponíveis
    scripts = dbm.get_available_scripts()
    print(f"📜 Scripts encontrados: {len(scripts)}")
    for script in scripts:
        print(f"   - {script['filename']}")

    # Contar tabelas se o banco existir
    if exists:
        table_count = dbm.count_tables()
        print(f"📊 Tabelas no schema opera: {table_count}")

        tables = dbm.list_tables()
        print(f"📋 Lista de tabelas: {len(tables)}")
        for table in tables[:5]:  # Mostrar apenas as primeiras 5
            print(f"   - {table}")
        if len(tables) > 5:
            print(f"   ... e mais {len(tables) - 5} tabelas")

    print("✅ Teste do DatabaseManager concluído!")