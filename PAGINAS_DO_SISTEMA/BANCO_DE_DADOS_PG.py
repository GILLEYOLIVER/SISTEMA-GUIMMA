# -*- coding: utf-8 -*-
"""
BANCO_DE_DADOS_PG.py — Versão Universal Windows/Mac
2025 • Compatível com Login, Usuários, Menu e todas as páginas antigas.
"""

import os
import json
import psycopg2
import psycopg2.extras
import socket
import platform
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

# ==============================================================================
# CONFIGURAÇÃO DE ENCODING
# ==============================================================================
import sys
import io

if platform.system() == "Windows":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# ==============================================================================
# CORES PARA TERMINAL
# ==============================================================================
class Colors:
    RESET = '\033[0m'
    GREEN = '\033[32m'
    RED = '\033[31m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    MAGENTA = '\033[35m'
    BG_GREEN = '\033[42m\033[37m'
    BG_RED = '\033[41m\033[37m'


if platform.system() == "Windows":
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except:
        pass


def log_ok(msg):    print(f"{Colors.GREEN}[OK]{Colors.RESET} {msg}")


def log_warn(msg):  print(f"{Colors.YELLOW}[AVISO]{Colors.RESET} {msg}")


def log_err(msg):   print(f"{Colors.RED}[ERRO]{Colors.RESET} {msg}")


def log_info(msg):  print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")


def log_debug(msg): print(f"{Colors.MAGENTA}[DEBUG]{Colors.RESET} {msg}")


def log_success(msg): print(f"{Colors.BG_GREEN}[SUCESSO]{Colors.RESET} {msg}")


def log_critical(msg): print(f"{Colors.BG_RED}[CRÍTICO]{Colors.RESET} {msg}")


# ==============================================================================
# CONFIGURAÇÃO SIMPLIFICADA - IGNORA VARIÁVEIS DE AMBIENTE PROBLEMÁTICAS
# ==============================================================================
DEFAULT_CFG = {
    "schema": "opera",
    "appname": "OPERA_APP",
    "defaults": {
        "dbname": "BANCO_OPERA",
        "user": "postgres",
        "password": "postgres"
    },
    "hosts": ["localhost", "127.0.0.1"],
    "ports": [5432, 5433],
    "connect_timeout": 8,
    "auto_detect_ports": True,
    "fallback_to_postgres": True
}

_BASE_DIR = os.path.dirname(os.path.dirname(__file__))
_MODULE_DIR = os.path.dirname(__file__)
_CFG_CANDIDATES = [
    os.path.join(_MODULE_DIR, "config.json"),
    os.path.join(_BASE_DIR, "config.json"),
    os.path.join(os.getcwd(), "config.json"),
]
CFG_PATH = next((path for path in _CFG_CANDIDATES if os.path.exists(path)), _CFG_CANDIDATES[0])
CONFIG = DEFAULT_CFG.copy()

if os.path.exists(CFG_PATH):
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        CONFIG.update(user_cfg)
        log_ok("config.json carregado com sucesso.")
    except Exception as e:
        log_warn(f"Falha ao ler config.json: {e}")
else:
    log_warn("config.json não encontrado — usando configurações padrão.")


# ==============================================================================
# DETECÇÃO DE PORTAS
# ==============================================================================
def _detect_ports():
    ports = [5432, 5433, 5434, 5435]
    active = []
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            if result == 0:
                active.append(port)
                log_debug(f"Porta {port} detectada")
        except:
            continue
    return active if active else [5432]


if CONFIG.get("auto_detect_ports", True):
    CONFIG["ports"] = _detect_ports()
    log_ok(f"Portas detectadas: {CONFIG['ports']}")

# ==============================================================================
# CONEXÃO DIRETA - MÉTODO UNIVERSAL
# ==============================================================================
_cached_conn = None


def _create_connection_simple(host, port, dbname, user, password, timeout=5):
    """Conexão direta - funciona em Windows e Mac"""
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=dbname,
            user=user,
            password=password,
            connect_timeout=timeout
        )
        return conn
    except Exception as e:
        raise e


