from __future__ import annotations

# -*- coding: utf-8 -*-
"""
SISTEMA DE GESTÃO DE USUÁRIOS – Profissional 2.2
-------------------------------------------------
- UI moderna com CustomTkinter
- Aba PERMISSÕES toda na janela (sem scroll vertical longuíssimo): grupos em grade de colunas
- Linhas separadoras entre ÁREAS/SISTEMAS
- Variáveis Tk com master=self (evita bugs de "can't invoke" quando parent some)
- Integração com PostgreSQL via BANCO_DE_DADOS_PG (get_conn, get_schema, require_ready)
- Fluxos completos: listar/carregar/criar/editar/excluir usuário + permissões + logs
"""

import os
import sys
import csv
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# --- UI ---
import customtkinter as ctk
from TEMAS import get_contraste_texto, is_dark_color, ajustar_hover
from tkinter import ttk
from tkinter import messagebox, ttk

# ============================================================
# Integração com PostgreSQL
# ============================================================
try:
    # Adiciona o diretório atual ao path para importar o módulo
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    # Esperado do seu módulo BANCO_DE_DADOS_PG:
    # - get_conn() -> contexto de conexão psycopg2
    # - get_schema() -> nome do schema (str)
    # - require_ready(essentials: list[str] | None) -> tuple[bool, str]
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready

    POSTGRES_AVAILABLE = True
    print("✅ Módulo PostgreSQL carregado com sucesso!")
except Exception as e:
    print(f"❌ Erro ao importar BANCO_DE_DADOS_PG: {e}")
    POSTGRES_AVAILABLE = False


    def get_conn():
        raise RuntimeError("Módulo PostgreSQL não disponível")


    def get_schema():
        return "opera"


    def require_ready(essentials=None):
        return False, "Módulo PostgreSQL não disponível"


# ============================================================
# Utilidades / Modelo
# ============================================================
@dataclass
class Usuario:
    id: int | None
    usuario: str
    email: str
    hierarquia: str
    ativo: bool
    dica_senha: str = ""
    telefone: str = ""
    departamento: str = ""
    ultimo_login: Optional[str] = None


def _hash_pwd(senha: str) -> str:
    salt = b'sistema_profissional_v2.2'
    return hashlib.sha256(salt + (senha or "").encode("utf-8")).hexdigest()


