import json
import os
import socket
import sys
from pathlib import Path
from typing import Optional

def detect_scripts_dir() -> Optional[Path]:
    """Descobre a pasta de scripts SQL em ambiente dev/instalador/executável."""
    bases = [
        Path(__file__).resolve().parent,
        Path(sys.executable).resolve().parent,
        Path.cwd().resolve(),
    ]

    candidates = []
    for base in bases:
        candidates.extend([
            base / "scripts",
            base / "data" / "INSTAL_BANCO_APP" / "scripts",
            base.parent / "data" / "INSTAL_BANCO_APP" / "scripts",
        ])

    # dedup mantendo ordem
    seen = set()
    ordered = []
    for c in candidates:
        k = str(c)
        if k not in seen:
            seen.add(k)
            ordered.append(c)

    for cand in ordered:
        if cand.exists() and cand.is_dir():
            return cand
    return None

def detect_server_ip() -> str:
    # pega IP “principal” do Windows (sem 127.*)
    hostname = socket.gethostname()
    ips = socket.gethostbyname_ex(hostname)[2]
    ips = [ip for ip in ips if not ip.startswith("127.")]
    if ips:
        return ips[0]

    # fallback mais resiliente para ambientes com DNS local ruim
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

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
        host=host, port=int(port), dbname=dbname, user=user, password=password,
        connect_timeout=5
    )

def exec_sql_file(cur, sql_path: Path):
    sql = sql_path.read_text(encoding="utf-8", errors="replace")
    cur.execute(sql)

def main():
    # --- PARAMETROS PADRAO (ajuste pro seu produto) ---
    host = "localhost"
    port = 5432
    superuser = "postgres"
    superpass = os.environ.get("OPERA_PG_SUPERPASS", "admin")  # coloque via instalador/variável
    app_user = "opera"
    app_pass = os.environ.get("OPERA_PG_APP_PASS", "opera123")  # defina senha padrão e force trocar depois
    dbname = "BANCO_OPERA"
    schema = "opera"

    scripts_dir = detect_scripts_dir()
    # ordem típica: criar banco, schema, tabelas (ajuste se seus nomes forem outros)
    script_order = [
        "1_CRIAR_BANCO.sql",
        "2_CRIAR_SCHEMA.sql",
        "3_CRIAR_TABELAS.sql",
    ]

    ensure_psycopg2()

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
        # não vamos destruir nada automaticamente aqui.

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

    # permissões básicas
    cur2.execute(f"GRANT ALL ON SCHEMA {schema} TO {app_user};")
    cur2.execute(f"ALTER ROLE {app_user} SET search_path TO {schema};")

    # 6) Rodar seus scripts SQL (se existirem)
    if scripts_dir is None:
        print("ATENCAO: pasta de scripts SQL não encontrada. Pulando execução de arquivos .sql")
    else:
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
    out_dirs = [
        Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "Opera",
        Path(__file__).resolve().parent,
    ]
    info = {
        "host": server_ip,
        "port": port,
        "dbname": dbname,
        "user": app_user,
        "password": app_pass,
        "schema": schema,
    }
    info_payload = json.dumps(info, indent=2, ensure_ascii=False)
    for out_dir in out_dirs:
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / "server_info.json"
        target.write_text(info_payload, encoding="utf-8")
        print("OK. server_info.json salvo em:", target)

    print("IP do servidor para os clientes:", server_ip)

if __name__ == "__main__":
    raise SystemExit(main())