def _create_connection():
    """Cria conexão de forma robusta para ambos OS"""
    host = CONFIG["hosts"][0]
    user = CONFIG["defaults"]["user"]
    pwd = CONFIG["defaults"]["password"]
    target_db = CONFIG["defaults"]["dbname"]

    for port in CONFIG["ports"]:
        try:
            log_info(f"Tentando {host}:{port} banco={target_db} user={user}")

            # Tenta conexão direta - MÉTODO PRINCIPAL
            try:
                conn = _create_connection_simple(
                    host=host,
                    port=port,
                    dbname=target_db,
                    user=user,
                    password=pwd,
                    timeout=CONFIG.get("connect_timeout", 8)
                )

                # Configurações pós-conexão
                with conn.cursor() as cur:
                    cur.execute(f"SET search_path TO {CONFIG['schema']}, public;")
                    if "appname" in CONFIG:
                        cur.execute(f"SET application_name TO '{CONFIG['appname']}';")

                log_success(f"Conectado: {user}@{host}:{port}/{target_db}")
                return conn

            except psycopg2.OperationalError as e:
                error_msg = str(e)

                # Banco não existe - cria automaticamente
                if "does not exist" in error_msg or "não existe" in error_msg:
                    log_warn(f"Banco {target_db} não existe. Criando...")

                    try:
                        # Conecta ao postgres para criar o banco
                        temp_conn = _create_connection_simple(
                            host=host,
                            port=port,
                            dbname="postgres",
                            user=user,
                            password=pwd,
                            timeout=5
                        )
                        temp_conn.autocommit = True
                        cursor = temp_conn.cursor()

                        # Cria o banco se não existir
                        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
                        if not cursor.fetchone():
                            cursor.execute(f'CREATE DATABASE "{target_db}"')
                            log_ok(f"Banco {target_db} criado com sucesso")
                        else:
                            log_info(f"Banco {target_db} já existe")

                        cursor.close()
                        temp_conn.close()

                        # Tenta conectar ao banco criado
                        conn = _create_connection_simple(
                            host=host,
                            port=port,
                            dbname=target_db,
                            user=user,
                            password=pwd,
                            timeout=CONFIG.get("connect_timeout", 8)
                        )

                        with conn.cursor() as cur:
                            cur.execute(f"SET search_path TO {CONFIG['schema']}, public;")

                        log_success(f"Conectado ao banco criado")
                        return conn

                    except Exception as create_error:
                        log_err(f"Falha ao criar banco: {create_error}")
                        continue
                else:
                    # Outro erro de conexão
                    log_err(f"Erro de conexão: {error_msg}")
                    continue

        except Exception as e:
            log_err(f"Falha na porta {port}: {str(e)}")
            continue

    raise Exception(f"Não foi possível conectar em nenhuma porta: {CONFIG['ports']}")


def get_connection():
    global _cached_conn
    if _cached_conn:
        try:
            _cached_conn.rollback()
            return _cached_conn
        except:
            _cached_conn = None

    _cached_conn = _create_connection()
    return _cached_conn


def get_conn():
    return get_connection()


# ==============================================================================
# CURSOR SEGURO
# ==============================================================================
@contextmanager
def get_conn_cursor():
    conn = get_connection()
    try:
        conn.rollback()
    except:
        pass
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        yield conn, cur
        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        raise e
    finally:
        try:
            cur.close()
        except:
            pass


# ==============================================================================
# FUNÇÕES PADRÃO
# ==============================================================================
def fetch_one(sql: str, params=None):
    with get_conn_cursor() as (con, cur):
        cur.execute(sql, params)
        r = cur.fetchone()
        return dict(r) if r else None


def fetch_all(sql: str, params=None):
    with get_conn_cursor() as (con, cur):
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows] if rows else []