# ============================================================
# Helpers de Log (opcionalmente escrevem no DB)
# ============================================================
def registrar_log_db(usuario: str, pagina: str, acao: str, detalhe: str):
    if not POSTGRES_AVAILABLE:
        print(f"[LOG] {usuario} | {pagina} | {acao} | {detalhe}")
        return
    try:
        schema = get_schema()
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO {schema}.usuario_logs (data_hora, usuario, acao, pagina, detalhe)
                    VALUES (NOW(), %s, %s, %s, %s)""",
                (usuario or "Sistema", acao or "", pagina or "", detalhe or ""),
            )
            conn.commit()
    except Exception as e:
        print(f"[LOG][ERRO] Falha ao gravar log no DB: {e}")


# ============================================================
# Componentes de UI
# ============================================================
class ModernButton(ctk.CTkButton):
    def __init__(self, master, text, command=None, **kwargs):
        super().__init__(master, text=text, command=command, **kwargs)
        self.configure(
            border_width=1,
            border_color="#3b82f6",
            corner_radius=8,
            fg_color="transparent",
            hover_color="#1e40af",
            text_color="#3b82f6",
            font=ctk.CTkFont(weight="bold")
        )


class CardFrame(ctk.CTkFrame):
    def __init__(self, master, title=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(corner_radius=12)
        if title:
            ctk.CTkLabel(self, text=title, font=ctk.CTkFont(weight="bold", size=14)).pack(
                pady=(12, 8), padx=12, anchor="w"
            )


class StatsCard(ctk.CTkFrame):
    def __init__(self, master, title, value, icon=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(corner_radius=12, height=92)
        self.grid_columnconfigure(0, weight=1)
        self.value_label = ctk.CTkLabel(self, text=value, font=ctk.CTkFont(size=24, weight="bold"))
        self.value_label.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 0))
        self.title_label = ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=12))
        self.title_label.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 12))
        if icon:
            ctk.CTkLabel(self, text=icon, font=ctk.CTkFont(size=16)).grid(
                row=0, column=1, rowspan=2, sticky="e", padx=12, pady=12
            )


# ============================================================
# Página Principal
# ============================================================
class UsuariosPage(ctk.CTkFrame):
    """
    Foco:
      - Tema coerente / responsivo
      - PERMISSÕES sem rolagem: grupos em grade (N_COLS_PERM)
      - Linhas separadoras entre áreas
      - Integração com PostgreSQL
    """
    N_COLS_PERM = 3 # colunas na grade da aba Permissões

    # ---------------- Construtor ----------------
    def __init__(self, host):
        """
        host:
          - Quando aberto pelo MENU_PRINCIPAL: instancia de OperaMenuApp (tem .content)
          - Quando aberto em modo teste: HostMock ou root, com ou sem .content_scroll
        """

        # 0) Resolve o parent-base a partir do host
        #    - Dentro do menu: usa host.content (CTkScrollableFrame do MENU_PRINCIPAL)
        #    - Fallback antigo: host.content_scroll
        #    - Último recurso: o próprio host
        if hasattr(host, "content"):
            resolved_parent = host.content
        elif hasattr(host, "content_scroll"):
            resolved_parent = host.content_scroll
        else:
            resolved_parent = host

        # 1) Verifica conexão com PostgreSQL (mesma lógica original)
        if POSTGRES_AVAILABLE:
            ok, msg = require_ready()
            if not ok:
                messagebox.showerror(
                    "Erro de Banco de Dados",
                    f"Não foi possível conectar ao PostgreSQL:\n{msg}",
                )
                # cria um frame "vazio" para evitar crash do caller
                super().__init__(resolved_parent)
                return
        else:
            messagebox.showwarning("Aviso", "Módulo PostgreSQL não disponível.")

        # 2) Garante um parent com suporte Tk (para modo teste / situações especiais)
        parent = resolved_parent
        self._owned_root = None
        if not getattr(parent, "tk", None):
            # Fallback técnico: cria um root oculto sem mexer no appearance_mode global
            self._owned_root = ctk.CTk()
            self._owned_root.withdraw()
            parent = self._owned_root

        # 3) Inicializa o frame base
        super().__init__(parent)
        self.host = host

        # 4) Estados e variáveis (original)
        self.user_id: Optional[int] = None
        self._boxes: Dict[str, tuple] = {}
        self._name2code: Dict[str, str] = {}
        self.PERM_COLS = 3

        self.usuario_var = ctk.StringVar(master=self)
        self.email_var = ctk.StringVar(master=self)
        self.hier_var = ctk.StringVar(master=self, value="Operador")
        self.ativo_var = ctk.BooleanVar(master=self, value=True)
        self.senha_var = ctk.StringVar(master=self)
        self.dica_var = ctk.StringVar(master=self)
        self.busca_var = ctk.StringVar(master=self)
        self.telefone_var = ctk.StringVar(master=self)
        self.departamento_var = ctk.StringVar(master=self)

        # 5) >>> APLICA O TEMA/ESTILO ANTES DE CRIAR OS WIDGETS <<<
        #    Isso evita o “flash” porque a Treeview e afins já nascem estilizados.
        self._setup_theme_fallbacks()
        self._apply_theme()  # PRÉ-estilização

        # 6) Agora sim, constrói a UI (agora os widgets já nascem com o tema certo)
        self._build_ui()

        # 7) Passo de segurança: reaplica para pintar qualquer widget recém-criado
        self._apply_theme()

        # 8) Carregamentos e binds (original)
        self._pesquisar_usuarios()
        self._load_logs()
        self._update_stats()
        self._setup_user_binds()

        # 9) Atalhos e janela (original)
        try:
            tl = self.winfo_toplevel()
            tl.bind("<Control-n>", lambda e: self._novo_usuario())
            tl.bind("<Control-s>", lambda e: self._salvar_usuario())
            tl.bind("<Delete>", lambda e: self._excluir_usuario())
            try:
                tl.state("zoomed")
            except Exception:
                try:
                    tl.attributes("-zoomed", True)
                except Exception:
                    pass
        except Exception:
            pass

        # 10) Se criou um root técnico, garante que ele apareça em tela em modo teste
        if self._owned_root is not None:
            self._owned_root.update_idletasks()
            self._owned_root.deiconify()
            try:
                self._owned_root.state("zoomed")
            except Exception:
                pass
            self._owned_root.lift()
            self._owned_root.focus_force()

    # ---------------- Banco PostgreSQL ----------------
    def _exec_sql(self, sql: str, params: tuple = None, fetch: bool = False):
        if not POSTGRES_AVAILABLE:
            print(f"[DEMO] SQL: {sql} {params}")
            return []

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                if fetch and sql.strip().upper().startswith("SELECT"):
                    return cur.fetchall()
                conn.commit()
                return cur.rowcount

    def _fetch_one(self, sql: str, params: tuple = None):
        if not POSTGRES_AVAILABLE:
            print(f"[DEMO] SQL: {sql} {params}")
            return None
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()

    def _fetch_all(self, sql: str, params: tuple = None):
        if not POSTGRES_AVAILABLE:
            print(f"[DEMO] SQL: {sql} {params}")
            return []
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()

    def _ativo_true_pred(self, colname="ativo") -> str:
        # Funciona tanto para INTEGER(0/1) quanto para BOOLEAN
        return f"COALESCE({colname}::text,'0') IN ('1','t','true','TRUE')"

    # ---------------- Tema ----------------
    def _setup_theme_fallbacks(self):
        defaults = {
            "cor_fundo": "#f8fafc",
            "cor_borda": "#e5e7eb",
            "cor_secundaria": "#ffffff",
            "cor_primaria": "#2563eb",
            "cor_texto": "#111827",
            "cor_sucesso": "#10b981",
            "cor_aviso": "#f59e0b",
            "cor_perigo": "#ef4444",
        }
        for k, v in defaults.items():
            if not hasattr(self.host, k):
                setattr(self.host, k, v)

    def _get_palette_from_host(self) -> dict:
        try:
            mode = ctk.get_appearance_mode()
        except Exception:
            mode = "Light"

        pal = {
            "bg": getattr(self.host, "cor_fundo", None),
            "bg2": getattr(self.host, "cor_secundaria", None),
            "brd": getattr(self.host, "cor_borda", None),
            "pri": getattr(self.host, "cor_primaria", None),
            "txt": getattr(self.host, "cor_texto", None),
            "success": getattr(self.host, "cor_sucesso", None),
            "warning": getattr(self.host, "cor_aviso", None),
            "danger": getattr(self.host, "cor_perigo", None),
        }

        if str(mode).lower().startswith("dark"):
            defaults = {
                "bg": "#0f172a", "bg2": "#111827", "brd": "#1f2937",
                "pri": "#3b82f6", "txt": "#e5e7eb",
                "thead_bg": "#111827", "sel": "#2563eb",
                "success": "#10b981", "warning": "#f59e0b", "danger": "#ef4444"
            }
        else:
            defaults = {
                "bg": "#f8fafc", "bg2": "#ffffff", "brd": "#e5e7eb",
                "pri": "#2563eb", "txt": "#111827",
                "thead_bg": "#f1f5f9", "sel": "#dbeafe",
                "success": "#10b981", "warning": "#f59e0b", "danger": "#ef4444"
            }
        for k, v in defaults.items():
            if pal.get(k) is None:
                pal[k] = v
        pal["mode"] = mode
        return pal

    def _apply_theme(self):
        pal = self._get_palette_from_host()
        try:
            self.configure(fg_color=pal["bg"], border_color=pal["brd"])
        except Exception:
            pass

        style = ttk.Style(self.winfo_toplevel())
        try:
            style.theme_use("default")
        except Exception:
            pass
        style.configure("Treeview",
                        background=pal["bg2"],
                        foreground=pal["txt"],
                        fieldbackground=pal["bg2"],
                        rowheight=28,
                        font=("Segoe UI", 11),
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        background=pal["thead_bg"],
                        foreground=pal["txt"],
                        font=("Segoe UI", 11, "bold"),
                        borderwidth=0)
        style.map("Treeview",
                  background=[("selected", pal["sel"])],
                  foreground=[("selected", "#111827")])

        def paint(widget):
            if isinstance(widget, (ctk.CTkFrame, ctk.CTkScrollableFrame, CardFrame, StatsCard, ctk.CTkTabview)):
                try:
                    bgc = pal["bg"] if widget is self else pal["bg2"]
                    widget.configure(fg_color=bgc, border_color=pal["brd"])
                except Exception:
                    pass
            if isinstance(widget, ctk.CTkLabel):
                try:
                    widget.configure(text_color=pal["txt"])
                except Exception:
                    pass
            for child in widget.winfo_children():
                paint(child)

        paint(self)

    # ============================================================
    # ---------------- Regras de Negócio (Usuários) --------------
    # ============================================================
    def _pesquisar_usuarios(self, event=None):
        termo = (self.busca_var.get() or "").strip()
        if not POSTGRES_AVAILABLE:
            # Dados de demonstração com o usuário correto
            demo_data = [
                (1, "GIL DE OLIVEIRA", "opera@.com", "Admin", True, "2024-01-01 10:00"),
                (2, "usuario1", "user1@sistema.com", "Operador", True, "2024-01-02 09:00"),
                (3, "usuario2", "user2@sistema.com", "Estoque", False, None),
            ]
            self._popular_lista(demo_data)
            self._update_stats()
            return

        schema = get_schema()
        if termo:
            sql = f"""
                SELECT id, usuario, email, hierarquia, ativo, ultimo_login
                FROM {schema}.usuarios
                WHERE usuario ILIKE %s OR email ILIKE %s OR departamento ILIKE %s
                ORDER BY usuario
            """
            params = (f"%{termo}%", f"%{termo}%", f"%{termo}%")
        else:
            sql = f"""
                SELECT id, usuario, email, hierarquia, ativo, ultimo_login
                FROM {schema}.usuarios
                ORDER BY usuario
            """
            params = ()
        rows = self._fetch_all(sql, params)
        self._popular_lista(rows)
        self._update_stats()

    def _popular_lista(self, rows):
        if not hasattr(self, "tree"):
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        for r in rows or []:
            ativo = "Sim" if (r[4] if len(r) > 4 else False) else "Não"
            ultimo = r[5] if (len(r) > 5 and r[5]) else "Nunca"
            self.tree.insert("", "end", values=(r[0], r[1], r[2], r[3], ativo, ultimo))

    def _carregar_usuario(self, usuario_id: int):
        if not POSTGRES_AVAILABLE:
            demo = {"usuario": "admin", "email": "admin@sistema.com", "hierarquia": "Admin",
                    "ativo": True, "dica_senha": "", "telefone": "", "departamento": ""}
            self.usuario_var.set(demo["usuario"])
            self.email_var.set(demo["email"])
            self.hier_var.set(demo["hierarquia"])
            self.ativo_var.set(demo["ativo"])
            self.dica_var.set(demo["dica_senha"])
            self.telefone_var.set(demo["telefone"])
            self.departamento_var.set(demo["departamento"])
            self.senha_var.set("")
            return
        try:
            schema = get_schema()
            row = self._fetch_one(f"SELECT * FROM {schema}.usuarios WHERE id = %s", (usuario_id,))
            if not row:
                messagebox.showwarning("Aviso", f"Usuário com ID {usuario_id} não encontrado.")
                return

            # Mapeamento defensivo por índice
            # Espera-se (id, usuario, senha_hash, hierarquia, email, data_criacao,
            #            ativo, dica_senha, ultimo_login, ... telefone, departamento ...)
            self.usuario_var.set(row[1] if len(row) > 1 else "")
            self.hier_var.set(row[3] if len(row) > 3 else "Operador")
            self.email_var.set(row[4] if len(row) > 4 else "")
            # ativo em índice 6 (bool/int/str)
            if len(row) > 6:
                v = row[6]
                if isinstance(v, bool):
                    self.ativo_var.set(v)
                elif isinstance(v, (int, float)):
                    self.ativo_var.set(bool(v))
                elif isinstance(v, str):
                    self.ativo_var.set(v.lower() in ("1", "true", "t", "sim", "yes", "on"))
                else:
                    self.ativo_var.set(True)
            self.dica_var.set(row[7] if len(row) > 7 else "")
            # telefone provável em 12, departamento em 13 (como em versões anteriores)
            self.telefone_var.set(row[12] if len(row) > 12 else "")
            self.departamento_var.set(row[13] if len(row) > 13 else "")
            self.senha_var.set("")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar usuário: {e}")

    def _validate_user_fields(self) -> Optional[str]:
        if not (self.usuario_var.get() or "").strip():
            return "Informe o nome de usuário."
        if not (self.hier_var.get() or "").strip():
            return "Informe a hierarquia."
        return None

    def _novo_usuario(self):
        self.user_id = None
        self.usuario_var.set("")
        self.email_var.set("")
        self.hier_var.set("Operador")
        self.ativo_var.set(True)
        self.senha_var.set("")
        self.dica_var.set("")
        self.telefone_var.set("")
        self.departamento_var.set("")
        if hasattr(self, "info_user_perm"):
            try:
                self.info_user_perm.configure(text="👤 Novo usuário (não salvo)")
            except Exception:
                pass
        self._limpar_permissoes_ui()

    def _salvar_usuario(self):
        err = self._validate_user_fields()
        if err:
            messagebox.showwarning("Validação", err)
            return

        schema = get_schema()
        usuario = (self.usuario_var.get() or "").strip()
        email = (self.email_var.get() or "").strip()
        hierarquia = (self.hier_var.get() or "Operador").strip()
        ativo = bool(self.ativo_var.get())
        dica = (self.dica_var.get() or "").strip()
        telefone = (self.telefone_var.get() or "").strip()
        departamento = (self.departamento_var.get() or "").strip()
        senha_txt = (self.senha_var.get() or "").strip()

        try:
            if self.user_id is None:
                # Inserção de novo usuário
                cols = ["usuario", "hierarquia", "email", "ativo", "dica_senha", "telefone", "departamento"]
                vals = [usuario, hierarquia, email, ativo, dica, telefone, departamento]
                ph = ["%s"] * len(vals)

                if senha_txt:
                    cols.insert(1, "senha_hash")
                    vals.insert(1, _hash_pwd(senha_txt))
                    ph.insert(1, "%s")

                sql = f"INSERT INTO {schema}.usuarios ({', '.join(cols)}) VALUES ({', '.join(ph)}) RETURNING id"
                row = self._fetch_one(sql, tuple(vals))
                new_id = row[0] if row else None
                self.user_id = new_id

                # SE FOR ADMIN, MARCA TODAS AS PERMISSÕES
                if hierarquia.lower() in ('admin', 'administrador', 'adm'):
                    self._marcar_todas_permissoes_admin(new_id)

                self._recarregar_lista_usuarios(selecionar_id=new_id)
                self._update_stats()
                registrar_log_db(usuario, "Usuários", "Criar", f"Usuário criado ID {new_id}")
                messagebox.showinfo("Usuários", "Usuário criado com sucesso.")

            else:
                # Atualização de usuário existente
                sets = ["usuario = %s", "hierarquia = %s", "email = %s", "ativo = %s",
                        "dica_senha = %s", "telefone = %s", "departamento = %s"]
                vals = [usuario, hierarquia, email, ativo, dica, telefone, departamento]
                if senha_txt:
                    sets.insert(1, "senha_hash = %s")
                    vals.insert(1, _hash_pwd(senha_txt))
                vals.append(self.user_id)

                sql = f"UPDATE {schema}.usuarios SET {', '.join(sets)} WHERE id = %s"
                self._exec_sql(sql, tuple(vals))

                # SE FOR ADMIN, MARCA TODAS AS PERMISSÕES
                if hierarquia.lower() in ('admin', 'administrador', 'adm'):
                    self._marcar_todas_permissoes_admin(self.user_id)

                self._recarregar_lista_usuarios(selecionar_id=self.user_id)
                self._update_stats()
                registrar_log_db(usuario, "Usuários", "Editar", f"Usuário editado ID {self.user_id}")
                messagebox.showinfo("Usuários", "Usuário atualizado com sucesso.")

        except Exception as e:
            messagebox.showerror("Usuários", f"Falha ao salvar: {e}")

    def _marcar_todas_permissoes_admin(self, usuario_id: int):
        """Marca todas as permissões como TRUE para usuários admin"""
        try:
            schema = get_schema()

            # Primeiro limpa permissões existentes
            self._exec_sql(f"DELETE FROM {schema}.usuario_permissoes WHERE usuario_id = %s", (usuario_id,))

            # Detecta quais colunas a tabela suporta
            has_print = bool(self._perm_cols.get("pode_imprimir"))
            has_del = bool(self._perm_cols.get("excluir"))
            has_adm = bool(self._perm_cols.get("administrar"))

            # Para cada permissão no catálogo, insere com todas as permissões TRUE
            for codigo in self._boxes.keys():
                cols = ["usuario_id", "codigo", "pode_ver", "pode_editar"]
                vals = [usuario_id, codigo, True, True]
                ph = ["%s", "%s", "%s::boolean", "%s::boolean"]

                if has_print:
                    cols.append("pode_imprimir")
                    vals.append(True)
                    ph.append("%s::boolean")
                if has_del:
                    cols.append("excluir")
                    vals.append(True)
                    ph.append("%s::boolean")
                if has_adm:
                    cols.append("administrar")
                    vals.append(True)
                    ph.append("%s::boolean")

                sql = f"INSERT INTO {schema}.usuario_permissoes ({', '.join(cols)}) VALUES ({', '.join(ph)})"
                self._exec_sql(sql, tuple(vals))

            print(f"[Admin] Todas as permissões marcadas para usuário ID {usuario_id}")

        except Exception as e:
            print(f"[Admin] Erro ao marcar permissões: {e}")

    def _excluir_usuario(self):
        if not self.user_id:
            messagebox.showwarning("Usuários", "Selecione um usuário para excluir.")
            return
        if not messagebox.askyesno("Excluir", "Tem certeza que deseja excluir este usuário?"):
            return
        try:
            schema = get_schema()
            # limpa permissões vinculadas
            self._exec_sql(f"DELETE FROM {schema}.usuario_permissoes WHERE usuario_id = %s", (self.user_id,))
            # exclui usuário
            self._exec_sql(f"DELETE FROM {schema}.usuarios WHERE id = %s", (self.user_id,))
            registrar_log_db("Sistema", "Usuários", "Excluir", f"Usuário ID {self.user_id}")
            self._novo_usuario()
            self._recarregar_lista_usuarios()
            messagebox.showinfo("Usuários", "Usuário excluído.")
        except Exception as e:
            messagebox.showerror("Usuários", f"Falha ao excluir: {e}")

    def _redefinir_senha(self):
        if not self.user_id:
            messagebox.showwarning("Senha", "Selecione um usuário.")
            return
        senha_txt = (self.senha_var.get() or "").strip()
        if not senha_txt:
            messagebox.showwarning("Senha", "Digite a nova senha no campo 'Senha' antes de confirmar.")
            return
        try:
            schema = get_schema()
            self._exec_sql(
                f"UPDATE {schema}.usuarios SET senha_hash = %s WHERE id = %s",
                (_hash_pwd(senha_txt), self.user_id),
            )
            registrar_log_db(self.usuario_var.get(), "Usuários", "RedefinirSenha", f"ID {self.user_id}")
            messagebox.showinfo("Senha", "Senha redefinida com sucesso.")
            self.senha_var.set("")
        except Exception as e:
            messagebox.showerror("Senha", f"Falha ao redefinir senha: {e}")

    def _on_tab_changed(self, event=None):
        """Chamado quando a aba é alterada"""
        try:
            selected_tab = self.notebook.get()
            if selected_tab == "🔐 Permissões":
                # Atualiza a lista de usuários na aba Permissões
                self._popular_tree_permissoes()
                # Se houver um usuário selecionado, carrega suas permissões
                if self.user_id:
                    self._carregar_permissoes_usuario()
        except Exception as e:
            print(f"[Tab Change] Erro: {e}")

    # ---------------- Permissões ----------------
    def _aplicar_permissoes_para_usuario(self):
        if not self.user_id:
            messagebox.showwarning("Permissões", "Selecione um usuário primeiro.")
            return
        try:
            self.notebook.set("🔐 Permissões")
            # Força a atualização da interface
            self._popular_tree_permissoes()
            self._carregar_permissoes_usuario()
            if hasattr(self, "info_user_perm"):
                try:
                    self.info_user_perm.configure(
                        text=f"👤 Usuário: {self.usuario_var.get() or '(sem nome)'} (ID: {self.user_id})"
                    )
                except Exception:
                    pass
        except Exception as e:
            print(f"[Permissões] Erro ao mudar aba: {e}")

    def _load_permissoes_catalogo_pg(self):
        """Carrega catálogo de permissões com lista fixa baseada nas tabelas do sistema"""
        try:
            # Lista completa de permissões baseada nas tabelas do seu sistema
            permissoes_completas = [
                # Sistema de Usuários
                ('usuarios', 'Usuários', 'Sistema'),
                ('usuario_permissoes', 'Permissões de Usuários', 'Sistema'),
                ('usuario_logs', 'Logs do Sistema', 'Sistema'),
                ('usuario_preferencias', 'Preferências', 'Sistema'),

                # Cadastros
                ('cadastro_modelos_cabecalho', 'Modelos - Cabeçalho', 'Cadastros'),
                ('cadastro_modelos_tecidos', 'Modelos - Tecidos', 'Cadastros'),
                ('cadastro_modelos_aviamentos', 'Modelos - Aviamentos', 'Cadastros'),
                ('cadastro_modelos_outros', 'Modelos - Outros', 'Cadastros'),
                ('cadastro_modelos_imagens', 'Modelos - Imagens', 'Cadastros'),
                ('cadastro_faccoes', 'Prestadores', 'Cadastros'),
                ('ficha_tecnica_cabecalho', 'Ficha Técnica', 'Cadastros'),

                # Corte
                ('cadastro_de_corte', 'Cadastro de Corte', 'Corte'),
                ('cadastro_de_corte_tecidos', 'Corte - Tecidos', 'Corte'),
                ('cadastro_de_corte_lotes', 'Corte - Lotes', 'Corte'),
                ('ordem_corte_ficha', 'Ordem de Corte', 'Corte'),
                ('adiantamento_faccao', 'Adiantamento Facção', 'Corte'),

                # Envio e Acabamento
                ('envios_cortes', 'Envios de Corte', 'Acabamento'),
                ('controle_envio_cortes', 'Controle de Envio', 'Acabamento'),
                ('entrada_acabamento', 'Entrada Acabamento', 'Acabamento'),
                ('controle_retorno_cortes', 'Retorno de Cortes', 'Acabamento'),
                ('cortes_finalizados', 'Cortes Finalizados', 'Acabamento'),
                ('pecas_finalizadas', 'Peças Finalizadas', 'Acabamento'),

                # Estoque
                ('estoque_tecidos', 'Estoque de Tecidos', 'Estoque'),
                ('estoque_aviamentos', 'Estoque de Aviamentos', 'Estoque'),
                ('estoque_insumos', 'Estoque de Insumos', 'Estoque'),
                ('estoque_escritorio', 'Estoque Escritório', 'Estoque'),
                ('estoque_limpeza', 'Estoque Limpeza', 'Estoque'),
                ('estoque_outros', 'Estoque Outros', 'Estoque'),

                # Financeiro
                ('pagamento_corte_acabamento', 'Pagamentos', 'Financeiro'),
                ('pricing_profiles', 'Perfis de Preço', 'Financeiro'),

                # Serviços
                ('servicos', 'Serviços', 'Serviços'),
                ('historico_servicos', 'Histórico Serviços', 'Serviços')
            ]

            grupos = {}
            for codigo, nome, grupo in permissoes_completas:
                grupos.setdefault(grupo, []).append((codigo, nome, grupo, None))

            self._render_grupos_permissoes(grupos)

        except Exception as e:
            messagebox.showerror("Permissões", f"Erro ao carregar catálogo: {e}")

    def _carregar_permissoes_usuario(self):
        if not self.user_id or not self._boxes:
            return
        for vars in self._boxes.values():
            for v in vars:
                v.set(False)
        try:
            schema = get_schema()
            # Para cada permissão no catálogo, verifica se existe na tabela usuario_permissoes
            for codigo in self._boxes.keys():
                sql = f"""
                    SELECT pode_ver, pode_editar, pode_imprimir, excluir, administrar
                    FROM {schema}.usuario_permissoes 
                    WHERE usuario_id = %s AND codigo = %s
                """
                row = self._fetch_one(sql, (self.user_id, codigo))
                if row:
                    v = self._boxes[codigo]
                    v[0].set(bool(row[0]))
                    v[1].set(bool(row[1]))
                    v[2].set(bool(row[2]))
                    v[3].set(bool(row[3]))
                    v[4].set(bool(row[4]))
        except Exception as e:
            print(f"[Permissões] Erro ao carregar: {e}")

    def _salvar_permissoes_usuario(self):
        """Salva permissões do usuário atual.
        - Usa booleans reais para colunas booleanas.
        - Aplica ::boolean nos placeholders para garantir tipagem correta no PostgreSQL.
        - Respeita colunas existentes (self._perm_cols).
        """
        # Se Admin: marca tudo na UI (garante persistência full)
        try:
            hier = (self.hier_var.get() or "").strip().lower() if hasattr(self, "hier_var") else ""
            if hier in ("admin", "administrador", "adm"):
                for flags in self._boxes.values():
                    for v in flags:
                        try:
                            v.set(True)
                        except Exception:
                            pass
        except Exception as _e:
            print(f"[Permissões] fallback admin (salvar): {_e}")

        # Validações
        if not getattr(self, "user_id", None):
            messagebox.showwarning("Permissões", "Selecione um usuário para salvar.")
            return
        if not getattr(self, "_boxes", None):
            messagebox.showwarning("Permissões", "Nada para salvar.")
            return

        try:
            schema = get_schema()

            # Limpa as permissões anteriores
            self._exec_sql(f"DELETE FROM {schema}.usuario_permissoes WHERE usuario_id = %s", (self.user_id,))

            # Quais colunas a tabela realmente tem?
            # self._perm_cols deve ter sido populado por _detect_perm_columns()
            has_print = bool(self._perm_cols.get("pode_imprimir"))
            has_del = bool(self._perm_cols.get("excluir"))
            has_adm = bool(self._perm_cols.get("administrar"))

            for codigo, flags in self._boxes.items():
                # Extrai flags como booleans
                try:
                    ver = bool(getattr(flags[0], "get", lambda: 0)())
                    editar = bool(getattr(flags[1], "get", lambda: 0)())
                    imprimir = bool(getattr(flags[2], "get", lambda: 0)()) if len(flags) > 2 else False
                    excluir = bool(getattr(flags[3], "get", lambda: 0)()) if len(flags) > 3 else False
                    administrar = bool(getattr(flags[4], "get", lambda: 0)()) if len(flags) > 4 else False
                except Exception:
                    ver = editar = imprimir = excluir = administrar = False

                # Só grava se houver ao menos uma permissão marcada
                if not (ver or editar or imprimir or excluir or administrar):
                    continue

                # Monta colunas e placeholders com cast booleano
                cols = ["usuario_id", "codigo", "pode_ver", "pode_editar"]
                vals = [self.user_id, codigo, ver, editar]
                ph = ["%s", "%s", "%s::boolean", "%s::boolean"]

                if has_print:
                    cols.append("pode_imprimir");
                    vals.append(imprimir);
                    ph.append("%s::boolean")
                if has_del:
                    cols.append("excluir");
                    vals.append(excluir);
                    ph.append("%s::boolean")
                if has_adm:
                    cols.append("administrar");
                    vals.append(administrar);
                    ph.append("%s::boolean")

                sql = f"INSERT INTO {schema}.usuario_permissoes ({', '.join(cols)}) VALUES ({', '.join(ph)})"
                self._exec_sql(sql, tuple(vals))

            try:
                registrar_log_db(self.usuario_var.get(), "Permissões", "Salvar", f"Usuario ID {self.user_id}")
            except Exception:
                pass

            messagebox.showinfo("Permissões", "Permissões salvas.")
        except Exception as e:
            messagebox.showerror("Permissões", f"Falha ao salvar permissões: {e}")

    def _limpar_permissoes_ui(self):
        if not self._boxes:
            return
        for vars in self._boxes.values():
            for v in vars:
                v.set(False)

    def _detect_perm_columns(self):
        """Detecta quais colunas existem em {schema}.usuario_permissoes e guarda em self._perm_cols."""
        self._perm_cols = {
            'pode_ver': True,
            'pode_editar': True,
            'pode_imprimir': False,
            'excluir': False,
            'administrar': False,
        }
        if not POSTGRES_AVAILABLE:
            return
        try:
            schema = get_schema()
            rows = self._fetch_all(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s",
                (schema, 'usuario_permissoes')
            )
            cols = {r[0] for r in rows or []}
            for k in list(self._perm_cols.keys()):
                self._perm_cols[k] = (k in cols)
        except Exception as e:
            # Se falhar, mantém defaults seguros
            pass

    # ---------------- Logs ----------------
    def _load_logs(self):
        self._filtrar_logs()

    def _filtrar_logs(self):
        if not hasattr(self, "tree_logs"):
            return
        data_ini = (self.log_ini.get() or "").strip() if hasattr(self, "log_ini") else ""
        data_fim = (self.log_fim.get() or "").strip() if hasattr(self, "log_fim") else ""
        termo = (self.log_busca.get() or "").strip() if hasattr(self, "log_busca") else ""

        where = []
        params = []
        if data_ini:
            where.append("data_hora >= %s")
            params.append(f"{data_ini} 00:00:00")
        if data_fim:
            where.append("data_hora <= %s")
            params.append(f"{data_fim} 23:59:59")
        if termo:
            where.append("(usuario ILIKE %s OR pagina ILIKE %s OR acao ILIKE %s OR detalhe ILIKE %s)")
            like = f"%{termo}%"
            params.extend([like, like, like, like])

        where_sql = "WHERE " + " AND ".join(where) if where else ""
        schema = get_schema()
        try:
            rows = self._fetch_all(
                f"""SELECT data_hora, usuario, acao, pagina, detalhe
                    FROM {schema}.usuario_logs
                    {where_sql}
                    ORDER BY data_hora DESC
                    LIMIT 1000""",
                tuple(params),
            )
        except Exception:
            rows = []

        for item in self.tree_logs.get_children():
            self.tree_logs.delete(item)
        for r in rows or []:
            self.tree_logs.insert("", "end", values=(r[0], r[1], r[2], r[3], r[4]))

    def _limpar_filtros_logs(self):
        try:
            self.log_ini.delete(0, "end")
            self.log_fim.delete(0, "end")
            self.log_busca.delete(0, "end")
        except Exception:
            pass
        self._filtrar_logs()

    def _exportar_logs_csv(self):
        try:
            schema = get_schema()
            rows = self._fetch_all(
                f"""SELECT data_hora, usuario, acao, pagina, detalhe
                    FROM {schema}.usuario_logs
                    ORDER BY data_hora DESC"""
            )
            base_dir = os.path.dirname(os.path.abspath(__file__))
            out_dir = os.path.join(base_dir, "relatorios")
            os.makedirs(out_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho = os.path.join(out_dir, f"logs_{ts}.csv")
            with open(caminho, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["data_hora", "usuario", "acao", "pagina", "detalhe"])
                for r in rows or []:
                    w.writerow([r[0], r[1], r[2], r[3], r[4]])
            messagebox.showinfo("Logs", f"CSV salvo em:\n{caminho}")
        except Exception as e:
            messagebox.showerror("Logs", f"Falha ao exportar: {e}")

    # ---------------- Estatísticas ----------------
    def _update_stats(self):
        try:
            schema = get_schema()
            total = self._fetch_one(f"SELECT COUNT(*) FROM {schema}.usuarios")[0] if POSTGRES_AVAILABLE else 3
            self.stats_total.value_label.configure(text=str(total))

            ativos = self._fetch_one(f"SELECT COUNT(*) FROM {schema}.usuarios WHERE {self._ativo_true_pred('ativo')}")[
                0] if POSTGRES_AVAILABLE else 2
            self.stats_ativos.value_label.configure(text=str(ativos))

            admins = self._fetch_one(f"SELECT COUNT(*) FROM {schema}.usuarios WHERE hierarquia = 'Admin'")[
                0] if POSTGRES_AVAILABLE else 1
            self.stats_admins.value_label.configure(text=str(admins))

            hoje = datetime.now().strftime("%Y-%m-%d")
            logs = self._fetch_one(f"SELECT COUNT(*) FROM {schema}.usuario_logs WHERE DATE(data_hora) = %s", (hoje,))[
                0] if POSTGRES_AVAILABLE else 0
            self.stats_logs.value_label.configure(text=str(logs))
        except Exception as e:
            print(f"[Stats] erro: {e}")

    def _recarregar_lista_usuarios(self, selecionar_id: Optional[int] = None):
        try:
            schema = get_schema()
            rows = self._fetch_all(
                f"""SELECT id, usuario, email, hierarquia, ativo, ultimo_login
                    FROM {schema}.usuarios
                    ORDER BY usuario"""
            )
            self._popular_lista(rows)
            if selecionar_id is not None:
                for item in self.tree.get_children():
                    vals = self.tree.item(item, "values")
                    if vals and str(vals[0]) == str(selecionar_id):
                        self.tree.selection_set(item)
                        self.tree.focus(item)
                        break
        except Exception as e:
            print(f"[Lista] erro: {e}")

    # ============================================================
    # ------------------------ UI -------------------------------
    # ============================================================
    def _build_ui(self):
        # Layout base
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        pal = self._get_palette_from_host()

        # Container principal
        main = ctk.CTkFrame(self, fg_color=pal["bg"])
        main.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # Cards de estatísticas
        stats = ctk.CTkFrame(main, fg_color="transparent", height=90)
        stats.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        stats.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.stats_total = StatsCard(stats, "Total de Usuários", "0", "👥", fg_color=pal["bg2"])
        self.stats_total.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        self.stats_ativos = StatsCard(stats, "Usuários Ativos", "0", "✅", fg_color=pal["bg2"])
        self.stats_ativos.grid(row=0, column=1, padx=6, sticky="nsew")

        self.stats_admins = StatsCard(stats, "Administradores", "0", "👑", fg_color=pal["bg2"])
        self.stats_admins.grid(row=0, column=2, padx=6, sticky="nsew")

        self.stats_logs = StatsCard(stats, "Logs Hoje", "0", "📊", fg_color=pal["bg2"])
        self.stats_logs.grid(row=0, column=3, padx=(6, 0), sticky="nsew")

        # Abas
        self.notebook = ctk.CTkTabview(main)
        self.notebook.grid(row=1, column=0, sticky="nsew")

        self.tab_usuarios = self.notebook.add("👥 Usuários")
        self.tab_permissoes = self.notebook.add("🔐 Permissões")
        self.tab_logs = self.notebook.add("📊 Logs")
        self.tab_dashboard = self.notebook.add("📈 Dashboard")
        self.notebook.configure(command=self._on_tab_changed)

        for tab in (self.tab_usuarios, self.tab_permissoes, self.tab_logs, self.tab_dashboard):
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)

        self._build_tab_usuarios()
        self._build_tab_logs()
        self._build_tab_dashboard()
        self._build_tab_permissoes()

        try:
            self.notebook.set("👥 Usuários")
        except Exception:
            pass

    # ---------- Aba Usuários ----------
    def _build_tab_usuarios(self):
        pal = self._get_palette_from_host()

        users_container = ctk.CTkFrame(self.tab_usuarios, fg_color="transparent")
        users_container.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        users_container.grid_rowconfigure(1, weight=1)
        users_container.grid_columnconfigure(0, weight=3)
        users_container.grid_columnconfigure(1, weight=2)

        actions_frame = CardFrame(users_container, title="Ações", fg_color=pal["bg2"])
        actions_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        actions_inner = ctk.CTkFrame(actions_frame, fg_color="transparent")
        actions_inner.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(actions_inner, text="🔍").pack(side="left", padx=(0, 6))
        self.busca_entry = ctk.CTkEntry(actions_inner, textvariable=self.busca_var,
                                        placeholder_text="Buscar por usuário, email ou departamento...", width=320)
        self.busca_entry.pack(side="left", padx=(0, 10))
        self.busca_entry.bind("<Return>", self._pesquisar_usuarios)

        ModernButton(actions_inner, "Pesquisar", command=self._pesquisar_usuarios).pack(side="left", padx=4)
        ModernButton(actions_inner, "Novo Usuário", command=self._novo_usuario).pack(side="left", padx=4)
        ModernButton(actions_inner, "Salvar", command=self._salvar_usuario).pack(side="left", padx=4)
        ModernButton(actions_inner, "Excluir", command=self._excluir_usuario,
                     fg_color=pal["danger"], text_color=get_contraste_texto(pal.get("danger", "#DC2626")), hover_color="#dc2626").pack(side="left", padx=4)

        # Lista (esquerda)
        list_frame = CardFrame(users_container, title="Lista de Usuários", fg_color=pal["bg2"])
        list_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        tree_container = ctk.CTkFrame(list_frame, fg_color="transparent")
        tree_container.pack(fill="both", expand=True, padx=12, pady=12)
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)

        cols = ("id", "usuario", "email", "hierarquia", "ativo", "ultimo_login")
        self.tree = ttk.Treeview(tree_container, columns=cols, show="headings", selectmode="browse")

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        headers = {
            "id": "ID", "usuario": "Usuário", "email": "E-mail",
            "hierarquia": "Hierarquia", "ativo": "Ativo", "ultimo_login": "Último Login",
        }
        for c in cols:
            self.tree.heading(c, text=headers[c])

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("usuario", width=160, anchor="w")
        self.tree.column("email", width=220, anchor="w")
        self.tree.column("hierarquia", width=120, anchor="center")
        self.tree.column("ativo", width=70, anchor="center")
        self.tree.column("ultimo_login", width=150, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<<TreeviewSelect>>", self._on_select_user)
        self.tree.bind("<Return>", self._on_select_user)
        self.tree.bind("<Double-1>", self._on_select_user)

        # Form (direita)
        form_frame = CardFrame(users_container, title="Detalhes do Usuário", fg_color=pal["bg2"])
        form_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 0))

        form_inner = ctk.CTkFrame(form_frame, fg_color="transparent")
        form_inner.pack(fill="both", expand=True, padx=12, pady=12)
        form_inner.grid_columnconfigure(1, weight=1)

        row = 0

        def add_row(label, widget):
            nonlocal row
            ctk.CTkLabel(form_inner, text=label, anchor="w").grid(row=row, column=0, sticky="w", pady=(0, 6))
            widget.grid(row=row, column=1, sticky="ew", pady=(0, 10), padx=(10, 0))
            row += 1

        self.ed_usuario = ctk.CTkEntry(form_inner, textvariable=self.usuario_var)
        add_row("Usuário *", self.ed_usuario)

        self.ed_email = ctk.CTkEntry(form_inner, textvariable=self.email_var)
        add_row("E-mail", self.ed_email)

        self.ed_telefone = ctk.CTkEntry(form_inner, textvariable=self.telefone_var)
        add_row("Telefone", self.ed_telefone)

        self.ed_departamento = ctk.CTkEntry(form_inner, textvariable=self.departamento_var)
        add_row("Departamento", self.ed_departamento)

        self.cb_hierarquia = ctk.CTkComboBox(form_inner, variable=self.hier_var,
                                             values=["Admin", "Operador", "Cortes", "Estoque", "Financeiro",
                                                     "Acabamento"])
        add_row("Hierarquia *", self.cb_hierarquia)

        self.sw_ativo = ctk.CTkSwitch(form_inner, text="Usuário ativo", variable=self.ativo_var)
        add_row("Status", self.sw_ativo)

        self.ed_senha = ctk.CTkEntry(form_inner, textvariable=self.senha_var, show="•",
                                     placeholder_text="Deixe em branco para manter a atual")
        add_row("Senha", self.ed_senha)

        self.ed_dica = ctk.CTkEntry(form_inner, textvariable=self.dica_var)
        add_row("Dica de Senha", self.ed_dica)

        ModernButton(form_inner, "Gerenciar Permissões", command=self._aplicar_permissoes_para_usuario).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8)
        )
        row += 1
        ModernButton(form_inner, "Redefinir Senha", command=self._redefinir_senha).grid(
            row=row, column=0, columnspan=2, sticky="ew"
        )

        row += 1

        # Label informativo para permissões
        if not hasattr(self, 'info_user_perm'):
            self.info_user_perm = ctk.CTkLabel(form_inner, text="👤 Nenhum usuário selecionado",
                                               font=ctk.CTkFont(weight="bold"))
            self.info_user_perm.grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 0))

    # ---------- Helpers: lista de usuários na aba Permissões ----------
    def _popular_tree_permissoes(self):
        """Preenche a lista de usuários na aba Permissões."""
        try:
            schema = get_schema()
            rows = self._fetch_all(
                f"SELECT id, usuario, hierarquia, COALESCE(ativo,false) FROM {schema}.usuarios ORDER BY usuario"
            ) or []
        except Exception:
            rows = []
        try:
            for it in self.tree_permissoes.get_children():
                self.tree_permissoes.delete(it)
            for uid, nome, hier, ativo in rows:
                self.tree_permissoes.insert("", "end", values=(uid, nome, hier, "Sim" if ativo else "Não"))
        except Exception:
            pass

    def _on_user_double_click_perms(self, event=None):
        """Duplo clique na lista de usuários (aba Permissões): define user_id e carrega permissões."""
        try:
            sel = self.tree_permissoes.selection()
            if not sel:
                return
            item = self.tree_permissoes.item(sel[0])
            vals = item.get("values", [])
            if not vals:
                return
            self.user_id = int(vals[0])
            if hasattr(self, "usuario_var"):
                self.usuario_var.set(str(vals[1]))
            if hasattr(self, "hier_var"):
                self.hier_var.set(str(vals[2]))
            self._carregar_permissoes_usuario()
        except Exception as e:
            try:
                from tkinter import messagebox
                messagebox.showerror("Permissões", f"Falha ao carregar permissões: {e}")
            except Exception:
                print("[Permissões]", e)

    # ---------- Aba Permissões ----------
    def _build_tab_permissoes(self):
        parent = self.tab_permissoes

        for w in parent.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        parent.grid_rowconfigure(1, weight=0)
        parent.grid_rowconfigure(2, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # Barra de ações
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))

        # Lista de usuários (topo) para seleção rápida de quem terá permissões carregadas
        list_wrap = ctk.CTkFrame(parent, fg_color="transparent")
        list_wrap.grid(row=1, column=0, sticky="ew", padx=10, pady=(8, 0))

        self.tree_permissoes = ttk.Treeview(
            list_wrap,
            columns=("id", "usuario", "hierarquia", "ativo"),
            show="headings",
            height=6,
            selectmode="browse"
        )
        self.tree_permissoes.heading("id", text="ID");
        self.tree_permissoes.column("id", width=60, anchor="center")
        self.tree_permissoes.heading("usuario", text="Usuário");
        self.tree_permissoes.column("usuario", width=220, anchor="w")
        self.tree_permissoes.heading("hierarquia", text="Hierarquia");
        self.tree_permissoes.column("hierarquia", width=130, anchor="center")
        self.tree_permissoes.heading("ativo", text="Ativo");
        self.tree_permissoes.column("ativo", width=70, anchor="center")
        self.tree_permissoes.pack(fill="x")

        self.tree_permissoes.bind("<Double-1>", self._on_user_double_click_perms)

        try:
            self._popular_tree_permissoes()
        except Exception:
            pass

        for c in range(7):
            bar.grid_columnconfigure(c, weight=0)
        bar.grid_columnconfigure(7, weight=1)

        ctk.CTkButton(bar, text="Marcar tudo", width=120,
                      command=lambda: self._set_all_perms(True)).grid(row=0, column=0, padx=4)
        ctk.CTkButton(bar, text="Desmarcar", width=120,
                      command=lambda: self._set_all_perms(False)).grid(row=0, column=1, padx=4)
        ctk.CTkButton(bar, text="Todos VER", width=110,
                      command=lambda: self._set_col_perm("ver", True)).grid(row=0, column=2, padx=(20, 4))
        ctk.CTkButton(bar, text="Todos EDITAR", width=110,
                      command=lambda: self._set_col_perm("editar", True)).grid(row=0, column=3, padx=4)
        ctk.CTkButton(bar, text="Todos IMPRIMIR", width=130,
                      command=lambda: self._set_col_perm("imprimir", True)).grid(row=0, column=4, padx=4)
        ctk.CTkButton(bar, text="Todos EXCLUIR", width=120,
                      command=lambda: self._set_col_perm("excluir", True)).grid(row=0, column=5, padx=4)
        ctk.CTkButton(bar, text="Salvar Permissões", width=150,
                      command=self._salvar_permissoes_usuario).grid(row=0, column=6, padx=(20, 4))

        # Grid principal
        self.perm_grid = ctk.CTkFrame(parent, fg_color="transparent")
        self.perm_grid.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)

        self.PERM_COLS = getattr(self, "PERM_COLS", 3)
        for c in range(self.PERM_COLS):
            self.perm_grid.grid_columnconfigure(c * 2, weight=1, uniform="dept")
            if c < self.PERM_COLS - 1:
                self.perm_grid.grid_columnconfigure(c * 2 + 1, weight=0)

        self._boxes = {}
        self._name2code = {}

        # Detecta colunas suportadas pela tabela usuario_permissoes
        self._detect_perm_columns()

        # Carrega catálogo do PostgreSQL
        self._load_permissoes_catalogo_pg()

    def _set_all_perms(self, val: bool):
        for (ver, editar, imprimir, excluir, administrar) in self._boxes.values():
            ver.set(val)
            editar.set(val)
            imprimir.set(val)
            excluir.set(val)
            administrar.set(False)  # não marca admin em massa por segurança
        if val:
            for (ver, editar, imprimir, excluir, administrar) in self._boxes.values():
                if editar.get() or excluir.get():
                    ver.set(True)

    def _set_col_perm(self, col: str, val: bool):
        for (ver, editar, imprimir, excluir, administrar) in self._boxes.values():
            if col == "ver":
                ver.set(val)
            elif col == "editar":
                editar.set(val);
                ver.set(ver.get() or val)
            elif col == "imprimir":
                imprimir.set(val);
                ver.set(ver.get() or val)
            elif col == "excluir":
                excluir.set(val);
                ver.set(ver.get() or val)

    def _load_permissoes_catalogo_pg(self):
        try:
            schema = get_schema()
            rows = self._fetch_all(
                f"""SELECT codigo, nome, 'Geral' AS grupo, NULL::text AS descricao FROM {schema}.permissoes_catalogo ORDER BY 2"""
            )
            grupos = {}
            for row in rows or []:
                grupo = row[2] or "Geral"
                grupos.setdefault(grupo, []).append(row)
            self._render_grupos_permissoes(grupos)
        except Exception as e:
            messagebox.showerror("Permissões", f"Erro ao carregar catálogo: {e}")

    def _render_grupos_permissoes(self, grupos: Dict[str, List[tuple]]):
        self._clear_perm_grid()
        if not grupos:
            return

        pal = self._get_palette_from_host()
        line = "#e5e7eb" if pal["mode"] == "Light" else "#2b2f33"
        head_bg = pal.get("bg2", "#ffffff")

        grupos_nomes = list(grupos.keys())
        cols = max(1, self.PERM_COLS)
        buckets = [[] for _ in range(cols)]
        for i, g in enumerate(grupos_nomes):
            buckets[i % cols].append(g)

        row_start = 0
        for col, grupos_coluna in enumerate(buckets):
            col_idx = col * 2
            r = row_start

            for grupo in grupos_coluna:
                # Cabeçalho do grupo
                box = ctk.CTkFrame(self.perm_grid, fg_color=head_bg, corner_radius=10)
                box.grid(row=r, column=col_idx, sticky="ew", padx=(6 if col == 0 else 3, 3), pady=(0, 8))
                box.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(box, text=grupo, font=ctk.CTkFont(size=14, weight="bold")).grid(
                    row=0, column=0, sticky="w", padx=10, pady=8
                )
                r += 1

                # Linha separadora
                ctk.CTkFrame(self.perm_grid, height=1, fg_color=line).grid(
                    row=r, column=col_idx, sticky="ew", padx=(6 if col == 0 else 3, 3), pady=(0, 6)
                )
                r += 1

                # Container interno
                wrap = ctk.CTkFrame(self.perm_grid, fg_color="transparent")
                wrap.grid(row=r, column=col_idx, sticky="nsew", padx=(6 if col == 0 else 3, 3))
                wrap.grid_columnconfigure(0, weight=1)
                r += 1

                # Linhas do grupo
                for item in grupos[grupo]:
                    codigo, nome, _grupo, descricao = item
                    row_frame = ctk.CTkFrame(wrap, fg_color="transparent")
                    row_frame.grid(row=wrap.grid_size()[1], column=0, sticky="ew", pady=2)
                    self._add_perm_row_pg(row_frame, codigo, nome, descricao)

            # Divisor vertical
            if col < cols - 1:
                v = ctk.CTkFrame(self.perm_grid, width=1, fg_color=line)
                v.grid(row=row_start, column=col_idx + 1, rowspan=999, sticky="ns")

    def _add_perm_row_pg(self, parent, codigo: str, nome: str, descricao: str):
        parent.grid_columnconfigure(0, weight=1)
        for i in range(1, 6):
            parent.grid_columnconfigure(i, weight=0)

        ctk.CTkLabel(parent, text=nome, anchor="w").grid(row=0, column=0, sticky="ew", padx=(10, 6))

        var_ver = ctk.BooleanVar(value=False)
        var_edit = ctk.BooleanVar(value=False)
        var_imp = ctk.BooleanVar(value=False)
        var_exc = ctk.BooleanVar(value=False)
        var_admin = ctk.BooleanVar(value=False)

        def _ensure_view():
            try:
                if var_edit.get() or var_imp.get() or var_exc.get():
                    var_ver.set(True)
            except Exception:
                pass

        # Checboxes com disable conforme suporte do DB
        cb_v = ctk.CTkCheckBox(parent, text="V", variable=var_ver, width=18)
        cb_e = ctk.CTkCheckBox(parent, text="E", variable=var_edit, width=18, command=_ensure_view)
        cb_i = ctk.CTkCheckBox(parent, text="I", variable=var_imp, width=18, command=_ensure_view)
        cb_x = ctk.CTkCheckBox(parent, text="X", variable=var_exc, width=18, command=_ensure_view)
        cb_a = ctk.CTkCheckBox(parent, text="ADM", variable=var_admin, width=38)

        cb_v.grid(row=0, column=1, padx=6)
        cb_e.grid(row=0, column=2, padx=6)
        cb_i.grid(row=0, column=3, padx=6)
        cb_x.grid(row=0, column=4, padx=6)
        cb_a.grid(row=0, column=5, padx=6)

        # desabilita colunas não suportadas
        if not getattr(self, "_perm_cols", {}).get("pode_imprimir", False):
            try:
                cb_i.configure(state="disabled")
            except Exception:
                pass
        if not getattr(self, "_perm_cols", {}).get("excluir", False):
            try:
                cb_x.configure(state="disabled")
            except Exception:
                pass
        if not getattr(self, "_perm_cols", {}).get("administrar", False):
            try:
                cb_a.configure(state="disabled")
            except Exception:
                pass

        self._boxes[codigo] = (var_ver, var_edit, var_imp, var_exc, var_admin)
        self._name2code[nome] = codigo

    def _clear_perm_grid(self):
        if not hasattr(self, "perm_grid") or not self.perm_grid.winfo_exists():
            self.perm_grid = ctk.CTkFrame(self.tab_permissoes, fg_color="transparent")
            self.perm_grid.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        for w in self.perm_grid.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

    # ---------- Aba Logs ----------
    def _build_tab_logs(self):
        pal = self._get_palette_from_host()

        logs_container = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        logs_container.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        logs_container.grid_rowconfigure(1, weight=1)
        logs_container.grid_columnconfigure(0, weight=1)

        filter_frame = CardFrame(logs_container, title="Filtros de Log", fg_color=pal["bg2"])
        filter_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        filter_inner = ctk.CTkFrame(filter_frame, fg_color="transparent")
        filter_inner.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(filter_inner, text="De:").pack(side="left", padx=(0, 6))
        self.log_ini = ctk.CTkEntry(filter_inner, placeholder_text="YYYY-MM-DD", width=110)
        self.log_ini.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(filter_inner, text="Até:").pack(side="left", padx=(0, 6))
        self.log_fim = ctk.CTkEntry(filter_inner, placeholder_text="YYYY-MM-DD", width=110)
        self.log_fim.pack(side="left", padx=(0, 10))

        self.log_busca = ctk.CTkEntry(filter_inner, placeholder_text="Buscar...", width=220)
        self.log_busca.pack(side="left", padx=(0, 10))
        self.log_busca.bind("<Return>", lambda e: self._filtrar_logs())

        ModernButton(filter_inner, "Filtrar", command=self._filtrar_logs).pack(side="left", padx=4)
        ModernButton(filter_inner, "Exportar CSV", command=self._exportar_logs_csv).pack(side="left", padx=4)
        ModernButton(filter_inner, "Limpar", command=self._limpar_filtros_logs).pack(side="left", padx=4)

        logs_table_frame = CardFrame(logs_container, title="Registros de Log", fg_color=pal["bg2"])
        logs_table_frame.grid(row=1, column=0, sticky="nsew")
        logs_table_frame.grid_columnconfigure(0, weight=1)
        logs_table_frame.grid_rowconfigure(0, weight=1)

        table_container = ctk.CTkFrame(logs_table_frame, fg_color="transparent")
        table_container.pack(fill="both", expand=True, padx=12, pady=12)
        table_container.grid_columnconfigure(0, weight=1)
        table_container.grid_rowconfigure(0, weight=1)

        cols = ("data_hora", "usuario", "acao", "pagina", "detalhe")
        self.tree_logs = ttk.Treeview(table_container, columns=cols, show="headings", selectmode="extended")
        vsb = ttk.Scrollbar(table_container, orient="vertical", command=self.tree_logs.yview)
        hsb = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree_logs.xview)
        self.tree_logs.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        headers = {"data_hora": "Data/Hora", "usuario": "Usuário", "acao": "Ação", "pagina": "Página",
                   "detalhe": "Detalhes"}
        for c in cols:
            self.tree_logs.heading(c, text=headers[c])

        self.tree_logs.column("data_hora", width=160, anchor="center")
        self.tree_logs.column("usuario", width=140, anchor="w")
        self.tree_logs.column("acao", width=140, anchor="w")
        self.tree_logs.column("pagina", width=180, anchor="w")
        self.tree_logs.column("detalhe", width=380, anchor="w")

        self.tree_logs.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

    # ---------- Aba Dashboard (placeholder) ----------
    def _build_tab_dashboard(self):
        pal = self._get_palette_from_host()
        dash_container = ctk.CTkFrame(self.tab_dashboard, fg_color="transparent")
        dash_container.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        dash_container.grid_columnconfigure((0, 1), weight=1)
        dash_container.grid_rowconfigure((0, 1), weight=1)

        CardFrame(dash_container, title="Atividade Recente", fg_color=pal["bg2"]).grid(row=0, column=0,
                                                                                       sticky="nsew", padx=6, pady=6)
        CardFrame(dash_container, title="Distribuição de Permissões", fg_color=pal["bg2"]).grid(row=0, column=1,
                                                                                                sticky="nsew", padx=6,
                                                                                                pady=6)
        CardFrame(dash_container, title="Logs por Tipo", fg_color=pal["bg2"]).grid(row=1, column=0, sticky="nsew",
                                                                                   padx=6, pady=6)
        CardFrame(dash_container, title="Usuários por Hierarquia", fg_color=pal["bg2"]).grid(row=1, column=1,
                                                                                             sticky="nsew", padx=6,
                                                                                             pady=6)

    # ---------------- Binds / Eventos ----------------
    def _setup_user_binds(self):
        if not hasattr(self, "tree"):
            return
        try:
            self.tree.configure(selectmode="browse")
        except Exception:
            pass
        for ev in ("<<TreeviewSelect>>", "<ButtonRelease-1>", "<Return>", "<Double-1>"):
            try:
                self.tree.unbind(ev)
            except Exception:
                pass
        self.tree.bind("<<TreeviewSelect>>", self._on_select_user)
        self.tree.bind("<ButtonRelease-1>", self._on_select_user)
        self.tree.bind("<Return>", self._on_select_user)
        self.tree.bind("<Double-1>", self._on_select_user)

    def _on_select_user(self, event=None):
        try:
            if not hasattr(self, "tree"):
                return
            sel = self.tree.selection()
            if not sel:
                self._novo_usuario()
                return
            item = sel[0]
            values = self.tree.item(item, "values")
            if not values:
                return
            uid = int(values[0])
            self.user_id = uid
            self._carregar_usuario(uid)
            if hasattr(self, "info_user_perm"):
                try:
                    self.info_user_perm.configure(text=f"👤 Usuário: {values[1]} (ID: {uid})")
                except Exception:
                    pass
        except Exception as e:
            messagebox.showerror("Seleção", f"Erro ao selecionar usuário: {e}")


# ============================================================
# Execução direta (teste)
# ============================================================
if __name__ == "__main__":
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Sistema de Gestão de Usuários - PostgreSQL")
    root.geometry("1280x800")


    class HostMock:
        def __init__(self, master):
            self.content_scroll = master
            self.cor_fundo = "#f8fafc"
            self.cor_borda = "#e5e7eb"
            self.cor_secundaria = "#ffffff"
            self.cor_primaria = "#2563eb"
            self.cor_texto = "#111827"
            self.cor_sucesso = "#10b981"
            self.cor_aviso = "#f59e0b"
            self.cor_perigo = "#ef4444"


    host = HostMock(root)
    page = UsuariosPage(host)
    page.pack(fill="both", expand=True)

    root.mainloop()
