import json
import os
import socket
import subprocess
import sys
from pathlib import Path


def run_ps_as_admin(ps1_path: Path) -> None:
    # Você pode chamar isso do seu app/instalador; aqui é simples via subprocess.
    # Execute o .ps1 manualmente como Admin se preferir.
    pass


def detect_server_ip() -> str:
    # pega IP “principal” do Windows (sem 127.*)
    hostname = socket.gethostname()
    ips = socket.gethostbyname_ex(hostname)[2]
    ips = [ip for ip in ips if not ip.startswith("127.")]
    return ips[0] if ips else "127.0.0.1"


def ensure_psycopg2():
    try:
        import psycopg2  # noqa
    except ImportError:
        raise RuntimeError("psycopg2 não instalado. Instale: pip install psycopg2-binary")


def connect_psycopg2(dbname: str, user: str, password: str, host="localhost", port=5432):
    import psycopg2

    # Em Windows, evita dor de cabeça com encoding de mensagens
    if sys.platform.startswith("win"):
        os.environ.setdefault("PGCLIENTENCODING", "WIN1252")
        os.environ.setdefault("PGOPTIONS", "-c client_encoding=WIN1252")
    return psycopg2.connect(
        host=host,
        port=int(port),
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=5,
    )


def exec_sql_file(cur, sql_path: Path):
    sql = sql_path.read_text(encoding="utf-8", errors="replace")
    cur.execute(sql)


def _setup_config_candidates() -> list[Path]:
    here = Path(__file__).resolve().parent
    appdata = os.getenv("APPDATA")

    cands = []
    if appdata:
        cands.extend([
            Path(appdata) / "SistemaOpera" / "config.json",
            Path(appdata) / "SistemaOpera" / "PAGINAS_DO_SISTEMA" / "config.json",
        ])

    cands.extend([
        Path.home() / "Library" / "Application Support" / "SistemaOpera" / "config.json",
        Path.home() / "Library" / "Application Support" / "SistemaOpera" / "PAGINAS_DO_SISTEMA" / "config.json",
        Path("/Library/Application Support/SistemaOpera/config.json"),
        Path("/Library/Application Support/SistemaOpera/PAGINAS_DO_SISTEMA/config.json"),
        here / "PAGINAS_DO_SISTEMA" / "config.json",
        here / "config.json",
    ])

    unique = []
    seen = set()
    for p in cands:
        k = str(p)
        if k not in seen:
            seen.add(k)
            unique.append(p)
    return unique


def _executar_interface_original_setup() -> bool:
    """Abre a interface original do projeto (SETUP_BANCO.py)."""
    here = Path(__file__).resolve().parent
    script = here / "PAGINAS_DO_SISTEMA" / "SETUP_BANCO.py"
    if not script.exists():
        script = here / "packaging" / "SETUP_BANCO.py"

    if not script.exists():
        print("SETUP_BANCO.py não encontrado para abrir a interface original.")
        return False

    code = subprocess.call([sys.executable, str(script)])
    return code == 0


def _carregar_config_validada() -> dict | None:
    for path in _setup_config_candidates():
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if not bool(data.get("validated_ok", False)):
            continue

        host = data.get("host")
        port = data.get("port")
        dbname = data.get("dbname")
        user = data.get("user")
        password = data.get("password")
        schema = data.get("schema") or data.get("pg_schema") or "opera"

        defaults = data.get("defaults") if isinstance(data.get("defaults"), dict) else {}
        hosts = data.get("hosts") if isinstance(data.get("hosts"), list) else []
        ports = data.get("ports") if isinstance(data.get("ports"), list) else []

        host = host or (hosts[0] if hosts else "localhost")
        port = port or (ports[0] if ports else 5432)
        dbname = dbname or defaults.get("dbname") or "BANCO_OPERA"
        user = user or defaults.get("user") or "postgres"
        password = password or defaults.get("password") or ""

        try:
            port = int(port)
        except Exception:
            port = 5432

        return {
            "host": str(host),
            "port": int(port),
            "dbname": str(dbname),
            "superuser": str(user),
            "superpass": str(password),
            "schema": str(schema),
        }

    return None