def execute(sql: str, params=None) -> int:
    with get_conn_cursor() as (con, cur):
        cur.execute(sql, params)
        return cur.rowcount or 0


# ==============================================================================
# FUNÇÕES DE COMPATIBILIDADE
# ==============================================================================
def get_schema():
    return CONFIG.get("schema", "opera")


_pg_exec = execute


def ready_check() -> bool:
    try:
        fetch_one("SELECT 1 AS ok;")
        return True
    except:
        return False


def require_ready(schemas=None):
    try:
        schema = get_schema()

        if isinstance(schemas, (list, tuple)):
            schemas = [s for s in schemas if s == schema]
        elif isinstance(schemas, str):
            schemas = [schemas] if schemas == schema else [schema]
        else:
            schemas = [schema]

        conn = get_conn()
        try:
            cur = conn.cursor()
            for sch in schemas:
                cur.execute("""
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name = %s
                """, (sch,))
                if cur.fetchone() is None:
                    return False, f"Schema '{sch}' não existe no banco."
        finally:
            conn.close()

        return True, "OK"
    except Exception as e:
        return False, f"Erro ao validar schema: {e}"


def load_config():
    return CONFIG


def get_config():
    return CONFIG


def list_tables(schema: str = None) -> list:
    if schema is None:
        schema = get_schema()

    sql = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
        ORDER BY table_name;
    """

    rows = fetch_all(sql, (schema,))
    return [r["table_name"] for r in rows]


def list_columns(table: str, schema: str = None) -> list:
    if schema is None:
        schema = get_schema()

    sql = """
        SELECT 
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
            a.attnotnull AS not_null,
            (SELECT EXISTS (
                SELECT 1 
                FROM pg_index i 
                WHERE i.indrelid = c.oid AND i.indisprimary AND a.attnum = ANY(i.indkey)
            )) AS is_primary
        FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE c.relname = %s
        AND n.nspname = %s
        AND a.attnum > 0
        AND NOT a.attisdropped
        ORDER BY a.attnum;
    """

    rows = fetch_all(sql, (table, schema))
    return rows or []


def table_exists(table: str, schema: str | None = None) -> bool:
    try:
        conn = get_conn()
        try:
            cur = conn.cursor()
            schema = schema or get_schema()
            cur.execute("""
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s
                AND table_name = %s
                LIMIT 1;
            """, (schema, table.lower()))
            return cur.fetchone() is not None
        finally:
            conn.close()
    except Exception:
        return False


# ==============================================================================
# SISTEMA DE AUDITORIA AUTOMÁTICO - OPERA AUDIT SYSTEM
# ==============================================================================

import functools
import inspect
from datetime import datetime


class OperaAuditSystem:
    """
    Sistema corporativo de auditoria e logs automáticos
    """

    def __init__(self):
        self.enabled = True
        self._current_user = "Sistema"
        self._user_stack = []

    def set_current_user(self, usuario: str):
        """Define o usuário atual para auditoria"""
        if usuario and isinstance(usuario, str):
            self._current_user = usuario
            print(f"🔐 [AUDIT] Usuário de auditoria definido: {usuario}")

    def get_current_user(self) -> str:
        """Obtém o usuário atual"""
        return self._current_user

    def push_user_context(self, usuario: str):
        """Empilha contexto de usuário (para operações aninhadas)"""
        self._user_stack.append(self._current_user)
        self.set_current_user(usuario)

    def pop_user_context(self):
        """Desempilha contexto de usuário"""
        if self._user_stack:
            self._current_user = self._user_stack.pop()

    def auto_detect_user(self, func, args, kwargs) -> str:
        """
        Detecta automaticamente o usuário a partir dos parâmetros da função
        """
        # 1. Usuário do contexto global
        if self._current_user != "Sistema":
            return self._current_user

        # 2. Procura em kwargs
        user_sources = ['usuario', 'user', 'username', 'usuario_logado', 'current_user', 'logged_user']
        for source in user_sources:
            if source in kwargs and kwargs[source]:
                return str(kwargs[source])

        # 3. Procura em args (analisa assinatura da função)
        if args:
            try:
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())

                for i, param_name in enumerate(params):
                    if i < len(args) and param_name in user_sources:
                        if args[i] and isinstance(args[i], str):
                            return args[i]
            except:
                pass

            # Fallback: primeiro argumento que seja string razoável
            for arg in args:
                if (isinstance(arg, str) and
                        len(arg) < 100 and
                        not arg.startswith(('__', 'SELECT', 'INSERT', 'UPDATE', 'DELETE'))):
                    return arg

        return "Sistema"

    def log_database_action(self, acao: str, pagina: str, detalhe: str = None, usuario: str = None):
        """
        Registra ação no banco de dados de forma segura e profissional
        """
        if not self.enabled:
            return False

        try:
            final_user = usuario or self.get_current_user()

            with get_conn_cursor() as (conn, cursor):
                cursor.execute(
                    "SELECT opera.registrar_log_usuario(%s, %s, %s, %s)",
                    (final_user, acao, pagina, detalhe or '')
                )
                conn.commit()

            print(f"📝 [AUDIT] {final_user} -> {acao} | {pagina}")
            return True

        except Exception as e:
            # Não quebra a aplicação em caso de falha no log
            print(f"🔴 [AUDIT ERROR] Falha no log: {e}")
            return False

    def log_crud_operation(self, operation: str, table: str, details: str = None):
        """Log simplificado para operações CRUD"""
        user = self.get_current_user()
        acao = f"{operation.upper()} em {table}"
        return self.log_database_action(acao, f"Database/{table}", details, user)


# Instância global do sistema de auditoria
audit_system = OperaAuditSystem()


# ==============================================================================
# DECORATORS PARA AUDITORIA AUTOMÁTICA
# ==============================================================================

def with_audit(acao: str, pagina: str, detalhe_template: str = None, log_errors: bool = True):
    """
    Decorator profissional para auditoria automática de funções

    Args:
        acao: Descrição da ação (ex: "CRIAÇÃO de usuário")
        pagina: Módulo/página (ex: "Configurações/Usuários")
        detalhe_template: Template com {usuario}, {result}, {args}, {kwargs}
        log_errors: Se deve registrar erros
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Detecta usuário automaticamente
            usuario = audit_system.auto_detect_user(func, args, kwargs)

            # Contexto para templates
            context = {
                'usuario': usuario,
                'args': str(args)[:200],
                'kwargs': str(kwargs)[:200],
                'timestamp': datetime.now().isoformat()
            }

            try:
                # Executa a função original
                result = func(*args, **kwargs)

                # Prepara detalhe com template
                detalhe_final = detalhe_template
                if detalhe_template:
                    try:
                        context['result'] = str(result)[:500] if result else "N/A"
                        detalhe_final = detalhe_template.format(**context)
                    except Exception as template_error:
                        detalhe_final = f"{detalhe_template} | TemplateError: {template_error}"

                # Registra log de sucesso
                audit_system.log_database_action(
                    f"✅ {acao}",
                    pagina,
                    detalhe_final,
                    usuario
                )

                return result

            except Exception as e:
                # Registra log de erro
                if log_errors:
                    error_detail = f"Erro: {str(e)}"
                    if detalhe_template:
                        error_detail = f"{detalhe_template} | {error_detail}"

                    audit_system.log_database_action(
                        f"❌ ERRO em {acao}",
                        pagina,
                        error_detail,
                        usuario
                    )

                # Propaga a exceção original
                raise

        return wrapper

    return decorator


