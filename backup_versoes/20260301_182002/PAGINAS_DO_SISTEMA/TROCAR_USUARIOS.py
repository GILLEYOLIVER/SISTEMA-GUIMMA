# -*- coding: utf-8 -*-
"""Janela de troca de usuário desacoplada do menu principal."""

import customtkinter as ctk
from tkinter import messagebox


def abrir_janela_trocar_usuario(self):
    """Abre tela completa de login para trocar usuário."""
    try:
        # =========================
        # JANELA MODAL DE LOGIN
        # =========================
        login_window = ctk.CTkToplevel(self)
        login_window.title("OPERA - Trocar Usuário")
        login_window.transient(self)

        # Dimensões fixas
        largura_janela = 480
        altura_janela = 680

        # Garantir que a janela exista antes de centralizar
        login_window.update_idletasks()

        screen_largura = login_window.winfo_screenwidth()
        screen_altura = login_window.winfo_screenheight()

        x = (screen_largura - largura_janela) // 2
        y = (screen_altura - altura_janela) // 2

        login_window.geometry(f"{largura_janela}x{altura_janela}+{x}+{y}")
        login_window.resizable(False, False)

        # =========================
        # MOVIMENTAÇÃO DA JANELA
        # =========================
        def start_move(event):
            login_window.x = event.x_root
            login_window.y = event.y_root

        def stop_move(event):
            login_window.x = None
            login_window.y = None

        def do_move(event):
            if hasattr(login_window, "x") and login_window.x is not None:
                deltax = event.x_root - login_window.x
                deltay = event.y_root - login_window.y
                nx = login_window.winfo_x() + deltax
                ny = login_window.winfo_y() + deltay
                login_window.geometry(f"+{nx}+{ny}")
                login_window.x = event.x_root
                login_window.y = event.y_root

        # =========================
        # FECHAMENTO SEGURO
        # =========================
        def on_login_close():
            try:
                login_window.grab_release()
            except Exception:
                pass
            login_window.destroy()

        login_window.protocol("WM_DELETE_WINDOW", on_login_close)

        # =========================
        # CORES DO TEMA ATUAL (DO MENU)
        # =========================
        cor_fundo = getattr(self, "cor_fundo", "#f8f9fa")
        cor_primaria = getattr(self, "cor_primaria", "#ffffff")
        cor_secundaria = getattr(self, "cor_secundaria", "#e9ecef")
        cor_terciaria = getattr(self, "cor_terciaria", "#6c757d")
        cor_texto = getattr(self, "cor_texto", "#212529")
        cor_borda = getattr(self, "cor_borda", "#ced4da")
        cor_botao_primario = getattr(self, "cor_destaque", "#007bff")
        cor_botao_secundario = cor_terciaria
        cor_texto_placeholder = getattr(self, "cor_texto_secundario", "#888888")
        cor_alerta = getattr(self, "cor_alerta", "#ff0000")

        # =========================
        # HELPER DE HOVER (INVERTER CORES)
        # =========================
        def aplicar_hover_inverter(botao, cor_bg_normal, cor_bg_hover, cor_txt_normal, cor_txt_hover):
            """Configura o botão para inverter cores de fundo/texto no hover."""

            def on_enter(_event):
                botao.configure(fg_color=cor_bg_hover, text_color=cor_txt_hover)

            def on_leave(_event):
                botao.configure(fg_color=cor_bg_normal, text_color=cor_txt_normal)

            botao.configure(hover_color=cor_bg_normal)
            botao.bind("<Enter>", on_enter)
            botao.bind("<Leave>", on_leave)

        # =========================
        # LAYOUT PRINCIPAL
        # =========================
        login_window.configure(fg_color=cor_fundo)

        container = ctk.CTkFrame(
            login_window,
            fg_color=cor_primaria,
            corner_radius=16,
            border_color=cor_borda,
            border_width=2,
        )
        container.pack(fill="both", expand=True, padx=25, pady=25)

        # ----- TÍTULO (arrastável)
        titulo_frame = ctk.CTkFrame(container, fg_color="transparent")
        titulo_frame.pack(fill="x", padx=25, pady=(25, 15))

        titulo = ctk.CTkLabel(
            titulo_frame,
            text="🔐 TROCAR USUÁRIO",
            font=("Arial", 22, "bold"),
            text_color=cor_texto,
        )
        titulo.pack(pady=10)

        titulo.bind("<ButtonPress-1>", start_move)
        titulo.bind("<ButtonRelease-1>", stop_move)
        titulo.bind("<B1-Motion>", do_move)

        ctk.CTkFrame(
            titulo_frame,
            fg_color=cor_borda,
            height=2,
        ).pack(fill="x", pady=5)

        # ----- FORMULÁRIO
        form_frame = ctk.CTkFrame(container, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=30, pady=20)

        # Campo Usuário
        lbl_usuario = ctk.CTkLabel(
            form_frame,
            text="Usuário:",
            font=("Arial", 14, "bold"),
            text_color=cor_texto,
        )
        lbl_usuario.pack(anchor="w", pady=(10, 5))

        entry_usuario = ctk.CTkEntry(
            form_frame,
            placeholder_text="Digite seu nome de usuário",
            width=300,
            height=45,
            font=("Arial", 14),
            fg_color=cor_secundaria,
            text_color=cor_texto,
            border_width=0,
            placeholder_text_color=cor_texto_placeholder,
            corner_radius=10,
        )
        entry_usuario.pack(fill="x", pady=(0, 20))

        # Campo Senha
        lbl_senha = ctk.CTkLabel(
            form_frame,
            text="Senha:",
            font=("Arial", 14, "bold"),
            text_color=cor_texto,
        )
        lbl_senha.pack(anchor="w", pady=(10, 5))

        entry_senha = ctk.CTkEntry(
            form_frame,
            placeholder_text="Digite sua senha",
            show="•",
            width=300,
            height=45,
            font=("Arial", 14),
            fg_color=cor_secundaria,
            text_color=cor_texto,
            border_width=0,
            placeholder_text_color=cor_texto_placeholder,
            corner_radius=10,
        )
        entry_senha.pack(fill="x", pady=(0, 15))

        # ----- Mostrar senha
        var_mostrar_senha = ctk.BooleanVar()

        def toggle_senha():
            entry_senha.configure(show="" if var_mostrar_senha.get() else "•")

        chk_mostrar = ctk.CTkCheckBox(
            form_frame,
            text="Mostrar senha",
            variable=var_mostrar_senha,
            command=toggle_senha,
            font=("Arial", 13),
            text_color=cor_texto,
            fg_color=cor_botao_primario,
            hover_color=cor_botao_primario,
            border_width=0,
        )
        chk_mostrar.pack(anchor="w", pady=(0, 25))

        # =========================
        # BOTÕES DE AJUDA
        # =========================
        help_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        help_frame.pack(fill="x", pady=(0, 25))

        def listar_usuarios():
            """Mostra lista de usuários cadastrados e permite seleção."""
            try:
                from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import fetch_all

                usuarios = fetch_all(
                    "SELECT usuario, hierarquia "
                    "FROM opera.usuarios "
                    "WHERE ativo = true "
                    "ORDER BY usuario"
                )

                if not usuarios:
                    messagebox.showinfo(
                        "Usuários",
                        "Nenhum usuário encontrado.",
                        parent=login_window,
                    )
                    return

                # Janela de listagem
                user_win = ctk.CTkToplevel(login_window)
                user_win.title("Usuários Cadastrados")
                user_win.transient(login_window)

                # Tamanho
                user_largura = 520
                user_altura = 420

                # Centralizar em relação à janela de login
                login_window.update_idletasks()
                parent_x = login_window.winfo_rootx()
                parent_y = login_window.winfo_rooty()
                parent_w = login_window.winfo_width()
                parent_h = login_window.winfo_height()

                ux = parent_x + (parent_w - user_largura) // 2
                uy = parent_y + (parent_h - user_altura) // 2

                user_win.geometry(f"{user_largura}x{user_altura}+{ux}+{uy}")
                user_win.resizable(False, False)

                user_win.configure(fg_color=cor_fundo)
                user_win.grab_set()
                user_win.focus_force()

                user_container = ctk.CTkFrame(
                    user_win, fg_color=cor_primaria, corner_radius=12
                )
                user_container.pack(fill="both", expand=True, padx=15, pady=15)

                ctk.CTkLabel(
                    user_container,
                    text="👥 Usuários Cadastrados",
                    font=("Arial", 16, "bold"),
                    text_color=cor_texto,
                ).pack(pady=(10, 5))

                # Frame da lista
                lista_frame = ctk.CTkFrame(
                    user_container, fg_color=cor_secundaria, corner_radius=8
                )
                lista_frame.pack(fill="both", expand=True, padx=10, pady=10)

                # Listbox para permitir duplo clique
                listbox = tk.Listbox(
                    lista_frame,
                    font=("Arial", 12),
                    activestyle="none",
                    borderwidth=0,
                    highlightthickness=0,
                )
                listbox.pack(fill="both", expand=True, padx=8, pady=8)

                for user in usuarios:
                    texto = f"• {user['usuario']} ({user['hierarquia']})"
                    listbox.insert("end", texto)

                # Função de seleção (botão + duplo clique)
                def selecionar_usuario(_event=None):
                    selecao = listbox.curselection()
                    if not selecao:
                        messagebox.showinfo(
                            "Selecionar",
                            "Selecione um usuário na lista.",
                            parent=user_win,
                        )
                        return
                    linha = listbox.get(selecao[0])
                    usuario_nome = linha.replace("•", "", 1).strip()
                    if " (" in usuario_nome:
                        usuario_nome = usuario_nome.split(" (", 1)[0].strip()

                    entry_usuario.delete(0, "end")
                    entry_usuario.insert(0, usuario_nome)

                    try:
                        user_win.grab_release()
                    except Exception:
                        pass
                    user_win.destroy()

                listbox.bind("<Double-Button-1>", selecionar_usuario)

                # Botões Selecionar / Fechar
                botoes_frame = ctk.CTkFrame(
                    user_container, fg_color="transparent"
                )
                botoes_frame.pack(fill="x", pady=(8, 5))

                btn_sel = ctk.CTkButton(
                    botoes_frame,
                    text="✅ Selecionar",
                    command=selecionar_usuario,
                    width=140,
                    height=36,
                    font=("Arial", 12),
                    fg_color=cor_botao_primario,
                    hover_color=cor_botao_primario,
                    corner_radius=8,
                    text_color="white",
                )
                btn_sel.pack(side="left", padx=(0, 10))
                aplicar_hover_inverter(
                    btn_sel,
                    cor_botao_primario,
                    cor_primaria,
                    "white",
                    cor_botao_primario,
                )

                btn_fechar = ctk.CTkButton(
                    botoes_frame,
                    text="Fechar",
                    command=lambda: (user_win.grab_release(), user_win.destroy()),
                    width=120,
                    height=36,
                    font=("Arial", 12),
                    fg_color=cor_botao_secundario,
                    hover_color=cor_botao_secundario,
                    corner_radius=8,
                    text_color=cor_texto,
                )
                btn_fechar.pack(side="left")
                aplicar_hover_inverter(
                    btn_fechar,
                    cor_botao_secundario,
                    cor_primaria,
                    cor_texto,
                    cor_botao_secundario,
                )

            except Exception as e:
                messagebox.showerror(
                    "Erro",
                    f"Erro ao carregar usuários:\n{e}",
                    parent=login_window,
                )

        def mostrar_dica_senha():
            """Mostra dica de senha do usuário."""
            usuario = entry_usuario.get().strip()
            if not usuario:
                messagebox.showinfo(
                    "Dica", "Digite o usuário primeiro.", parent=login_window
                )
                return

            try:
                from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import fetch_one

                resultado = fetch_one(
                    "SELECT dica_senha "
                    "FROM opera.usuarios "
                    "WHERE usuario = %s",
                    (usuario,),
                )

                if resultado and resultado.get("dica_senha"):
                    messagebox.showinfo(
                        "Dica de Senha",
                        f"Usuário: {usuario}\n\nDica: {resultado['dica_senha']}",
                        parent=login_window,
                    )
                else:
                    messagebox.showinfo(
                        "Dica",
                        "Nenhuma dica cadastrada para este usuário.",
                        parent=login_window,
                    )

            except Exception as e:
                messagebox.showerror(
                    "Erro", f"Erro ao buscar dica:\n{e}", parent=login_window
                )

        # Linha com os 2 botões de ajuda
        help_inner_frame = ctk.CTkFrame(help_frame, fg_color="transparent")
        help_inner_frame.pack(fill="x")

        btn_listar = ctk.CTkButton(
            help_inner_frame,
            text="👥 Listar Usuários",
            command=listar_usuarios,
            width=160,
            height=36,
            font=("Arial", 12, "bold"),
            fg_color=cor_secundaria,
            hover_color=cor_secundaria,
            corner_radius=8,
            text_color=cor_botao_primario,
        )
        btn_listar.pack(side="left", padx=(0, 8))
        aplicar_hover_inverter(
            btn_listar,
            cor_secundaria,  # normal: cinza claro
            cor_primaria,  # hover: branco
            cor_botao_primario,
            cor_botao_primario,
        )

        btn_dica = ctk.CTkButton(
            help_inner_frame,
            text="🔍 Dica de Senha",
            command=mostrar_dica_senha,
            width=160,
            height=36,
            font=("Arial", 12, "bold"),
            fg_color=cor_secundaria,
            hover_color=cor_secundaria,
            corner_radius=8,
            text_color=cor_botao_primario,
        )
        btn_dica.pack(side="left", padx=8)
        aplicar_hover_inverter(
            btn_dica,
            cor_secundaria,
            cor_primaria,
            cor_botao_primario,
            cor_botao_primario,
        )

        # =========================
        # FUNÇÃO PRINCIPAL DE LOGIN
        # =========================
        def fazer_login():
            usuario = entry_usuario.get().strip()
            senha = entry_senha.get().strip()

            if not usuario or not senha:
                messagebox.showwarning(
                    "Atenção",
                    "Informe usuário e senha.",
                    parent=login_window,
                )
                return

            try:
                import bcrypt
                import hashlib
                from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import fetch_one

                sql = """
                    SELECT 
                        u.id, 
                        u.senha_hash, 
                        u.ativo, 
                        u.hierarquia,
                        COALESCE(up.tema_nome, u.tema_preferido, 'CLÁSSICO CLARO') AS tema_preferido
                    FROM opera.usuarios u
                    LEFT JOIN opera.usuario_preferencias up ON u.id = up.usuario_id
                    WHERE u.usuario = %s
                """
                usuario_data = fetch_one(sql, (usuario,))

                if not usuario_data:
                    messagebox.showerror(
                        "Erro", "Usuário não encontrado.", parent=login_window
                    )
                    return

                if not usuario_data.get("ativo", True):
                    messagebox.showerror(
                        "Erro", "Usuário inativo.", parent=login_window
                    )
                    return

                senha_hash = usuario_data["senha_hash"] or ""
                senha_correta = False

                # Verificar BCRYPT (pgcrypto)
                try:
                    if senha_hash.startswith("$2"):
                        if bcrypt.checkpw(senha.encode(), senha_hash.encode()):
                            senha_correta = True
                except Exception:
                    pass

                # SHA256 antigo
                if not senha_correta:

                    def hash_salt(s):
                        return hashlib.sha256(
                            b"sistema_profissional_v2.2" + s.encode()
                        ).hexdigest()

                    def hash_simples(s):
                        return hashlib.sha256(s.encode()).hexdigest()

                    if (
                            senha_hash == hash_salt(senha)
                            or senha_hash == hash_simples(senha)
                    ):
                        senha_correta = True

                # Texto plano (compatibilidade extrema)
                if not senha_correta and senha_hash == senha:
                    senha_correta = True

                if not senha_correta:
                    messagebox.showerror(
                        "Erro", "Senha incorreta.", parent=login_window
                    )
                    return

                # ============== LOGIN OK ==============
                # Fechar janela de troca de usuário
                on_login_close()

                # Atualizar dados do app
                self.usuario_id = usuario_data["id"]
                self.usuario_nome = usuario
                self.usuario_hierarquia = usuario_data["hierarquia"] or "Padrão"
                tema_preferido = (
                        usuario_data.get("tema_preferido") or "CLÁSSICO CLARO"
                )

                # Atualizar UserManager
                self.user_manager.usuario_id = self.usuario_id
                self.user_manager.usuario_nome = self.usuario_nome
                self.user_manager.usuario_hierarquia = self.usuario_hierarquia

                # 🔁 RESTAURAR ESTRUTURA COMPLETA DO MENU
                # (garante que, ao trocar de usuário, a filtragem de permissões
                #  comece sempre do menu cheio, e não de um menu já filtrado)
                try:
                    self.MENU_ESTRUTURA = type(self).MENU_ESTRUTURA
                except Exception:
                    pass

                # Limpar caches completamente
                self.permissoes_usuario = {}
                self.cache_permissoes = {}
                self.menu_cache = {}
                self.current_page = None

                # Recarregar permissões do novo usuário
                self._load_user_permissions()  # aplica _apply_permissions_to_menu internamente

                # Carregar tema completo do usuário
                print(
                    f"🔄 Carregando tema do usuário {self.usuario_nome}: "
                    f"{tema_preferido}"
                )
                tema_nome, palette = self.user_manager.load_user_theme_completo()
                if tema_nome:
                    self.current_theme_name = tema_nome
                    print(f"🎨 Aplicando tema do usuário: {tema_nome}")
                    if palette:
                        self.theme_manager.apply_theme(tema_nome, palette)
                    else:
                        self.theme_manager.apply_theme(tema_nome)
                else:
                    self.current_theme_name = tema_preferido
                    print(
                        f"🎨 Aplicando tema preferido: {tema_preferido}"
                    )
                    self.theme_manager.apply_theme(tema_preferido)

                # Reconstruir menu e interface (já com permissões aplicadas)
                self._build_menu_content()
                self._update_user_display()
                self._add_theme_switch_to_topbar()

                messagebox.showinfo(
                    "Sucesso",
                    f"Usuário alterado para: {usuario}",
                    parent=self,
                )

                # Abre o Dashboard respeitando permissão
                self.open_page("Dashboard")

            except Exception as e:
                messagebox.showerror(
                    "Erro", f"Erro ao efetuar login:\n{e}", parent=login_window
                )

        # =========================
        # BOTÕES PRINCIPAIS
        # =========================
        btn_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))

        btn_entrar = ctk.CTkButton(
            btn_frame,
            text="🎯 ENTRAR NO SISTEMA",
            command=fazer_login,
            width=300,
            height=50,
            font=("Arial", 16, "bold"),
            fg_color=cor_botao_primario,
            hover_color=cor_botao_primario,
            corner_radius=12,
            text_color="white",
        )
        btn_entrar.pack(pady=(0, 12))
        aplicar_hover_inverter(
            btn_entrar,
            cor_botao_primario,
            cor_primaria,
            "white",
            cor_botao_primario,
        )

        btn_cancelar = ctk.CTkButton(
            btn_frame,
            text="❌ CANCELAR",
            command=on_login_close,
            width=300,
            height=40,
            font=("Arial", 14),
            fg_color=cor_botao_secundario,
            hover_color=cor_botao_secundario,
            corner_radius=10,
            text_color=cor_alerta,
        )
        btn_cancelar.pack()
        aplicar_hover_inverter(
            btn_cancelar,
            cor_botao_secundario,
            cor_primaria,
            cor_alerta,
            cor_alerta,
        )

        # Enter → fazer login
        entry_senha.bind("<Return>", lambda e: fazer_login())

        # Exibir janela como modal
        login_window.deiconify()
        login_window.update_idletasks()
        login_window.grab_set()
        login_window.focus_force()
        entry_usuario.focus_set()

        print("✅ Janela de trocar usuário aberta com tema aplicado corretamente")

    except Exception as e:
        print(f"❌ Erro ao abrir janela de trocar usuário: {e}")
        messagebox.showerror(
            "Erro",
            f"Falha ao abrir tela de login:\n{e}",
            parent=self,
        )