def main():
    scripts_dir = Path(__file__).parent / "scripts"
    script_order = [
        "1_CRIAR_BANCO.sql",
        "2_CRIAR_SCHEMA.sql",
        "3_CRIAR_TABELAS.sql",
    ]

    ensure_psycopg2()

    print("Abrindo interface original de configuração do banco...")
    if not _executar_interface_original_setup():
        print("Configuração cancelada/encerrada antes de concluir o setup.")
        return 1

    cfg = _carregar_config_validada()
    if not cfg:
        print("Nenhum config validado foi encontrado após o setup.")
        return 1

    host = cfg["host"]
    port = cfg["port"]
    superuser = cfg["superuser"]
    superpass = cfg["superpass"]
    dbname = cfg["dbname"]
    schema = cfg["schema"]

    # Usuário da aplicação pode ser configurado por env, senão usa o usuário definido no setup.
    app_user = os.environ.get("OPERA_PG_APP_USER", superuser)
    app_pass = os.environ.get("OPERA_PG_APP_PASS", superpass)

    # 1) Conectar no postgres (banco padrão) como superuser
    conn = connect_psycopg2(dbname="postgres", user=superuser, password=superpass, host=host, port=port)
    conn.autocommit = True
    cur = conn.cursor()

    # 2) Verificar encoding do servidor (recomendado: UTF8)
    cur.execute("SHOW server_encoding;")
    enc = cur.fetchone()[0]
    print("server_encoding =", enc)
    if enc.upper() != "UTF8":
        print("ATENCAO: server_encoding não é UTF8. Recomendo recriar o cluster em UTF8 para evitar erros.")

    # 3) Criar usuário do app (se não existir)
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname=%s;", (app_user,))
    if cur.fetchone() is None:
        cur.execute(f"CREATE ROLE {app_user} WITH LOGIN PASSWORD %s;", (app_pass,))
        print("Criou role:", app_user)
    else:
        print("Role já existe:", app_user)

    # 4) Criar banco do app (se não existir) com owner = app_user
    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s;", (dbname,))
    if cur.fetchone() is None:
        cur.execute(f"CREATE DATABASE {dbname} OWNER {app_user} TEMPLATE template0 ENCODING 'UTF8';")
        print("Criou database:", dbname)
    else:
        print("Database já existe:", dbname)

    cur.close()
    conn.close()

    # 5) Conectar no banco do app e criar schema + permissões base
    conn2 = connect_psycopg2(dbname=dbname, user=superuser, password=superpass, host=host, port=port)
    conn2.autocommit = True
    cur2 = conn2.cursor()

    cur2.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name=%s;", (schema,))
    if cur2.fetchone() is None:
        cur2.execute(f"CREATE SCHEMA {schema} AUTHORIZATION {app_user};")
        print("Criou schema:", schema)
    else:
        print("Schema já existe:", schema)

    cur2.execute(f"GRANT ALL ON SCHEMA {schema} TO {app_user};")
    cur2.execute(f"ALTER ROLE {app_user} SET search_path TO {schema};")

    # 6) Rodar scripts SQL (se existirem)
    for name in script_order:
        p = scripts_dir / name
        if p.exists():
            print("Rodando:", p.name)
            exec_sql_file(cur2, p)
        else:
            print("Ignorando (não encontrado):", p.name)

    cur2.close()
    conn2.close()

    # 7) Salvar server_info.json para os clientes
    server_ip = detect_server_ip()
    out_dir = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "Opera"
    out_dir.mkdir(parents=True, exist_ok=True)
    info = {
        "host": server_ip,
        "port": port,
        "dbname": dbname,
        "user": app_user,
        "password": app_pass,
        "schema": schema,
    }
    (out_dir / "server_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print("OK. server_info.json salvo em:", out_dir / "server_info.json")
    print("IP do servidor para os clientes:", server_ip)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
