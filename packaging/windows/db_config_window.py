#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Janela de configuração do banco de dados - VERSÃO CORRIGIDA
"""
import sys
import os
import json
import socket
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

try:
    from PIL import Image, ImageTk

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = ImageTk = None


class BancoConfigWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Configuração do Banco de Dados - Sistema Opera")
        self.root.resizable(False, False)

        # Configuração de cores
        self.bg = "#0B1320"
        self.panel = "#0E1A2E"
        self.fg = "#EAF2FF"
        self.muted = "#9FB3C8"

        self.root.configure(bg=self.bg)

        # Centralizar janela
        self.center_window(850, 580)

        # Variáveis
        self.modo = tk.StringVar(value="local")
        self.host = tk.StringVar(value="localhost")
        self.porta = tk.StringVar(value="5432")
        self.dbname = tk.StringVar(value="BANCO_OPERA")
        self.usuario = tk.StringVar(value="postgres")
        self.senha = tk.StringVar(value="")
        self.schema = tk.StringVar(value="opera")
        self.status = tk.StringVar(value="Configure a conexão com o banco de dados")
        self.validado = False

        # Configurar UI
        self.setup_ui()

        # Bind para quando a janela fechar
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def center_window(self, width, height):
        """Centraliza a janela na tela"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self):
        """Configura a interface do usuário"""
        # Frame principal
        main_frame = tk.Frame(self.root, bg=self.panel, bd=2, relief=tk.RIDGE)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Título
        title_frame = tk.Frame(main_frame, bg=self.panel)
        title_frame.pack(fill=tk.X, pady=(10, 5))

        tk.Label(
            title_frame,
            text="Configuração do Banco de Dados",
            font=("Arial", 16, "bold"),
            fg="#1CC8FF",
            bg=self.panel
        ).pack()

        tk.Label(
            title_frame,
            text="Configure a conexão com o PostgreSQL",
            font=("Arial", 10),
            fg=self.muted,
            bg=self.panel
        ).pack(pady=(0, 10))

        # Frame do formulário
        form_frame = tk.Frame(main_frame, bg=self.panel)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Configurar grid (2 colunas)
        for i in range(2):
            form_frame.columnconfigure(i, weight=1)

        # Tipo de banco (ocupa 2 colunas)
        tipo_frame = tk.Frame(form_frame, bg=self.panel)
        tipo_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        tk.Label(
            tipo_frame,
            text="Tipo de banco:",
            font=("Arial", 10, "bold"),
            fg=self.fg,
            bg=self.panel
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Radiobutton(
            tipo_frame,
            text="Local",
            variable=self.modo,
            value="local",
            command=self.set_modo_local,
            fg=self.fg,
            bg=self.panel,
            selectcolor=self.panel,
            activebackground=self.panel
        ).pack(side=tk.LEFT)

        tk.Radiobutton(
            tipo_frame,
            text="Rede",
            variable=self.modo,
            value="rede",
            fg=self.fg,
            bg=self.panel,
            selectcolor=self.panel,
            activebackground=self.panel
        ).pack(side=tk.LEFT, padx=(15, 0))

        # Campos do formulário
        row = 1
        self.create_field(form_frame, row, 0, "Host/IP:", self.host)
        self.create_field(form_frame, row, 1, "Porta:", self.porta)

        row = 2
        self.create_field(form_frame, row, 0, "Banco:", self.dbname)
        self.create_field(form_frame, row, 1, "Schema:", self.schema)

        row = 3
        self.create_field(form_frame, row, 0, "Usuário:", self.usuario)

        # Campo senha especial
        tk.Label(
            form_frame,
            text="Senha:",
            fg=self.fg,
            bg=self.panel,
            font=("Arial", 10)
        ).grid(row=4, column=0, sticky="w", padx=5, pady=(5, 2))

        senha_entry = tk.Entry(
            form_frame,
            textvariable=self.senha,
            show="•",
            bg="#1A2332",
            fg="#F5F8FF",
            insertbackground="#F5F8FF",
            relief="flat",
            font=("Arial", 11),
            width=20
        )
        senha_entry.grid(row=5, column=0, sticky="ew", padx=5, pady=(0, 10), ipady=5)

        # Checkbox mostrar senha
        self.mostrar_senha = tk.BooleanVar(value=False)
        chk_senha = tk.Checkbutton(
            form_frame,
            text="Mostrar senha",
            variable=self.mostrar_senha,
            command=lambda: self.toggle_senha(senha_entry),
            fg=self.muted,
            bg=self.panel,
            selectcolor=self.panel,
            activebackground=self.panel
        )
        chk_senha.grid(row=5, column=1, sticky="w", padx=5, pady=(0, 10))

        # Status
        status_frame = tk.Frame(main_frame, bg=self.panel)
        status_frame.pack(fill=tk.X, padx=15, pady=(5, 10))

        status_label = tk.Label(
            status_frame,
            textvariable=self.status,
            fg="#B8CCE0",
            bg=self.panel,
            font=("Arial", 9)
        )
        status_label.pack(side=tk.LEFT)

        # Botões
        button_frame = tk.Frame(main_frame, bg=self.panel)
        button_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        btn_detectar = tk.Button(
            button_frame,
            text="Detectar porta",
            command=self.detectar_porta,
            bg="#2A3A4A",
            fg="white",
            relief=tk.FLAT,
            padx=10,
            pady=5
        )
        btn_detectar.pack(side=tk.LEFT, padx=(0, 10))

        btn_testar = tk.Button(
            button_frame,
            text="Testar conexão",
            command=self.testar_conexao,
            bg="#2A3A4A",
            fg="white",
            relief=tk.FLAT,
            padx=10,
            pady=5
        )
        btn_testar.pack(side=tk.LEFT)

        btn_salvar = tk.Button(
            button_frame,
            text="Salvar e continuar",
            command=self.salvar,
            bg="#1CC8FF",
            fg="black",
            relief=tk.FLAT,
            padx=15,
            pady=5,
            font=("Arial", 10, "bold")
        )
        btn_salvar.pack(side=tk.RIGHT)

    def create_field(self, parent, row, col, label_text, variable):
        """Cria um campo de entrada com label"""
        # Label
        tk.Label(
            parent,
            text=label_text,
            fg=self.fg,
            bg=self.panel,
            font=("Arial", 10)
        ).grid(row=row * 2, column=col, sticky="w", padx=5, pady=(5, 2))

        # Entry
        entry = tk.Entry(
            parent,
            textvariable=variable,
            bg="#1A2332",
            fg="#F5F8FF",
            insertbackground="#F5F8FF",
            relief="flat",
            font=("Arial", 11),
            width=20
        )
        entry.grid(row=row * 2 + 1, column=col, sticky="ew", padx=5, pady=(0, 15), ipady=5)

        # Bind para invalidar quando mudar
        def on_change(*args):
            self.validado = False
            self.status.set("Clique em Testar conexão para validar")

        variable.trace_add("write", on_change)

        return entry

    def set_modo_local(self):
        """Define modo local"""
        if self.modo.get() == "local":
            self.host.set("localhost")

    def toggle_senha(self, entry):
        """Mostra/oculta senha"""
        if self.mostrar_senha.get():
            entry.configure(show="")
        else:
            entry.configure(show="•")

    def porta_aberta(self, host, porta, timeout=2):
        """Verifica se uma porta está aberta"""
        try:
            with socket.create_connection((host, int(porta)), timeout=timeout):
                return True
        except:
            return False

    def detectar_porta(self):
        """Detecta porta PostgreSQL automaticamente"""
        host = self.host.get().strip()
        if not host:
            messagebox.showerror("Erro", "Informe o Host/IP para detectar a porta.")
            return

        portas_teste = [5432, 5433, 5434]
        for porta in portas_teste:
            if self.porta_aberta(host, porta):
                self.porta.set(str(porta))
                self.status.set(f"Porta detectada: {porta}")
                messagebox.showinfo("Porta detectada", f"Porta {porta} está aberta")
                return

        messagebox.showwarning("Aviso", "Nenhuma porta PostgreSQL detectada")

    def testar_conexao(self):
        """Testa a conexão com o banco"""
        host = self.host.get().strip()
        porta_str = self.porta.get().strip()

        if not host or not porta_str:
            messagebox.showerror("Erro", "Preencha Host/IP e Porta.")
            return

        try:
            porta = int(porta_str)
        except ValueError:
            messagebox.showerror("Erro", "Porta deve ser um número.")
            return

        if self.porta_aberta(host, porta):
            self.validado = True
            self.status.set("✅ Conexão OK! Pode salvar.")
            messagebox.showinfo("Sucesso", "Conexão estabelecida!")
        else:
            self.validado = False
            self.status.set("❌ Falha na conexão")
            messagebox.showerror("Erro", "Não foi possível conectar")

    def salvar(self):
        """Salva a configuração"""
        host = self.host.get().strip()
        porta_str = self.porta.get().strip()
        db = self.dbname.get().strip()
        usuario = self.usuario.get().strip()
        senha = self.senha.get()
        schema = self.schema.get().strip() or "opera"

        if not all([host, porta_str, db, usuario]):
            messagebox.showerror("Erro", "Preencha todos os campos")
            return

        try:
            porta = int(porta_str)
        except ValueError:
            messagebox.showerror("Erro", "Porta deve ser número")
            return

        # Configuração
        config = {
            "host": host,
            "port": porta,
            "dbname": db,
            "user": usuario,
            "password": senha,
            "schema": schema,
            "mode": self.modo.get()
        }

        # Salvar no TEMP
        temp_dir = os.environ.get('TEMP', 'C:\\Temp')
        config_file = os.path.join(temp_dir, 'sistema_opera_config.json')

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        # Salvar no APPDATA (local onde o BANCO_DE_DADOS_PG procura)
        appdata = os.path.join(os.environ.get('APPDATA', ''), 'SistemaOpera')
        if appdata:
            os.makedirs(appdata, exist_ok=True)
            config_appdata = os.path.join(appdata, 'config.json')
            with open(config_appdata, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            print(f"Configuração salva em: {config_appdata}")

        messagebox.showinfo("Sucesso", "Configuração salva!")
        self.root.quit()
        self.root.destroy()

    def on_close(self):
        """Fechar janela"""
        if messagebox.askyesno("Confirmar", "Deseja cancelar?"):
            self.root.quit()
            self.root.destroy()

    def run(self):
        """Executar"""
        self.root.mainloop()


def main():
    """Função principal"""
    window = BancoConfigWindow()
    window.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())