import json
import os
import socket
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


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


class SetupServidorUI:
    def __init__(self, defaults: dict):
        self.defaults = defaults
        self.resultado = None

        self.root = tk.Tk()
        self.root.title("Configuração do Servidor PostgreSQL")
        self.root.geometry("760x560")
        self.root.minsize(700, 500)
        self.root.configure(bg="#1f1f1f")
        self.root.protocol("WM_DELETE_WINDOW", self._cancelar)

        self._centralizar_janela()
        self._montar_interface()

    def _centralizar_janela(self):
        self.root.update_idletasks()
        largura = self.root.winfo_width()
        altura = self.root.winfo_height()
        x = max((self.root.winfo_screenwidth() - largura) // 2, 0)
        y = max((self.root.winfo_screenheight() - altura) // 2, 0)
        self.root.geometry(f"{largura}x{altura}+{x}+{y}")

    def _montar_interface(self):
        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except Exception:
            pass

        frame = ttk.Frame(self.root, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Assistente de Configuração do Banco",
            font=("Segoe UI", 15, "bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))

        ttk.Label(
            frame,
            text="Informe os dados, teste a conexão, busque os bancos disponíveis e clique em Executar Setup.",
            wraplength=700,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 12))

        self.var_host = tk.StringVar(value=str(self.defaults["host"]))
        self.var_port = tk.StringVar(value=str(self.defaults["port"]))
        self.var_superuser = tk.StringVar(value=str(self.defaults["superuser"]))
        self.var_superpass = tk.StringVar(value=str(self.defaults["superpass"]))
        self.var_app_user = tk.StringVar(value=str(self.defaults["app_user"]))
        self.var_app_pass = tk.StringVar(value=str(self.defaults["app_pass"]))
        self.var_dbname = tk.StringVar(value=str(self.defaults["dbname"]))
        self.var_schema = tk.StringVar(value=str(self.defaults["schema"]))

        campos = [
            ("Host", self.var_host),
            ("Porta", self.var_port),
            ("Superusuário", self.var_superuser),
            ("Senha do superusuário", self.var_superpass),
            ("Usuário da aplicação", self.var_app_user),
            ("Senha da aplicação", self.var_app_pass),
            ("Schema", self.var_schema),
        ]

        row = 2
        for idx, (label, var) in enumerate(campos):
            col = 0 if idx % 2 == 0 else 2
            if idx % 2 == 0 and idx != 0:
                row += 1
            ttk.Label(frame, text=label).grid(row=row, column=col, sticky="w", pady=(3, 0))
            show = "*" if "Senha" in label else ""
            ttk.Entry(frame, textvariable=var, show=show).grid(
                row=row + 1, column=col, columnspan=2 if col == 0 else 2, sticky="ew", padx=(0, 8), pady=(0, 4)
            )

        row += 2
        ttk.Label(frame, text="Banco de dados").grid(row=row, column=0, sticky="w", pady=(6, 0))
        self.combo_db = ttk.Combobox(frame, textvariable=self.var_dbname, values=[self.var_dbname.get()])
        self.combo_db.grid(row=row + 1, column=0, columnspan=2, sticky="ew", padx=(0, 8))

        ttk.Button(frame, text="🔎 Buscar bancos", command=self._buscar_bancos).grid(
            row=row + 1, column=2, sticky="ew", padx=(0, 6)
        )
        ttk.Button(frame, text="🧪 Testar conexão", command=self._testar_conexao).grid(
            row=row + 1, column=3, sticky="ew"
        )

        row += 2
        ttk.Label(frame, text="Log").grid(row=row, column=0, sticky="w", pady=(10, 4))
        self.log_text = tk.Text(frame, height=12, wrap="word")
        self.log_text.grid(row=row + 1, column=0, columnspan=4, sticky="nsew")

        btns = ttk.Frame(frame)
        btns.grid(row=row + 2, column=0, columnspan=4, sticky="e", pady=(10, 0))
        ttk.Button(btns, text="Cancelar", command=self._cancelar).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text="Executar Setup", command=self._confirmar).pack(side="right")

        for i in range(4):
            frame.columnconfigure(i, weight=1)
        frame.rowconfigure(row + 1, weight=1)

        self._log("Interface pronta. Informe os dados para continuar.")

    def _log(self, msg: str):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.root.update_idletasks()

    def _ler_parametros(self):
        try:
            porta = int((self.var_port.get() or "").strip())
        except Exception:
            messagebox.showerror("Erro", "Porta inválida.", parent=self.root)
            return None

        return {
            "host": (self.var_host.get() or "localhost").strip(),
            "port": porta,
            "superuser": (self.var_superuser.get() or "postgres").strip(),
            "superpass": self.var_superpass.get() or "",
            "app_user": (self.var_app_user.get() or "opera").strip(),
            "app_pass": self.var_app_pass.get() or "",
            "dbname": (self.var_dbname.get() or "opera").strip(),
            "schema": (self.var_schema.get() or "opera").strip(),
        }

    def _testar_conexao(self):
        params = self._ler_parametros()
        if not params:
            return

        try:
            ensure_psycopg2()
            conn = connect_psycopg2(
                dbname="postgres",
                user=params["superuser"],
                password=params["superpass"],
                host=params["host"],
                port=params["port"],
            )
            conn.close()
            self._log("✅ Conexão com PostgreSQL OK.")
            messagebox.showinfo("Conexão", "Conexão realizada com sucesso!", parent=self.root)
        except Exception as exc:
            self._log(f"❌ Falha ao conectar: {exc}")
            messagebox.showerror("Conexão", f"Falha na conexão:\n{exc}", parent=self.root)

    def _buscar_bancos(self):
        params = self._ler_parametros()
        if not params:
            return

        try:
            ensure_psycopg2()
            conn = connect_psycopg2(
                dbname="postgres",
                user=params["superuser"],
                password=params["superpass"],
                host=params["host"],
                port=params["port"],
            )
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;"
                )
                bancos = [row[0] for row in cur.fetchall()]
            conn.close()

            if bancos:
                self.combo_db["values"] = bancos
                if params["dbname"] not in bancos:
                    self.var_dbname.set(bancos[0])
                self._log(f"✅ Bancos encontrados: {', '.join(bancos)}")
            else:
                self._log("⚠️ Nenhum banco de dados encontrado.")
        except Exception as exc:
            self._log(f"❌ Erro ao buscar bancos: {exc}")
            messagebox.showerror("Buscar bancos", f"Não foi possível listar bancos:\n{exc}", parent=self.root)

    def _confirmar(self):
        params = self._ler_parametros()
        if not params:
            return
        self.resultado = params
        self.root.destroy()

    def _cancelar(self):
        self.resultado = None
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        return self.resultado


def _coletar_parametros_setup(defaults: dict):
    """Abre interface única completa para configuração e testes."""
    ui = SetupServidorUI(defaults)
    return ui.run()


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
