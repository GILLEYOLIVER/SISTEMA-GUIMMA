import json
import os
import socket
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import simpledialog, messagebox


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



def _coletar_parametros_setup(defaults: dict) -> dict | None:
    """Abre interface para coletar parâmetros antes de conectar ao PostgreSQL."""
    root = tk.Tk()
    root.withdraw()
    try:
        root.update_idletasks()
        largura = 420
        altura = 180
        x = max((root.winfo_screenwidth() - largura) // 2, 0)
        y = max((root.winfo_screenheight() - altura) // 2, 0)
        root.geometry(f"{largura}x{altura}+{x}+{y}")
    except Exception:
        pass

    host = simpledialog.askstring("Configuração do Servidor", "Host do PostgreSQL:", initialvalue=str(defaults["host"]), parent=root)
    if host is None:
        root.destroy()
        return None

    porta_txt = simpledialog.askstring("Configuração do Servidor", "Porta do PostgreSQL:", initialvalue=str(defaults["port"]), parent=root)
    if porta_txt is None:
        root.destroy()
        return None

    superuser = simpledialog.askstring("Configuração do Servidor", "Usuário administrador (superuser):", initialvalue=str(defaults["superuser"]), parent=root)
    if superuser is None:
        root.destroy()
        return None

    superpass = simpledialog.askstring("Configuração do Servidor", "Senha do usuário administrador:", initialvalue=str(defaults["superpass"]), show="*", parent=root)
    if superpass is None:
        root.destroy()
        return None

    app_user = simpledialog.askstring("Configuração do Servidor", "Usuário da aplicação:", initialvalue=str(defaults["app_user"]), parent=root)
    if app_user is None:
        root.destroy()
        return None

    app_pass = simpledialog.askstring("Configuração do Servidor", "Senha do usuário da aplicação:", initialvalue=str(defaults["app_pass"]), show="*", parent=root)
    if app_pass is None:
        root.destroy()
        return None

    dbname = simpledialog.askstring("Configuração do Servidor", "Nome do banco:", initialvalue=str(defaults["dbname"]), parent=root)
    if dbname is None:
        root.destroy()
        return None

    schema = simpledialog.askstring("Configuração do Servidor", "Schema padrão:", initialvalue=str(defaults["schema"]), parent=root)
    if schema is None:
        root.destroy()
        return None

    try:
        port = int(porta_txt)
    except Exception:
        messagebox.showerror("Erro", f"Porta inválida: {porta_txt}", parent=root)
        root.destroy()
        return None

    root.destroy()
    return {
        "host": host.strip() or defaults["host"],
        "port": port,
        "superuser": superuser.strip() or defaults["superuser"],
        "superpass": superpass,
        "app_user": app_user.strip() or defaults["app_user"],
        "app_pass": app_pass,
        "dbname": dbname.strip() or defaults["dbname"],
        "schema": schema.strip() or defaults["schema"],
    }

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
    defaults = {
        "host": "localhost",
        "port": 5432,
        "superuser": "postgres",
        "superpass": os.environ.get("OPERA_PG_SUPERPASS", ""),
        "app_user": "opera",
        "app_pass": os.environ.get("OPERA_PG_APP_PASS", "opera123"),
        "dbname": "opera",
        "schema": "opera",
    }

    parametros = _coletar_parametros_setup(defaults)
    if not parametros:
        print("Configuração cancelada pelo usuário.")
        return 1

    host = parametros["host"]
    port = parametros["port"]
    superuser = parametros["superuser"]
    superpass = parametros["superpass"]
    app_user = parametros["app_user"]
    app_pass = parametros["app_pass"]
    dbname = parametros["dbname"]
    schema = parametros["schema"]

    scripts_dir = Path(__file__).parent / "scripts"
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

if __name__ == "__main__":
    raise SystemExit(main())