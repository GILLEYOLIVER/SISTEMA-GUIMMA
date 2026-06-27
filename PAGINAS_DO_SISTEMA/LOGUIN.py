import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
import hashlib
import time
import subprocess

import customtkinter as ctk



from PAGINAS_DO_SISTEMA.UI_TREEVIEW_OPERA import instalar_cabecalho_treeview
try:
    from PIL import Image, ImageTk
except Exception:
    Image = ImageTk = None

from PAGINAS_DO_SISTEMA.ui_after_guard import (
    cancel_all_after_info,
    cancel_all_afters,
    initialize_after_guard,
    reset_tk_default_root,
)

from pathlib import Path
import sys

try:
    from licenciamento.runtime import check_application_access, open_license_app

    LICENCIAMENTO_DISPONIVEL = True
except Exception as erro_licenciamento:
    check_application_access = None
    open_license_app = None
    LICENCIAMENTO_DISPONIVEL = False
    print(f"⚠️ Licenciamento não disponível: {erro_licenciamento}")


def _licenciamento_exigido_por_ambiente() -> bool:
    valor = os.environ.get("SISTEMA_GUIMMA_LICENSE_ENFORCE", "")
    return valor.strip().lower() in {"1", "true", "yes", "sim", "on"}


def _verificar_licenca_antes_do_login(parent: tk.Misc) -> bool:
    if not LICENCIAMENTO_DISPONIVEL:
        if _licenciamento_exigido_por_ambiente():
            _mostrar_erro_centralizado(
                parent,
                "Licenciamento indisponível",
                "O módulo de licenciamento não foi encontrado.\n"
                "Reinstale o Sistema Guimma ou abra o aplicativo de licenciamento.",
            )
            return False
        return True

    try:
        decisao = check_application_access(try_online=True)
    except Exception as erro:
        _mostrar_erro_centralizado(
            parent,
            "Erro no licenciamento",
            f"Não foi possível validar a licença:\n{erro}",
        )
        return False

    if decisao.allowed:
        return True

    _mostrar_erro_centralizado(parent, decisao.title, decisao.message)
    try:
        if open_license_app is not None:
            open_license_app()
    except Exception:
        pass
    return False


def _abrir_setup_banco() -> bool:
    """Abre o configurador de banco sem reinvocar o app principal em loop."""
    exe_path = Path(sys.executable).resolve()

    # 1) Prioriza app dedicado do configurador (macOS empacotado)
    candidatos_apps = [
        Path("/Applications/CONFIGURAR_BANCO.app"),
        exe_path.parent / "CONFIGURAR_BANCO.app",
        exe_path.parent.parent / "CONFIGURAR_BANCO.app",
        exe_path.parent.parent.parent / "CONFIGURAR_BANCO.app",
        Path.cwd() / "dist" / "SistemaGuimma" / "CONFIGURAR_BANCO.app",
    ]

    for app_path in candidatos_apps:
        try:
            if app_path.is_dir():
                subprocess.Popen(["open", str(app_path)])
                return True
        except Exception as erro:
            print(f"⚠️ Falha ao abrir app do configurador ({app_path}): {erro}")

    # 2) Fallback para script python (ambiente de desenvolvimento)
    candidatos = [
        Path(__file__).resolve().parent / "SETUP_BANCO.py",
        Path(__file__).resolve().parent.parent / "packaging" / "SETUP_BANCO.py",
    ]

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidatos.extend(
            [
                Path(meipass) / "PAGINAS_DO_SISTEMA" / "SETUP_BANCO.py",
                Path(meipass) / "SETUP_BANCO.py",
            ]
        )

    for script in candidatos:
        if script.is_file():
            try:
                # Em app empacotado, sys.executable aponta para o próprio app.
                # Evita abrir o Sistema Guimma de novo em loop.
                if getattr(sys, "frozen", False):
                    py_candidates = [
                        os.environ.get("PYTHON_BIN"),
                        "python3",
                        "python",
                    ]
                    for py in py_candidates:
                        if not py:
                            continue
                        try:
                            subprocess.Popen([py, str(script)])
                            return True
                        except Exception:
                            continue
                    print("⚠️ Python externo não encontrado para abrir SETUP_BANCO.py em modo empacotado.")
                    return False

                subprocess.Popen([sys.executable, str(script)])
                return True
            except Exception as erro:
                print(f"⚠️ Falha ao abrir SETUP_BANCO.py ({script}): {erro}")
                return False
    print("⚠️ SETUP_BANCO.py não encontrado nos caminhos esperados.")
    return False


