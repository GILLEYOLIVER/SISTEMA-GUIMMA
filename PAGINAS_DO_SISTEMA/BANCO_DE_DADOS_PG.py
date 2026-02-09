# -*- coding: utf-8 -*-
"""
BANCO_DE_DADOS_PG.py — Versão Universal Windows/Mac (PyInstaller OK)
2026 • Compatível com Login, Usuários, Menu e páginas antigas.

✅ Agora lê OPERA_PG_DSN / OPERA_PG_SCHEMA
✅ Agora encontra config.json mesmo dentro do .app (Application Support / AppData)
✅ Mantém fallback por hosts/ports + criação automática do banco se não existir
"""

import os
import json
import socket
import platform
import sys
import io
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras


# ==============================================================================
# CONFIGURAÇÃO DE ENCODING (mantém seu comportamento)
# ==============================================================================
if platform.system() == "Windows":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
else:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    except Exception:
        pass


# ==============================================================================
# CORES PARA TERMINAL (mantém seu comportamento)
# ==============================================================================
class Colors:
    RESET = "\033[0m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    BG_GREEN = "\033[42m\033[37m"
    BG_RED = "\033[41m\033[37m"


if platform.system() == "Windows":
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


def log_ok(msg): print(f"{Colors.GREEN}[OK]{Colors.RESET} {msg}")
def log_warn(msg): print(f"{Colors.YELLOW}[AVISO]{Colors.RESET} {msg}")
def log_err(msg): print(f"{Colors.RED}[ERRO]{Colors.RESET} {msg}")
def log_info(msg): print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")
def log_debug(msg): print(f"{Colors.MAGENTA}[DEBUG]{Colors.RESET} {msg}")
def log_success(msg): print(f"{Colors.BG_GREEN}[SUCESSO]{Colors.RESET} {msg}")
def log_critical(msg): print(f"{Colors.BG_RED}[CRÍTICO]{Colors.RESET} {msg}")


# ==============================================================================
# CAMINHOS (PyInstaller / .app)
# ==============================================================================
def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _app_name() -> str:
    return "SistemaOpera"


def _user_config_dir() -> str:
    """
    Pasta segura para config do app instalado:
    - Windows: %APPDATA%\\SistemaOpera
    - macOS: ~/Library/Application Support/SistemaOpera
    - Linux: ~/.config/SistemaOpera
    """
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    elif system == "Darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")

    path = os.path.join(base, _app_name())
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass
    return path


def _resource_candidates() -> List[str]:
    """
    Candidatos adicionais quando empacotado (PyInstaller):
    - sys._MEIPASS/config.json (onefile/onedir)
    - .../Contents/Resources/config.json (macOS .app)
    """
    cands: List[str] = []
    if _is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            cands.append(os.path.join(meipass, "config.json"))

        # macOS: sys.executable -> .../SistemaOpera.app/Contents/MacOS/SistemaOpera
        try:
            exe_dir = os.path.dirname(sys.executable)
            resources_dir = os.path.normpath(os.path.join(exe_dir, "..", "Resources"))
            cands.append(os.path.join(resources_dir, "config.json"))
        except Exception:
            pass

    return cands


# ==============================================================================
# CONFIGURAÇÃO (agora com ENV + config.json no AppData/Application Support)
# ==============================================================================
DEFAULT_CFG: Dict[str, Any] = {
    "schema": "opera",
    "appname": "OPERA_APP",
    "defaults": {
        "dbname": "BANCO_OPERA",
        "user": "postgres",
        "password": "postgres",
    },
    "hosts": ["localhost", "127.0.0.1"],
    "ports": [5432, 5433],
    "connect_timeout": 8,
    "auto_detect_ports": True,
    "fallback_to_postgres": True,
    # opcional:
    # "dsn": "postgresql://user:pass@host:port/dbname"
}

# Variáveis de ambiente (PRIORIDADE MÁXIMA)
ENV_DSN = (os.environ.get("OPERA_PG_DSN") or "").strip()
ENV_SCHEMA = (os.environ.get("OPERA_PG_SCHEMA") or "").strip()

# candidatos do config.json
_MODULE_DIR = os.path.dirname(__file__)
_BASE_DIR = os.path.dirname(os.path.dirname(__file__))

_CFG_CANDIDATES = [
    os.path.join(_user_config_dir(), "config.json"),   # ✅ principal em app instalado
    os.path.join(_MODULE_DIR, "config.json"),
    os.path.join(_BASE_DIR, "config.json"),
    os.path.join(os.getcwd(), "config.json"),
] + _resource_candidates()

CFG_PATH = next((p for p in _CFG_CANDIDATES if p and os.path.exists(p)), _CFG_CANDIDATES[0])
CONFIG: Dict[str, Any] = dict(DEFAULT_CFG)

if os.path.exists(CFG_PATH):
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            user_cfg = json.load(f) or {}
        if isinstance(user_cfg, dict):
            CONFIG.update(user_cfg)
        log_ok(f"config.json carregado: {CFG_PATH}")
    except Exception as e:
        log_warn(f"Falha ao ler config.json ({CFG_PATH}): {e}")
else:
    log_warn(f"config.json não encontrado — usando padrão. (candidato principal: {CFG_PATH})")

# aplica ENV_SCHEMA por cima
if ENV_SCHEMA:
    CONFIG["schema"] = ENV_SCHEMA

# ==============================================================================
# DETECÇÃO DE PORTAS
# ==============================================================================
def _detect_ports() -> List[int]:
    ports = [5432, 5433, 5434, 5435]
    active: List[int] = []
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            if result == 0:
                active.append(port)
                log_debug(f"Porta {port} detectada")
        except Exception:
            continue
    return active if active else [5432]


if CONFIG.get("auto_detect_ports", True) and not ENV_DSN and not str(CONFIG.get("dsn", "")).strip():
    CONFIG["ports"] = _detect_ports()
    log_ok(f"Portas detectadas: {CONFIG['ports']}")


# ==============================================================================
# CONEXÃO
# ==============================================================================
_cached_conn = None


def _apply_session_settings(conn) -> None:
    schema = CONFIG.get("schema", "opera")
    appname = CONFIG.get("appname", "OPERA_APP")
    try:
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {schema}, public;")
            if appname:
                cur.execute("SET application_name TO %s;", (str(appname),))
    except Exception:
        # não quebra
        pass


def _create_connection_simple(host: str, port: int, dbname: str, user: str, password: str, timeout: int = 5):
    return psycopg2.connect(
        host=host,
        port=port,
        database=dbname,
        user=user,
        password=password,
        connect_timeout=timeout,
    )


def _create_connection_by_dsn(dsn: str):
    timeout = int(CONFIG.get("connect_timeout", 8))
    conn = psycopg2.connect(dsn, connect_timeout=timeout)
    _apply_session_settings(conn)
    return conn


def _create_connection():
    """
    Ordem:
    1) OPERA_PG_DSN (env)
    2) CONFIG["dsn"] (config.json)
    3) host/port/dbname/user/pass + autodetect + create db (se habilitado)
    """
    # 1) ENV DSN
    if ENV_DSN:
        log_info("Conectando via OPERA_PG_DSN (env)...")
        try:
            conn = _create_connection_by_dsn(ENV_DSN)
            log_success("Conectado via OPERA_PG_DSN")
            return conn
        except Exception as e:
            log_err(f"Falha via OPERA_PG_DSN: {e}")

    # 2) config DSN
    cfg_dsn = str(CONFIG.get("dsn", "")).strip()
    if cfg_dsn:
        log_info("Conectando via CONFIG['dsn'] (config.json)...")
        try:
            conn = _create_connection_by_dsn(cfg_dsn)
            log_success("Conectado via config.json (dsn)")
            return conn
        except Exception as e:
            log_err(f"Falha via config.json (dsn): {e}")

    # 3) modo antigo (host/port)
    host = (CONFIG.get("hosts") or ["localhost"])[0]
    user = (CONFIG.get("defaults") or {}).get("user", "postgres")
    pwd = (CONFIG.get("defaults") or {}).get("password", "postgres")
    target_db = (CONFIG.get("defaults") or {}).get("dbname", "BANCO_OPERA")
    timeout = int(CONFIG.get("connect_timeout", 8))
    fallback_to_postgres = bool(CONFIG.get("fallback_to_postgres", True))

    ports = CONFIG.get("ports") or [5432]

    for port in ports:
        try:
            log_info(f"Tentando {host}:{port} banco={target_db} user={user}")
            try:
                conn = _create_connection_simple(host, int(port), target_db, user, pwd, timeout=timeout)
                _apply_session_settings(conn)
                log_success(f"Conectado: {user}@{host}:{port}/{target_db}")
                return conn

            except psycopg2.OperationalError as e:
                error_msg = str(e)

                # Banco não existe -> tenta criar
                if ("does not exist" in error_msg or "não existe" in error_msg) and fallback_to_postgres:
                    log_warn(f"Banco {target_db} não existe. Criando...")

                    try:
                        temp_conn = _create_connection_simple(host, int(port), "postgres", user, pwd, timeout=5)
                        temp_conn.autocommit = True
                        cursor = temp_conn.cursor()

                        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
                        if not cursor.fetchone():
                            cursor.execute(f'CREATE DATABASE "{target_db}"')
                            log_ok(f"Banco {target_db} criado com sucesso")
                        else:
                            log_info(f"Banco {target_db} já existe")

                        cursor.close()
                        temp_conn.close()

                        conn = _create_connection_simple(host, int(port), target_db, user, pwd, timeout=timeout)
                        _apply_session_settings(conn)
                        log_success("Conectado ao banco criado")
                        return conn

                    except Exception as create_error:
                        log_err(f"Falha ao criar banco: {create_error}")
                        continue

                log_err(f"Erro de conexão: {error_msg}")
                continue

        except Exception as e:
            log_err(f"Falha na porta {port}: {e}")
            continue

    raise Exception(f"Não foi possível conectar. Portas testadas: {ports}")


def get_connection():
    global _cached_conn
    if _cached_conn:
        try:
            # mantém o cache vivo
            _cached_conn.rollback()
            return _cached_conn
        except Exception:
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
    except Exception:
        pass
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        yield conn, cur
        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        raise e
    finally:
        try:
            cur.close()
        except Exception:
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
    except Exception:
        return False


def require_ready(schemas=None):
    """
    ATENÇÃO: não fecha conexão cacheada.
    """
    try:
        schema = get_schema()

        if isinstance(schemas, (list, tuple)):
            schemas = [s for s in schemas if s == schema]
        elif isinstance(schemas, str):
            schemas = [schemas] if schemas == schema else [schema]
        else:
            schemas = [schema]

        with get_conn_cursor() as (conn, cur):
            for sch in schemas:
                cur.execute(
                    """
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name = %s
                    """,
                    (sch,),
                )
                if cur.fetchone() is None:
                    return False, f"Schema '{sch}' não existe no banco."

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
        schema = schema or get_schema()
        sql = """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_name = %s
            LIMIT 1;
        """
        r = fetch_one(sql, (schema, table.lower()))
        return bool(r)
    except Exception:
        return False


# ==============================================================================
# SISTEMA DE AUDITORIA AUTOMÁTICO - OPERA AUDIT SYSTEM (mantido)
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
        if usuario and isinstance(usuario, str):
            self._current_user = usuario
            print(f"🔐 [AUDIT] Usuário de auditoria definido: {usuario}")

    def get_current_user(self) -> str:
        return self._current_user

    def push_user_context(self, usuario: str):
        self._user_stack.append(self._current_user)
        self.set_current_user(usuario)

    def pop_user_context(self):
        if self._user_stack:
            self._current_user = self._user_stack.pop()

    def auto_detect_user(self, func, args, kwargs) -> str:
        if self._current_user != "Sistema":
            return self._current_user

        user_sources = ["usuario", "user", "username", "usuario_logado", "current_user", "logged_user"]
        for source in user_sources:
            if source in kwargs and kwargs[source]:
                return str(kwargs[source])

        if args:
            try:
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                for i, param_name in enumerate(params):
                    if i < len(args) and param_name in user_sources:
                        if args[i] and isinstance(args[i], str):
                            return args[i]
            except Exception:
                pass

            for arg in args:
                if (
                    isinstance(arg, str)
                    and len(arg) < 100
                    and not arg.startswith(("__", "SELECT", "INSERT", "UPDATE", "DELETE"))
                ):
                    return arg

        return "Sistema"

    def log_database_action(self, acao: str, pagina: str, detalhe: str = None, usuario: str = None):
        if not self.enabled:
            return False

        try:
            final_user = usuario or self.get_current_user()
            with get_conn_cursor() as (conn, cursor):
                cursor.execute(
                    "SELECT opera.registrar_log_usuario(%s, %s, %s, %s)",
                    (final_user, acao, pagina, detalhe or ""),
                )
                conn.commit()

            print(f"📝 [AUDIT] {final_user} -> {acao} | {pagina}")
            return True

        except Exception as e:
            print(f"🔴 [AUDIT ERROR] Falha no log: {e}")
            return False

    def log_crud_operation(self, operation: str, table: str, details: str = None):
        user = self.get_current_user()
        acao = f"{operation.upper()} em {table}"
        return self.log_database_action(acao, f"Database/{table}", details, user)


audit_system = OperaAuditSystem()


def with_audit(acao: str, pagina: str, detalhe_template: str = None, log_errors: bool = True):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            usuario = audit_system.auto_detect_user(func, args, kwargs)
            context = {
                "usuario": usuario,
                "args": str(args)[:200],
                "kwargs": str(kwargs)[:200],
                "timestamp": datetime.now().isoformat(),
            }

            try:
                result = func(*args, **kwargs)

                detalhe_final = detalhe_template
                if detalhe_template:
                    try:
                        context["result"] = str(result)[:500] if result else "N/A"
                        detalhe_final = detalhe_template.format(**context)
                    except Exception as template_error:
                        detalhe_final = f"{detalhe_template} | TemplateError: {template_error}"

                audit_system.log_database_action(f"✅ {acao}", pagina, detalhe_final, usuario)
                return result

            except Exception as e:
                if log_errors:
                    error_detail = f"Erro: {str(e)}"
                    if detalhe_template:
                        error_detail = f"{detalhe_template} | {error_detail}"
                    audit_system.log_database_action(f"❌ ERRO em {acao}", pagina, error_detail, usuario)
                raise

        return wrapper

    return decorator


def audit_crud(table: str, operation: str):
    return with_audit(
        f"{operation.upper()} {table}",
        f"CRUD/{table}",
        f"Operação {operation} na tabela {table}",
    )


_original_execute = execute
_original_fetch_one = fetch_one


@functools.wraps(_original_execute)
def execute_with_audit(sql: str, params=None):
    result = _original_execute(sql, params)
    sql_upper = sql.strip().upper()

    if any(sql_upper.startswith(op) for op in ["INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"]):
        detalhe = f"SQL: {sql_upper.split()[0]} | Linhas afetadas: {result}"
        if params:
            detalhe += f" | Params: {str(params)[:100]}"

        audit_system.log_database_action("EXECUTOU SQL", "Database/Execute", detalhe)

    return result


@functools.wraps(_original_fetch_one)
def fetch_one_with_audit(sql: str, params=None):
    result = _original_fetch_one(sql, params)
    sql_upper = sql.strip().upper()

    if any(term in sql_upper for term in ["DELETE", "DROP", "TRUNCATE", "GRANT", "REVOKE"]):
        audit_system.log_database_action(
            "CONSULTA ADMINISTRATIVA",
            "Database/Query",
            f"SQL: {sql_upper.split()[0]}...",
            audit_system.get_current_user(),
        )

    return result


execute = execute_with_audit
fetch_one = fetch_one_with_audit


def set_audit_user(usuario: str):
    """CHAME ESTA FUNÇÃO APÓS O LOGIN!"""
    audit_system.set_current_user(usuario)


def get_audit_user() -> str:
    return audit_system.get_current_user()


def enable_audit_logs():
    audit_system.enabled = True
    print("✅ Sistema de auditoria ATIVADO")


def disable_audit_logs():
    audit_system.enabled = False
    print("⏸️ Sistema de auditoria DESATIVADO")


def quick_audit_log(acao: str, pagina: str, detalhe: str = None):
    return audit_system.log_database_action(acao, pagina, detalhe)


def with_user_context(usuario: str):
    class UserContext:
        def __enter__(self):
            audit_system.push_user_context(usuario)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            audit_system.pop_user_context()

    return UserContext()


def audit_login(func):
    return with_audit(
        "Login no sistema",
        "Autenticação",
        "Usuário {usuario} autenticado",
        log_errors=True,
    )(func)


def audit_user_create(func):
    return with_audit(
        "CRIAÇÃO de usuário",
        "Admin/Usuários",
        "Novo usuário: {kwargs.get('novo_usuario', 'N/A')} criado por {usuario}",
        log_errors=True,
    )(func)


def audit_user_edit(func):
    return with_audit(
        "EDIÇÃO de usuário",
        "Admin/Usuários",
        "Usuário editado: {kwargs.get('usuario_id', 'N/A')} por {usuario}",
        log_errors=True,
    )(func)


def audit_model_create(func):
    return with_audit(
        "CRIAÇÃO de modelo",
        "Cadastro/Modelos",
        "Modelo {result} criado por {usuario}",
        log_errors=True,
    )(func)


def audit_model_edit(func):
    return with_audit(
        "EDIÇÃO de modelo",
        "Cadastro/Modelos",
        "Modelo ID: {kwargs.get('modelo_id', 'N/A')} editado por {usuario}",
        log_errors=True,
    )(func)


def audit_model_delete(func):
    return with_audit(
        "EXCLUSÃO de modelo",
        "Cadastro/Modelos",
        "Modelo ID: {kwargs.get('modelo_id', 'N/A')} excluído por {usuario}",
        log_errors=True,
    )(func)


def audit_corte_create(func):
    return with_audit(
        "CRIAÇÃO de ordem de corte",
        "Produção/Cortes",
        "Ordem de corte criada por {usuario}",
        log_errors=True,
    )(func)


def audit_corte_finalize(func):
    return with_audit(
        "FINALIZAÇÃO de corte",
        "Produção/Cortes",
        "Corte finalizado por {usuario}",
        log_errors=True,
    )(func)


print("✅ Sistema de Auditoria OPERA carregado com sucesso!")


# ==============================================================================
# TESTE UNIVERSAL
# ==============================================================================
if __name__ == "__main__":
    print(f"\n{Colors.CYAN}=== BANCO_DE_DADOS_PG - UNIVERSAL WINDOWS/MAC ==={Colors.RESET}")
    print(f"Sistema: {platform.system()}  |  Frozen: {_is_frozen()}")
    print(f"CFG_PATH: {CFG_PATH}")
    print(f"ENV OPERA_PG_DSN: {'SIM' if ENV_DSN else 'NÃO'}")
    print(f"ENV OPERA_PG_SCHEMA: {ENV_SCHEMA or '(vazio)'}")
    print(f"Host: {(CONFIG.get('hosts') or ['?'])[0]}")
    print(f"Portas: {CONFIG.get('ports')}")
    print(f"Banco: {(CONFIG.get('defaults') or {}).get('dbname')}")
    print(f"Schema: {CONFIG.get('schema')}")
    print(f"Usuário: {(CONFIG.get('defaults') or {}).get('user')}")
    print("=" * 60)

    try:
        conn = get_connection()
        log_success("✅ Conexão estabelecida com sucesso!")

        db_info = fetch_one("SELECT version() as versao, current_database() as banco, current_user as usuario;")
        if db_info:
            log_ok(f"Banco: {db_info['banco']}")
            log_ok(f"Usuário: {db_info['usuario']}")
            log_ok(f"PostgreSQL: {db_info['versao'].split(',')[0]}")

        schema_result = fetch_one("SELECT current_schema() as schema;")
        if schema_result:
            log_ok(f"Schema: {schema_result['schema']}")

        tabelas = list_tables()
        log_ok(f"Tabelas encontradas: {len(tabelas)}")

        status, mensagem = require_ready()
        if status:
            log_ok(f"Sistema pronto: {mensagem}")
        else:
            log_err(f"Sistema não pronto: {mensagem}")

        log_success("🎉 SISTEMA FUNCIONANDO PERFEITAMENTE!")

    except Exception as e:
        log_critical(f"❌ FALHA: {e}")
        print(f"\n{Colors.YELLOW}💡 DICA:{Colors.RESET}")
        print(f"Crie um config.json em: {_user_config_dir()}/config.json")
        print("ou defina OPERA_PG_DSN / OPERA_PG_SCHEMA (env).")
        raise