def audit_crud(table: str, operation: str):
    """
    Decorator simplificado para operações CRUD
    """
    return with_audit(
        f"{operation.upper()} {table}",
        f"CRUD/{table}",
        f"Operação {operation} na tabela {table}"
    )


# ==============================================================================
# FUNÇÕES DE BANCO COM AUDITORIA AUTOMÁTICA
# ==============================================================================

# Guarda as funções originais
_original_execute = execute
_original_fetch_one = fetch_one


@functools.wraps(_original_execute)
def execute_with_audit(sql: str, params=None):
    """
    Versão com auditoria automática da função execute
    """
    result = _original_execute(sql, params)

    # Log automático para operações DML importantes
    sql_upper = sql.strip().upper()

    if any(sql_upper.startswith(op) for op in ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP']):
        # Detalhes resumidos para não sobrecarregar os logs
        detalhe = f"SQL: {sql_upper.split()[0]} | Linhas afetadas: {result}"

        if params:
            detalhe += f" | Params: {str(params)[:100]}"

        audit_system.log_database_action(
            "EXECUTOU SQL",
            "Database/Execute",
            detalhe
        )

    return result


@functools.wraps(_original_fetch_one)
def fetch_one_with_audit(sql: str, params=None):
    """
    Versão com auditoria para consultas importantes
    """
    result = _original_fetch_one(sql, params)

    # Log apenas para consultas complexas ou administrativas
    sql_upper = sql.strip().upper()

    if any(term in sql_upper for term in ['DELETE', 'DROP', 'TRUNCATE', 'GRANT', 'REVOKE']):
        audit_system.log_database_action(
            "CONSULTA ADMINISTRATIVA",
            "Database/Query",
            f"SQL: {sql_upper.split()[0]}...",
            audit_system.get_current_user()
        )

    return result


# Substitui as funções originais
execute = execute_with_audit
fetch_one = fetch_one_with_audit


# ==============================================================================
# API PÚBLICA DO SISTEMA DE AUDITORIA
# ==============================================================================

def set_audit_user(usuario: str):
    """
    Define o usuário atual para o sistema de auditoria
    CHAME ESTA FUNÇÃO APÓS O LOGIN!
    """
    audit_system.set_current_user(usuario)


def get_audit_user() -> str:
    """Obtém o usuário atual de auditoria"""
    return audit_system.get_current_user()


def enable_audit_logs():
    """Ativa o sistema de auditoria"""
    audit_system.enabled = True
    print("✅ Sistema de auditoria ATIVADO")


def disable_audit_logs():
    """Desativa o sistema de auditoria (para testes)"""
    audit_system.enabled = False
    print("⏸️ Sistema de auditoria DESATIVADO")


def quick_audit_log(acao: str, pagina: str, detalhe: str = None):
    """
    Log rápido para ações manuais
    """
    return audit_system.log_database_action(acao, pagina, detalhe)


def with_user_context(usuario: str):
    """
    Context manager para operações com usuário específico
    """

    class UserContext:
        def __enter__(self):
            audit_system.push_user_context(usuario)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            audit_system.pop_user_context()

    return UserContext()


# ==============================================================================
# DECORATORS PRÉ-DEFINIDOS PARA OPERAÇÕES COMUNS
# ==============================================================================

# Decorators para módulo de usuários
def audit_login(func):
    return with_audit(
        "Login no sistema",
        "Autenticação",
        "Usuário {usuario} autenticado",
        log_errors=True
    )(func)


def audit_user_create(func):
    return with_audit(
        "CRIAÇÃO de usuário",
        "Admin/Usuários",
        "Novo usuário: {kwargs.get('novo_usuario', 'N/A')} criado por {usuario}",
        log_errors=True
    )(func)


def audit_user_edit(func):
    return with_audit(
        "EDIÇÃO de usuário",
        "Admin/Usuários",
        "Usuário editado: {kwargs.get('usuario_id', 'N/A')} por {usuario}",
        log_errors=True
    )(func)


# Decorators para módulo de modelos
def audit_model_create(func):
    return with_audit(
        "CRIAÇÃO de modelo",
        "Cadastro/Modelos",
        "Modelo {result} criado por {usuario}",
        log_errors=True
    )(func)


def audit_model_edit(func):
    return with_audit(
        "EDIÇÃO de modelo",
        "Cadastro/Modelos",
        "Modelo ID: {kwargs.get('modelo_id', 'N/A')} editado por {usuario}",
        log_errors=True
    )(func)


def audit_model_delete(func):
    return with_audit(
        "EXCLUSÃO de modelo",
        "Cadastro/Modelos",
        "Modelo ID: {kwargs.get('modelo_id', 'N/A')} excluído por {usuario}",
        log_errors=True
    )(func)


# Decorators para módulo de cortes
def audit_corte_create(func):
    return with_audit(
        "CRIAÇÃO de ordem de corte",
        "Produção/Cortes",
        "Ordem de corte criada por {usuario}",
        log_errors=True
    )(func)


def audit_corte_finalize(func):
    return with_audit(
        "FINALIZAÇÃO de corte",
        "Produção/Cortes",
        "Corte finalizado por {usuario}",
        log_errors=True
    )(func)


print("✅ Sistema de Auditoria OPERA carregado com sucesso!")

# ==============================================================================
# FIM DO MÓDULO DE ACESSO
# ==============================================================================


# ==============================================================================
# TESTE UNIVERSAL
# ==============================================================================
if __name__ == "__main__":
    print(f"\n{Colors.CYAN}=== BANCO_DE_DADOS_PG - UNIVERSAL WINDOWS/MAC ==={Colors.RESET}")
    print(f"Sistema: {platform.system()}")
    print(f"Host: {CONFIG['hosts'][0]}")
    print(f"Portas: {CONFIG['ports']}")
    print(f"Banco: {CONFIG['defaults']['dbname']}")
    print(f"Schema: {CONFIG['schema']}")
    print(f"Usuário: {CONFIG['defaults']['user']}")
    print("=" * 60)

    try:
        conn = get_connection()
        log_success("✅ Conexão estabelecida com sucesso!")

        # Testes básicos
        print(f"\n{Colors.BLUE}Executando testes...{Colors.RESET}")

        # Teste 1: Informações do banco
        db_info = fetch_one("SELECT version() as versao, current_database() as banco, current_user as usuario;")
        if db_info:
            log_ok(f"Banco: {db_info['banco']}")
            log_ok(f"Usuário: {db_info['usuario']}")
            log_ok(f"PostgreSQL: {db_info['versao'].split(',')[0]}")

        # Teste 2: Schema
        schema_result = fetch_one("SELECT current_schema() as schema;")
        if schema_result:
            log_ok(f"Schema: {schema_result['schema']}")

        # Teste 3: Tabelas
        tabelas = list_tables()
        log_ok(f"Tabelas encontradas: {len(tabelas)}")

        # Teste 4: Ready check
        status, mensagem = require_ready()
        if status:
            log_ok(f"Sistema pronto: {mensagem}")
        else:
            log_err(f"Sistema não pronto: {mensagem}")

        log_success("🎉 SISTEMA FUNCIONANDO PERFEITAMENTE!")

    except Exception as e:
        log_critical(f"❌ FALHA: {e}")

        # Informações de debug
        print(f"\n{Colors.YELLOW}=== INFORMAÇÕES PARA DEBUG ==={Colors.RESET}")
        print(f"Configuração carregada:")
        print(f"  Host: {CONFIG['hosts'][0]}")
        print(f"  Portas: {CONFIG['ports']}")
        print(f"  Banco: {CONFIG['defaults']['dbname']}")
        print(f"  Usuário: {CONFIG['defaults']['user']}")
        print(f"  Schema: {CONFIG['schema']}")

        print(f"\n{Colors.YELLOW}💡 SOLUÇÕES:{Colors.RESET}")
        print("1. Verifique se o PostgreSQL está rodando na porta 5433")
        print("2. Teste manualmente: psql -h localhost -p 5433 -U postgres -d postgres")
        print("3. Verifique a senha no config.json")
        print("4. No Windows, execute como Administrador se necessário")

        exit(1)