def _mostrar_erro_centralizado(parent: tk.Misc, titulo: str, mensagem: str) -> None:
    """Exibe mensagem de erro centralizada no display principal."""
    janela_aux = None
    try:
        janela_aux = tk.Toplevel(parent)
        janela_aux.withdraw()
        janela_aux.overrideredirect(True)
        janela_aux.attributes("-topmost", True)

        largura_tela = janela_aux.winfo_screenwidth()
        altura_tela = janela_aux.winfo_screenheight()
        pos_x = max((largura_tela // 2), 0)
        pos_y = max((altura_tela // 2), 0)

        janela_aux.geometry(f"1x1+{pos_x}+{pos_y}")
        janela_aux.deiconify()
        janela_aux.lift()
        janela_aux.focus_force()

        messagebox.showerror(titulo, mensagem, parent=janela_aux)
    except Exception:
        messagebox.showerror(titulo, mensagem)
    finally:
        if janela_aux is not None:
            try:
                janela_aux.destroy()
            except Exception:
                pass


def asset_path(nome_arquivo: str) -> str:
    """
    Resolve assets tanto no modo normal quanto no PyInstaller (.app).
    Mantém compatibilidade com seu layout atual:
      - imagens dentro de PAGINAS_DO_SISTEMA
    """
    # PyInstaller
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    # tenta dentro da pasta do pacote
    p1 = base / "PAGINAS_DO_SISTEMA" / nome_arquivo
    if p1.exists():
        return str(p1)
    # tenta ao lado do arquivo (caso rode solto)
    p2 = Path(__file__).resolve().parent / nome_arquivo
    if p2.exists():
        return str(p2)
    # tenta na pasta PAGINAS_DO_SISTEMA real do projeto (rodando fora do bundle)
    return str(Path(__file__).resolve().parent / nome_arquivo)



# ============================================================
# Configuração: carrega config.json e exporta OPERA_PG_DSN/OPERA_PG_SCHEMA
# ============================================================
def _carregar_config_json_e_exportar_ambiente():
    candidatos = []

    # 1) Local do app (Windows)
    appdata = os.getenv("APPDATA")
    if appdata:
        candidatos.append(os.path.join(appdata, "SistemaGuimma", "config.json"))

    # 2) Local global (macOS / Linux)
    candidatos.append("/Library/Application Support/SistemaGuimma/config.json")
    candidatos.append(os.path.expanduser("~/Library/Application Support/SistemaGuimma/config.json"))

    # 3) Local global Windows
    candidatos.append(r"C:\ProgramData\SistemaGuimma\config.json")

    # 4) Ao lado do arquivo e raiz do projeto
    aqui = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(aqui)
    candidatos.append(os.path.join(aqui, "config.json"))
    candidatos.append(os.path.join(base_dir, "config.json"))

    for caminho in candidatos:
        try:
            if os.path.isfile(caminho):
                with open(caminho, "r", encoding="utf-8") as arquivo:
                    configuracao = json.load(arquivo) or {}
                dsn = configuracao.get("pg_dsn") or configuracao.get("OPERA_PG_DSN") or configuracao.get("OPERA_PG_DSN".lower())
                esquema = configuracao.get("pg_schema") or configuracao.get("OPERA_PG_SCHEMA") or configuracao.get("OPERA_PG_SCHEMA".lower())
                if dsn:
                    os.environ["OPERA_PG_DSN"] = str(dsn)
                if esquema:
                    os.environ["OPERA_PG_SCHEMA"] = str(esquema)
                return caminho
        except Exception:
            pass
    return None


_CONFIG_PATH_ENCONTRADO = _carregar_config_json_e_exportar_ambiente()

# Importa o banco DEPOIS da configuração
from PAGINAS_DO_SISTEMA import BANCO_DE_DADOS_PG as banco_de_dados

# Importa o sistema de auditoria
try:
    from PAGINAS_DO_SISTEMA.database_logger import audit_login, set_audit_user, quick_audit_log

    AUDIT_AVAILABLE = True
    print("✅ Sistema de auditoria carregado")
except ImportError:
    AUDIT_AVAILABLE = False
    print("⚠️  Sistema de auditoria não disponível")


# ============================================================
# Aplicação
# ============================================================
class SistemaLoginModerno:
    def __init__(self, root: tk.Tk, iniciar_oculto: bool = False):
        self.root = root
        self.root.title("Sistema Guimma - Login")
        self.iniciar_oculto = bool(iniciar_oculto)

        # Treeview: cabeçalho global (cinza + hover)
        try:
            instalar_cabecalho_treeview()
        except Exception:
            pass
        if not self.iniciar_oculto:
            self.exibir_janela()

        initialize_after_guard(self, root_attr="root")

        self.cores = {
            "primary": "#2c3e50",
            "secondary": "#1abc9c",
            "success": "#27ae60",
            "danger": "#e74c3c",
            "warning": "#e67e22",
            "light": "#f8f9fa",
            "dark": "#2b2d42",
        }
        self.fonte_titulo = ("Segoe UI", 18, "bold")
        self.fonte_rotulo = ("Segoe UI", 11)
        self.fonte_entrada = ("Segoe UI", 11)
        self.fonte_botao = ("Segoe UI", 11, "bold")

        # Licenciamento: quando ativado, bloqueia antes do login.
        if not _verificar_licenca_antes_do_login(self.root):
            self.root.after(50, self.root.destroy)
            return

        # Verifica conexão e readiness do banco (sem criar nada)
        if not banco_de_dados.ready_check():
            _mostrar_erro_centralizado(
                self.root,
                "Banco não preparado",
                "Não foi possível conectar ao banco de dados.\n"
                "Rode os scripts SQL e configure a conexão pelo configurador de banco.",
            )
            abriu_setup = _abrir_setup_banco()
            if abriu_setup:
                _mostrar_erro_centralizado(
                    self.root,
                    "Configuração necessária",
                    "O configurador de banco foi aberto.\n"
                    "Conclua a configuração e abra o Sistema Guimma novamente.",
                )
            else:
                _mostrar_erro_centralizado(
                    self.root,
                    "Configuração necessária",
                    "Não foi possível abrir automaticamente o configurador de banco.\n"
                    "Abra manualmente o SETUP_BANCO.py e tente novamente.",
                )

            # Encerra de forma limpa para evitar comportamento de 'crash/reopen loop' no macOS.
            self.root.after(50, self.root.destroy)
            return

        self._configurar_interface()
        try:
            self.refresh_texts()
        except Exception:
            pass

        self.root.bind("<Return>", lambda evento: self.entrar_no_sistema())
        try:
            self.refresh_texts()
        except Exception:
            pass


    def exibir_janela(self):
        try:
            self.root.state("zoomed")
        except Exception:
            self.root.geometry("1024x700")

    def _registrar_auditoria_login(self, usuario: str, sucesso: bool, detalhes: str = ""):
        """Registra tentativa de login no sistema de auditoria"""
        if not AUDIT_AVAILABLE:
            return

        try:
            acao = "Login bem-sucedido" if sucesso else "Tentativa de login falhou"
            quick_audit_log(acao, "Autenticação", f"Usuário: {usuario} | {detalhes}")
        except Exception as e:
            print(f"⚠️  Erro no registro de auditoria: {e}")

    def entrar_no_sistema(self):
        """Processa login e abre o sistema normalmente (versão final corrigida)."""

        usuario_digitado = self.entrada_usuario.get().strip()
        senha_digitada = self.entrada_senha.get().strip()

        if not usuario_digitado or not senha_digitada:
            messagebox.showwarning("Atenção", "Preencha usuário e senha.", parent=self.root)
            return

        from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn_cursor

        try:
            with get_conn_cursor() as (con, cursor):

                # ============ BUSCA O USUÁRIO ============
                cursor.execute("""
                    SELECT 
                        u.id, 
                        u.usuario, 
                        u.senha_hash, 
                        u.hierarquia, 
                        u.ativo, 
                        u.email,
                        COALESCE(up.tema_nome, u.tema_preferido, 'Noite Urbana') AS tema_preferido
                    FROM opera.usuarios u
                    LEFT JOIN opera.usuario_preferencias up ON u.id = up.usuario_id
                    WHERE u.usuario = %s
                """, (usuario_digitado,))

                linha = cursor.fetchone()

                if not linha:
                    self._registrar_auditoria_login(usuario_digitado, False, "Usuário não encontrado")
                    messagebox.showerror("Falha no login", "Usuário não encontrado.", parent=self.root)
                    return

                user = {
                    "id": linha[0],
                    "usuario": linha[1],
                    "senha_hash": linha[2],
                    "hierarquia": linha[3],
                    "ativo": linha[4],
                    "email": linha[5],
                    "tema": linha[6],
                }

                if not user["ativo"]:
                    self._registrar_auditoria_login(usuario_digitado, False, "Usuário inativo")
                    messagebox.showerror("Acesso negado", "Usuário inativo.", parent=self.root)
                    return

                # ============ VALIDA SENHA ============
                senha_ok = False
                senha_hash_banco = (user["senha_hash"] or "").strip()

                # bcrypt
                try:
                    import bcrypt
                    if senha_hash_banco.startswith("$2"):
                        if bcrypt.checkpw(senha_digitada.encode(), senha_hash_banco.encode()):
                            senha_ok = True
                except:
                    pass

                # validar_senha() do banco
                if not senha_ok:
                    cursor.execute("SELECT opera.validar_senha(%s, %s)",
                                   (usuario_digitado, senha_digitada))
                    r = cursor.fetchone()
                    if r and r[0] is True:
                        senha_ok = True

                # SHA256 antigo
                if not senha_ok:
                    import hashlib
                    salt = "sistema_profissional_v2.2"
                    if hashlib.sha256((salt + senha_digitada).encode()).hexdigest() == senha_hash_banco:
                        senha_ok = True

                if not senha_ok:
                    self._registrar_auditoria_login(usuario_digitado, False, "Senha incorreta")
                    messagebox.showerror("Falha no login", "Senha incorreta.", parent=self.root)
                    return

                # ============ REGISTRA ÚLTIMO LOGIN ============
                cursor.execute("UPDATE opera.usuarios SET ultimo_login = NOW() WHERE id = %s",
                               (user["id"],))

            # ============ REGISTRA AUDITORIA DE SUCESSO ============
            self._registrar_auditoria_login(usuario_digitado, True, f"Hierarquia: {user['hierarquia']}")

            # ============ CONFIGURA USUÁRIO NO SISTEMA DE AUDITORIA ============
            if AUDIT_AVAILABLE:
                try:
                    set_audit_user(usuario_digitado)
                    print(f"✅ Usuário de auditoria definido: {usuario_digitado}")
                except Exception as e:
                    print(f"⚠️  Não foi possível configurar usuário de auditoria: {e}")

            # ============================================
            # SUCESSO — AGORA PODE FECHAR A JANELA DE LOGIN
            # E ABRIR O MENU/SPLASH NORMALMENTE
            # ============================================
            print(f"[LOGIN] Login OK → Abrindo sistema para {usuario_digitado}...")

            self.root.destroy()

            # Caso esteja em modo troca de usuário
            if getattr(self, "modo_troca", False) and callable(getattr(self, "callback_troca", None)):
                self.callback_troca(
                    user["id"],
                    user["usuario"],
                    user["hierarquia"],
                    user["tema"]
                )
                return

            # Abre o sistema normalmente
            self._abrir_sistema_principal_apos_login(
                user_id=user["id"],
                usuario=user["usuario"],
                hierarquia=user["hierarquia"],
                tema_preferido=user["tema"]
            )

        except Exception as e:
            self._registrar_auditoria_login(usuario_digitado, False, f"Erro: {str(e)}")
            print("[LOGIN ERRO]", e)
            messagebox.showerror("Erro de login", f"Erro ao processar login:\n{e}", parent=self.root)

    def _salvar_tema_preferido_configuracoes(self, tema_preferido):
        """
        Salva o tema preferido do usuário nas configurações locais
        para que o sistema principal possa carregá-lo
        """
        try:
            # Tenta salvar nas configurações do sistema
            config_path = None
            appdata = os.getenv("APPDATA")
            if appdata:
                config_path = os.path.join(appdata, "Opera", "user_settings.json")

            if config_path:
                # Cria diretório se não existir
                os.makedirs(os.path.dirname(config_path), exist_ok=True)

                # Carrega configurações existentes ou cria novas
                settings = {}
                if os.path.exists(config_path):
                    try:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            settings = json.load(f)
                    except:
                        settings = {}

                # Atualiza tema preferido
                settings["theme"] = tema_preferido
                settings["last_user_theme"] = tema_preferido
                settings["last_login"] = time.strftime("%Y-%m-%d %H:%M:%S")

                # Salva configurações
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)

                print(f"[LOGIN] ✅ Tema '{tema_preferido}' salvo nas configurações: {config_path}")

        except Exception as e:
            print(f"[LOGIN] ⚠️ Não foi possível salvar tema nas configurações: {e}")

    def _abrir_sistema_principal_apos_login(self, user_id, usuario, hierarquia, tema_preferido="Noite Urbana",
                                            modo_callback=False):
        """Abre o MENU diretamente (sem splash). O splash já roda no BOOT."""
        print(f"[LOGIN] Abrindo sistema para: {usuario} (Tema: {tema_preferido})")

        try:
            # Fecha janela de login
            if hasattr(self, "root") and self.root:
                try:
                    self._fechando = True
                    cancel_all_afters(self, root_attr="root")
                    cancel_all_after_info(self, root_attr="root")
                    self.root.quit()
                    self.root.destroy()
                    reset_tk_default_root()
                except Exception:
                    pass

            # Abre direto o MENU
            from MENU_PRINCIPAL import OperaMenuApp
            app = OperaMenuApp(
                usuario_id=int(user_id),
                usuario_nome=usuario,
                usuario_hierarquia=hierarquia,
                tema_preferido=tema_preferido
            )
            app.mainloop()

        except Exception as erro:
            print(f"[LOGIN] Erro ao abrir MENU: {erro}")
            import traceback
            traceback.print_exc()
            try:
                from tkinter import messagebox
                messagebox.showerror("Erro", f"Falha ao iniciar o sistema:\n{erro}")
            except Exception:
                pass

    def abrir_modo_troca(self, callback):
        """
        Abre o login em modo de troca de usuário com callback robusto.
        O callback recebe (user_id, usuario, hierarquia, tema_preferido).
        """
        print("[LOGIN] Configurando modo troca de usuário")
        self.callback_troca = callback
        self.modo_troca = True

        # Garante que a janela de login está visível e com foco
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.entrada_usuario.delete(0, tk.END)
            self.entrada_senha.delete(0, tk.END)
            self.entrada_usuario.focus_set()
            print("[LOGIN] Tela de login preparada para troca")
        except Exception as e:
            print(f"[LOGIN] Aviso ao preparar modo troca: {e}")

    def trocar_usuario_via_login(self, callback):
        """
        Método para ser chamado pelo MENU_PRINCIPAL para trocar usuário
        usando a tela de login completa.
        """
        print("[LOGIN] Iniciando troca de usuário via login externo")

        # Configura o modo troca e o callback
        self.callback_troca = callback
        self.modo_troca = True

        # Prepara a janela de login
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.entrada_usuario.delete(0, tk.END)
            self.entrada_senha.delete(0, tk.END)
            self.entrada_usuario.focus_set()
            print("[LOGIN] Tela de login preparada para troca de usuário")
        except Exception as e:
            print(f"[LOGIN] Erro ao preparar tela de login: {e}")

    def _abrir_sistema_principal(self, user_id: int, usuario: str, hierarquia: str = "Padrão",
                                 tema_preferido: str = "Noite Urbana"):
        """Abre o MENU diretamente (sem splash)."""
        print(f"[LOGIN] Abrindo sistema para: {usuario} (Tema: {tema_preferido})")

        try:
            if hasattr(self, "root") and self.root:
                try:
                    self.root.quit()
                    self.root.destroy()
                except Exception:
                    pass

            from MENU_PRINCIPAL import OperaMenuApp
            app = OperaMenuApp(
                usuario_id=int(user_id),
                usuario_nome=usuario,
                usuario_hierarquia=hierarquia,
                tema_preferido=tema_preferido
            )
            app.mainloop()

        except Exception as erro:
            print(f"[LOGIN] Erro crítico: {erro}")
            import traceback
            traceback.print_exc()

    # ----------------------
    # Helpers de banco
    # ----------------------
    def _buscar_um(self, sql, parametros=()):
        return banco_de_dados.fetch_one(sql, parametros)

    def _buscar_todos(self, sql, parametros=()):
        return banco_de_dados.fetch_all(sql, parametros)

    def _executar(self, sql, parametros=()):
        return banco_de_dados.execute(sql, parametros)

    # ----------------------
    # Detecção de Caps Lock
    # ----------------------
    def _capslock_ativo_windows(self) -> bool:
        try:
            import ctypes
            return bool(ctypes.windll.user32.GetKeyState(0x14) & 1)
        except Exception:
            return False

    def _detectar_capslock_por_evento(self, evento=None):
        """
        Atualiza aviso de Caps Lock.
        Prioriza leitura real no Windows e usa fallback por tecla digitada.
        """
        caps_ativo = False

        # Método real para Windows
        if os.name == "nt":
            caps_ativo = self._capslock_ativo_windows()
        else:
            # fallback simples
            if evento is not None:
                tecla = getattr(evento, "keysym", "") or ""
                caractere = getattr(evento, "char", "") or ""
                shift_pressionado = bool(getattr(evento, "state", 0) & 0x0001)

                if len(caractere) == 1 and caractere.isalpha():
                    if caractere.isupper() and not shift_pressionado:
                        caps_ativo = True
                    elif caractere.islower() and shift_pressionado:
                        caps_ativo = True
                    else:
                        caps_ativo = False

        self._mostrar_aviso_capslock(caps_ativo)

    def _mostrar_aviso_capslock(self, ativo: bool):
        if hasattr(self, "label_capslock") and self.label_capslock:
            if ativo:
                self.label_capslock.configure(text="Caps Lock ativo")
            else:
                self.label_capslock.configure(text="")

    # ----------------------
    # Interface do usuário
    # ----------------------
    def _configurar_interface(self):
        # --- Configuração do cursor piscante ---
        self.root.option_add('*Entry.insertOffTime', 300)
        self.root.option_add('*Entry.insertOnTime', 600)
        self.root.option_add('*Entry.insertWidth', 2)
        self.root.option_add('*Entry.insertBackground', '#2c3e50')

        caminho_fundo = asset_path("FUNDO_LOGUIN.jpg")
        caminho_icone = asset_path("ICONE_SISTEMA.png")

        largura_tela = self.root.winfo_screenwidth()
        altura_tela = self.root.winfo_screenheight()

        # Fundo
        self.root.configure(bg="#f5f7fb")
        if Image and os.path.isfile(caminho_fundo):
            try:
                imagem = Image.open(caminho_fundo).resize((largura_tela, altura_tela))
                self._imagem_fundo = ImageTk.PhotoImage(imagem)
                rotulo_fundo = tk.Label(self.root, image=self._imagem_fundo, borderwidth=0)
                rotulo_fundo.place(x=0, y=0, relwidth=1, relheight=1)
                rotulo_fundo.lower()
            except Exception:
                pass

        # ============================================================
        # CARTÃO CENTRAL (largura +40%, altura +60%)
        # ============================================================
        largura_base = 360
        altura_base = 520
        nova_largura = int(largura_base * 1.4)
        nova_altura = int(altura_base * 1.6)

        x = (largura_tela - nova_largura) // 2
        y = (altura_tela - nova_altura) // 3

        cartao = tk.Frame(
            self.root,
            bg="white",
            highlightthickness=1,
            highlightbackground="#dfe4ea"
        )
        cartao.place(x=x, y=y, width=nova_largura, height=nova_altura)

        # wrap = conteúdo (título, campos, botão)
        wrap = tk.Frame(cartao, bg="white")
        wrap.pack(fill="both", expand=True, padx=36, pady=(32, 4))

        # ============================================================
        # ÍCONE DO SISTEMA APENAS NO TOPO
        # ============================================================
        self._icone_sistema = None
        if Image and os.path.isfile(caminho_icone):
            try:
                imagem_icone = Image.open(caminho_icone)
                tamanho_icone = min(int(nova_largura * 0.36), 160)
                imagem_icone = imagem_icone.resize((tamanho_icone, tamanho_icone))
                self._icone_sistema = ImageTk.PhotoImage(imagem_icone)
            except Exception as erro:
                print("[AVISO] Falha ao carregar ícone do sistema:", erro)
        else:
            print("[AVISO] Arquivo ICONE_SISTEMA.png não encontrado no diretório atual.")

        if self._icone_sistema:
            tk.Label(
                wrap,
                image=self._icone_sistema,
                bg="white"
            ).pack(pady=(6, 10))
        else:
            tk.Label(
                wrap,
                text="🔐",
                font=("Arial", 48),
                bg="white",
                fg=self.cores["primary"]
            ).pack(pady=(6, 10))

        tk.Label(
            wrap,
            text="ACESSO AO SISTEMA",
            font=("Segoe UI", 26, "bold"),
            bg="white",
            fg=self.cores["primary"]
        ).pack(pady=(0, 18))

        formulario = tk.Frame(wrap, bg="white")
        formulario.pack(fill="x")

        # ============================================================
        # Campos
        # ============================================================
        tk.Label(
            formulario,
            text="Usuário",
            font=("Segoe UI", 14),
            bg="white",
            fg=self.cores["dark"]
        ).pack(anchor="w", pady=(2, 0))
        self.entrada_usuario = tk.Entry(
            formulario,
            font=("Segoe UI", 15),
            relief="flat",
            bd=1,
            bg="white",
            fg=self.cores["dark"],
            insertbackground=self.cores["primary"],
            insertwidth=2,
            takefocus=1
        )
        self.entrada_usuario.configure(
            highlightthickness=1,
            highlightbackground="#dfe4ea",
            highlightcolor=self.cores["secondary"]
        )
        self.entrada_usuario.pack(fill="x", pady=(0, 12), ipady=8)

        tk.Label(
            formulario,
            text="Senha",
            font=("Segoe UI", 14),
            bg="white",
            fg=self.cores["dark"]
        ).pack(anchor="w", pady=(2, 0))
        self.entrada_senha = tk.Entry(
            formulario,
            font=("Segoe UI", 15),
            show="•",
            relief="flat",
            bd=1,
            bg="white",
            fg=self.cores["dark"],
            insertbackground=self.cores["primary"],
            insertwidth=2,
            takefocus=1
        )
        self.entrada_senha.configure(
            highlightthickness=1,
            highlightbackground="#dfe4ea",
            highlightcolor=self.cores["secondary"]
        )
        self.entrada_senha.pack(fill="x", pady=(0, 4), ipady=8)

        # ============================================================
        # Aviso de Caps Lock
        # ============================================================
        self.label_capslock = tk.Label(
            formulario,
            text="",
            font=("Segoe UI", 11, "bold"),
            bg="white",
            fg=self.cores["warning"],
            anchor="w"
        )
        self.label_capslock.pack(fill="x", pady=(0, 8))

        self.entrada_senha.bind("<KeyRelease>", self._detectar_capslock_por_evento, add="+")
        self.entrada_senha.bind("<FocusIn>", self._detectar_capslock_por_evento, add="+")
        self.entrada_senha.bind("<FocusOut>", lambda evento: self._mostrar_aviso_capslock(False), add="+")

        # ============================================================
        # Checkbox e links
        # ============================================================
        self.var_ver_senha = tk.BooleanVar(value=False)
        checkbox = tk.Checkbutton(
            formulario,
            text="Mostrar senha",
            variable=self.var_ver_senha,
            command=self._alternar_senha,
            bg="white",
            fg=self.cores["dark"],
            font=("Segoe UI", 13),
            activebackground="white",
            cursor="arrow"
        )
        checkbox.pack(anchor="w", pady=(0, 12))

        links = tk.Frame(formulario, bg="white")
        links.pack(fill="x", pady=(0, 14))

        def _criar_link(parent, texto, cor, comando):
            rotulo = tk.Label(
                parent,
                text=texto,
                bg="white",
                fg=cor,
                cursor="hand2",
                font=("Segoe UI", 13)
            )
            rotulo.bind("<Button-1>", lambda evento: comando())
            return rotulo

        _criar_link(
            links,
            "Esqueceu o login?",
            self.cores["dark"],
            self._listar_usuarios
        ).pack(side="right")
        _criar_link(
            links,
            "Esqueceu a senha?",
            self.cores["danger"],
            self._mostrar_dica_senha
        ).pack(side="right", padx=(0, 14))

        # ============================================================
        # Botão ENTRAR (hover claro + texto escuro + mãozinha)
        # ============================================================
        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except Exception:
            pass

        estilo.configure(
            "Opera.TButton",
            font=("Segoe UI", 17, "bold"),
            padding=(16, 10),
            foreground="white",
            background=self.cores["primary"],
            borderwidth=0,
        )

        estilo.map(
            "Opera.TButton",
            background=[
                ("active", "#ecf0f1"),
                ("pressed", self.cores["secondary"]),
                ("disabled", "#95a5a6"),
            ],
            foreground=[
                ("active", self.cores["primary"]),
                ("pressed", "white"),
                ("disabled", "#bdc3c7"),
            ]
        )

        botao_entrar = ttk.Button(
            wrap,
            text="ENTRAR",
            style="Opera.TButton",
            command=self.entrar_no_sistema,
            cursor="hand2",
            takefocus=1,
        )
        botao_entrar.pack(fill="x", pady=(10, 4))

        # ============================================================
        # Foco e cursor piscante
        # ============================================================
        def _forcar_foco():
            try:
                self.root.focus_force()
                self.entrada_usuario.focus_set()
                self.entrada_usuario.icursor(tk.END)
                self.root.update_idletasks()
            except Exception:
                pass

        self.root.bind("<Map>", lambda evento: self._agendar_after(50, _forcar_foco))
        self._agendar_after(250, _forcar_foco)

        self.entrada_usuario.bind("<Return>", lambda evento: self.entrar_no_sistema())
        self.entrada_senha.bind("<Return>", lambda evento: self.entrar_no_sistema())

        self.entrada_usuario.bind("<FocusIn>", lambda evento: self.root.config(cursor="xterm"))
        self.entrada_senha.bind("<FocusIn>", lambda evento: self.root.config(cursor="xterm"))
        self.entrada_usuario.bind("<FocusOut>", lambda evento: self.root.config(cursor="arrow"))
        self.entrada_senha.bind("<FocusOut>", lambda evento: self.root.config(cursor="arrow"))

    def _alternar_senha(self):
        self.entrada_senha.config(show="" if self.var_ver_senha.get() else "•")
        self._detectar_capslock_por_evento()

    # ----------------------
    # Ações auxiliares
    # ----------------------
    def _listar_usuarios(self):
        """Lista usuários e suas hierarquias, permite selecionar com duplo clique."""
        try:
            usuarios = self._buscar_todos(
                "SELECT usuario, COALESCE(hierarquia,'') AS hierarquia FROM opera.usuarios ORDER BY usuario"
            )
        except Exception as erro:
            messagebox.showerror("Erro", f"Não foi possível listar usuários:\n{erro}", parent=self.root)
            return

        janela = tk.Toplevel(self.root)
        janela.title("Usuários cadastrados")
        janela.transient(self.root)
        janela.grab_set()

        tk.Label(janela, text="Usuários no sistema:", font=self.fonte_rotulo).pack(pady=6, padx=10, anchor="w")

        frame = tk.Frame(janela)
        frame.pack(padx=10, pady=(0, 10), fill="both", expand=True)

        scrollbar_y = tk.Scrollbar(frame, orient="vertical")
        lista = tk.Listbox(frame, width=50, height=12, yscrollcommand=scrollbar_y.set, activestyle="dotbox")
        scrollbar_y.config(command=lista.yview)
        lista.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")

        for usuario_info in usuarios or []:
            usuario = usuario_info.get("usuario", "")
            hierarquia = usuario_info.get("hierarquia", "") or "sem perfil"
            lista.insert(tk.END, f"{usuario}  ({hierarquia})")

        def _aplicar_selecao(*args):
            selecao = lista.curselection()
            if not selecao:
                return
            linha_usuario = lista.get(selecao[0])
            usuario_selecionado = linha_usuario.split(" (")[0].strip()
            try:
                self.entrada_usuario.delete(0, tk.END)
                self.entrada_usuario.insert(0, usuario_selecionado)
                self.entrada_senha.focus_set()
            except Exception:
                pass
            janela.destroy()

        lista.bind("<Double-Button-1>", _aplicar_selecao)
        lista.bind("<Return>", _aplicar_selecao)

        botoes = tk.Frame(janela)
        botoes.pack(padx=10, pady=(0, 10), fill="x")
        tk.Button(botoes, text="Selecionar", command=_aplicar_selecao).pack(side="right")
        tk.Button(botoes, text="Fechar", command=janela.destroy).pack(side="right", padx=(0, 8))

        janela.update_idletasks()
        largura_janela, altura_janela = janela.winfo_reqwidth(), janela.winfo_reqheight()
        largura_tela, altura_tela = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x = (largura_tela - largura_janela) // 2
        y = (altura_tela - altura_janela) // 3
        janela.geometry(f"{largura_janela}x{altura_janela}+{x}+{y}")
        janela.focus_force()

    def _mostrar_dica_senha(self):
        usuario = (self.entrada_usuario.get() or "").strip()
        if not usuario:
            messagebox.showinfo("Dica de senha", "Digite o usuário primeiro.", parent=self.root)
            return
        try:
            linha = self._buscar_um(
                "SELECT COALESCE(dica_senha,'') AS dica_senha FROM opera.usuarios WHERE usuario = %s",
                (usuario,),
            )
            dica = (linha or {}).get("dica_senha") or ""
        except Exception:
            dica = ""
        if not dica:
            messagebox.showinfo("Dica de senha", "Nenhuma dica cadastrada para este usuário.", parent=self.root)
        else:
            messagebox.showinfo("Dica de senha", str(dica), parent=self.root)

    def _registrar_log(self, usuario, acao, detalhe=None):
        try:
            if detalhe is None:
                self._executar(
                    "INSERT INTO opera.usuario_logs (usuario, acao) VALUES (%s, %s)",
                    (usuario, acao),
                )
            else:
                import json as json_module
                self._executar(
                    "INSERT INTO opera.usuario_logs (usuario, acao, detalhe) VALUES (%s, %s, %s)",
                    (usuario, acao, json_module.dumps(detalhe, ensure_ascii=False)),
                )
        except Exception:
            pass

    # ----------------------
    # Fechamentos
    # ----------------------
    def ao_fechar(self):
        if getattr(self, "_fechando", False):
            return
        self._fechando = True
        try:
            cancel_all_afters(self, root_attr="root")
            cancel_all_after_info(self, root_attr="root")
        except Exception:
            pass
        try:
            for widget in self.root.winfo_children():
                try:
                    import tkinter as tk_module
                    if isinstance(widget, tk_module.Toplevel) and widget.winfo_exists():
                        widget.destroy()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if self.root and self.root.winfo_exists():
                self.root.destroy()
        except Exception:
            pass

    def fechar_aplicacao(self):
        """Compatibilidade: método chamado por menus externos."""
        try:
            cancel_all_afters(self, root_attr="root")
            cancel_all_after_info(self, root_attr="root")
        except Exception:
            pass
        try:
            for widget in self.root.winfo_children():
                try:
                    import tkinter as tk_module
                    if isinstance(widget, tk_module.Toplevel) and widget.winfo_exists():
                        widget.destroy()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if self.root and self.root.winfo_exists():
                self.root.destroy()
        except Exception:
            pass


# ============================================================
# Inicialização
# ============================================================
    _I18N_MAP = {'en_US': {'Sistema Guimma - Login': 'Sistema Guimma - Login', 'ACESSO AO SISTEMA': 'SYSTEM ACCESS', 'Usuário': 'User', 'Senha': 'Password', 'Mostrar senha': 'Show password', 'ENTRAR': 'LOGIN', 'Usuários no sistema:': 'Users in the system:', 'Selecionar': 'Select', 'Fechar': 'Close', 'Usuários cadastrados': 'Registered users', 'Caps Lock ativo': 'Caps Lock is on', 'Atenção': 'Attention', 'Preencha usuário e senha.': 'Enter username and password.', 'Falha no login': 'Login failed', 'Usuário não encontrado.': 'User not found.', 'Acesso negado': 'Access denied', 'Usuário inativo.': 'Inactive user.', 'Senha incorreta.': 'Incorrect password.', 'Erro': 'Error', 'Falha ao iniciar o sistema:\n{erro}': 'Failed to start the system:\n{erro}', 'Banco não preparado': 'Database not ready', 'Configuração necessária': 'Configuration required'}, 'es_ES': {'Sistema Guimma - Login': 'Sistema Guimma - Inicio de sesión', 'ACESSO AO SISTEMA': 'ACCESO AL SISTEMA', 'Usuário': 'Usuario', 'Senha': 'Contraseña', 'Mostrar contraseña': 'Mostrar contraseña', 'Mostrar senha': 'Mostrar contraseña', 'ENTRAR': 'INGRESAR', 'Usuários no sistema:': 'Usuarios en el sistema:', 'Selecionar': 'Seleccionar', 'Fechar': 'Cerrar', 'Usuários cadastrados': 'Usuarios registrados', 'Caps Lock ativo': 'Bloq Mayús activo', 'Atenção': 'Atención', 'Preencha usuário e senha.': 'Ingrese usuario y contraseña.', 'Falha no login': 'Error de inicio de sesión', 'Usuário não encontrado.': 'Usuario no encontrado.', 'Acesso negado': 'Acceso denegado', 'Usuário inativo.': 'Usuario inactivo.', 'Senha incorreta.': 'Contraseña incorrecta.', 'Erro': 'Error', 'Banco não preparado': 'Base de datos no preparada', 'Configuração necesaria': 'Configuración necesaria', 'Configuração necessária': 'Configuración necesaria'}}

    def _get_idioma_atual(self):
        try:
            if getattr(self, "sistema", None) is not None:
                return getattr(self.sistema, "idioma_atual", "pt_BR") or "pt_BR"
        except Exception:
            pass
        return getattr(self, "idioma_atual", "pt_BR") or "pt_BR"

    def _canonical_i18n_text(self, text):
        if text is None:
            return text
        s = str(text)
        maps = getattr(self, "_I18N_MAP", {}) or {}
        if s in maps.get("pt_BR", {}):
            return s
        for _lang, table in maps.items():
            for pt_key, translated in table.items():
                if s == translated:
                    return pt_key
        return s

    def _translate_i18n_text(self, text):
        if text is None:
            return text
        idioma = self._get_idioma_atual()
        maps = getattr(self, "_I18N_MAP", {}) or {}
        canonical = self._canonical_i18n_text(text)
        return maps.get(idioma, {}).get(canonical, canonical)

    def _translate_i18n_values(self, values):
        if not isinstance(values, (list, tuple)):
            return values
        return [self._translate_i18n_text(v) for v in values]

    def _refresh_widget_i18n(self, widget):
        try:
            if hasattr(widget, "cget"):
                try:
                    text = widget.cget("text")
                    if isinstance(text, str) and text:
                        new_text = self._translate_i18n_text(text)
                        if new_text != text:
                            widget.configure(text=new_text)
                except Exception:
                    pass

                try:
                    placeholder = widget.cget("placeholder_text")
                    if isinstance(placeholder, str) and placeholder:
                        new_placeholder = self._translate_i18n_text(placeholder)
                        if new_placeholder != placeholder:
                            widget.configure(placeholder_text=new_placeholder)
                except Exception:
                    pass

                try:
                    values = widget.cget("values")
                    if isinstance(values, (list, tuple)) and values:
                        current = None
                        try:
                            current = widget.get()
                        except Exception:
                            current = None
                        translated_values = self._translate_i18n_values(list(values))
                        widget.configure(values=translated_values)
                        if current:
                            widget.set(self._translate_i18n_text(current))
                except Exception:
                    pass

            if isinstance(widget, ttk.Treeview):
                try:
                    for col in widget["columns"]:
                        info = widget.heading(col)
                        heading_text = info.get("text", "")
                        if heading_text:
                            widget.heading(col, text=self._translate_i18n_text(heading_text))
                except Exception:
                    pass

            for child in widget.winfo_children():
                self._refresh_widget_i18n(child)
        except Exception:
            pass

    def refresh_texts(self):
        try:
            target = getattr(self, "root", None) or self
            self._refresh_widget_i18n(target)
        except Exception:
            pass

        try:
            if hasattr(self, "root") and self.root:
                self.root.title(self._translate_i18n_text(self.root.title()))
        except Exception:
            pass

        try:
            if hasattr(self, "PAGE_TITLE"):
                self.PAGE_TITLE = self._translate_i18n_text(self.PAGE_TITLE)
        except Exception:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    aplicacao = SistemaLoginModerno(root)
    root.protocol("WM_DELETE_WINDOW", aplicacao.ao_fechar)
    root.mainloop()

#15/12/2025
