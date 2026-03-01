# tema_database.py
# Gerencia a persistência de temas usando o banco principal do OPERA.

import json
from typing import Any, Dict, Optional

import psycopg2

try:  # Preferir conexões utilitárias do sistema
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema
except Exception:  # Fallback controlado
    get_conn = None

    def get_schema() -> str:
        return "opera"


def _sanitize_palette(paleta: Dict[str, Any]) -> Dict[str, str]:
    """Normaliza valores de paleta para o formato #RRGGBB garantindo segurança."""

    segura: Dict[str, str] = {}
    for chave, valor in (paleta or {}).items():
        if not isinstance(valor, str):
            continue
        cor = valor.strip().upper()
        if not cor.startswith("#"):
            continue
        hex_part = cor.lstrip("#")
        if len(hex_part) >= 6:
            hex_part = hex_part[:6]
        else:
            continue
        try:
            int(hex_part, 16)
            segura[chave] = f"#{hex_part}"
        except Exception:
            continue
    return segura


class DatabaseTemaManager:
    """Carregamento e salvamento de temas do usuário."""

    def __init__(self, app: Optional[Any] = None):
        self.app = app
        self.user_id = self._extract_user_id(app)

    def _resolve_user_id(self, override: Optional[int] = None) -> Optional[int]:
        """Preserva IDs zero e prioriza overrides explícitos."""

        if override is None:
            return self.user_id
        return override

    @staticmethod
    def _extract_user_id(app: Optional[Any]) -> Optional[int]:
        if not app:
            return None

        for attr in ("usuario_id", "user_id"):
            if hasattr(app, attr):
                val = getattr(app, attr)
                if val is not None:
                    return val

        um = getattr(app, "user_manager", None)
        if um:
            for attr in ("usuario_id", "user_id"):
                if hasattr(um, attr):
                    val = getattr(um, attr)
                    if val is not None:
                        return val

            usuario = getattr(um, "usuario", None) or getattr(um, "user", None)
            if usuario:
                if hasattr(usuario, "get"):
                    val = usuario.get("id")
                    if val is not None:
                        return val
                elif hasattr(usuario, "id"):
                    return usuario.id

        return None

    def get_connection(self):
        """Obter conexão com o banco usando a infraestrutura do sistema."""
        if callable(get_conn):
            try:
                return get_conn()
            except Exception as exc:  # pragma: no cover - apenas log
                print(f"❌ Erro ao obter conexão integrada: {exc}")

        try:  # fallback manual
            return psycopg2.connect(
                host="localhost",
                database="BANCO_OPERA",
                user="postgres",
                password="sua_senha",
                port="5432",
            )
        except Exception as exc:  # pragma: no cover
            print(f"❌ Erro de conexão com banco: {exc}")
            return None

    def carregar_preferencias_usuario(self, user_id: Optional[int] = None) -> Optional[Dict]:
        """Carrega preferências (tema e personalizados) do usuário."""

        user_id = self._resolve_user_id(user_id)
        if user_id is None:
            print("⚠️ Nenhum user_id fornecido, usando fallback")
            return self._get_fallback_settings()

        conn = self.get_connection()
        if not conn:
            print("❌ Não foi possível conectar ao banco")
            return self._get_fallback_settings()

        schema = get_schema() if callable(get_schema) else "opera"
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        COALESCE(up.tema_nome, u.tema_preferido, 'Noite Urbana') AS tema_nome,
                        up.usar_tema_personalizado,
                        up.tema_personalizado
                    FROM {schema}.usuarios u
                    LEFT JOIN {schema}.usuario_preferencias up ON up.usuario_id = u.id
                    WHERE u.id = %s
                    """,
                    (user_id,),
                )

                row = cursor.fetchone()
                if not row:
                    print(f"📝 Criando preferências padrão para usuário {user_id}")
                    return self._criar_preferencias_padrao(user_id)

                (
                    tema_nome,
                    usar_tema_personalizado,
                    tema_personalizado_json,
                ) = row

                custom_themes: Dict[str, Dict[str, str]] = {}
                if tema_personalizado_json:
                    try:
                        carregado = json.loads(tema_personalizado_json) or {}
                        if isinstance(carregado, dict):
                            custom_themes = {
                                nome: _sanitize_palette(pal) for nome, pal in carregado.items()
                                if isinstance(pal, dict)
                            }
                    except Exception as exc:
                        print(f"⚠️ Erro ao carregar temas personalizados: {exc}")

                # Carrega os temas da tabela dedicada
                cursor.execute(
                    f"""
                    SELECT nome_tema, cores_tema
                    FROM {schema}.usuario_temas_personalizados
                    WHERE usuario_id = %s
                    ORDER BY atualizado_em DESC
                    """,
                    (user_id,),
                )
                for nome, cores in cursor.fetchall() or []:
                    try:
                        pal = cores if isinstance(cores, dict) else json.loads(cores)
                        custom_themes[nome] = _sanitize_palette(pal) if isinstance(pal, dict) else {}
                    except Exception:
                        continue

                settings = {
                    "theme": tema_nome or "Noite Urbana",
                    "custom_themes": custom_themes,
                    "excluded_default_themes": [],
                    "usar_tema_personalizado": bool(usar_tema_personalizado),
                    # Flags não existem em todos os bancos; mantemos no contexto local
                    "aplicar_dashboard": True,
                    "aplicar_tabelas": True,
                    "aplicar_login": True,
                }

                print(f"✅ Preferências carregadas para usuário {user_id}: {settings['theme']}")
                return settings
        except Exception as exc:
            print(f"❌ Erro ao carregar preferências: {exc}")
            return self._get_fallback_settings()
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def salvar_preferencias_usuario(self, settings: Dict, user_id: Optional[int] = None) -> bool:
        """Salva preferências do usuário no banco e garante tema preferido."""

        user_id = self._resolve_user_id(user_id)
        if user_id is None:
            print("❌ Nenhum user_id para salvar preferências")
            return False

        conn = self.get_connection()
        if not conn:
            print("❌ Não foi possível conectar ao banco para salvar")
            return False

        schema = get_schema() if callable(get_schema) else "opera"
        try:
            with conn.cursor() as cursor:
                custom = settings.get("custom_themes", {}) or {}
                temas_personalizados_json = json.dumps(
                    {nome: _sanitize_palette(pal) for nome, pal in custom.items() if isinstance(pal, dict)}
                )
                tema_nome = settings.get("theme", "Noite Urbana")
                usar_tema_personalizado = bool(settings.get("usar_tema_personalizado", False))

                cursor.execute(
                    f"""
                    INSERT INTO {schema}.usuario_preferencias
                        (usuario_id, tema_nome, usar_tema_personalizado, tema_personalizado, atualizado_em)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (usuario_id)
                    DO UPDATE SET
                        tema_nome = EXCLUDED.tema_nome,
                        usar_tema_personalizado = EXCLUDED.usar_tema_personalizado,
                        tema_personalizado = EXCLUDED.tema_personalizado,
                        atualizado_em = NOW()
                    """,
                    (
                        user_id,
                        tema_nome,
                        usar_tema_personalizado,
                        temas_personalizados_json,
                    ),
                )

                cursor.execute(
                    f"""
                    UPDATE {schema}.usuarios
                    SET tema_preferido = %s
                    WHERE id = %s
                    """,
                    (tema_nome, user_id),
                )

                conn.commit()
                print(f"💾 Tema '{tema_nome}' salvo para usuário {user_id}")
                return True
        except Exception as exc:
            print(f"❌ Erro ao salvar preferências: {exc}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def salvar_tema_personalizado(self, nome: str, paleta: Dict[str, Any], user_id: Optional[int] = None) -> bool:
        """Upsert do tema personalizado na tabela dedicada."""

        user_id = self._resolve_user_id(user_id)
        if user_id is None:
            print("❌ Nenhum user_id para salvar tema personalizado")
            return False

        conn = self.get_connection()
        if not conn:
            print("❌ Não foi possível conectar ao banco para salvar tema personalizado")
            return False

        schema = get_schema() if callable(get_schema) else "opera"
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {schema}.usuario_temas_personalizados (usuario_id, nome_tema, cores_tema, data_criacao, atualizado_em)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    ON CONFLICT (usuario_id, nome_tema)
                    DO UPDATE SET cores_tema = EXCLUDED.cores_tema, atualizado_em = NOW()
                    """,
                    (user_id, nome, json.dumps(_sanitize_palette(paleta))),
                )
                conn.commit()
                print(f"💾 Tema personalizado '{nome}' salvo para usuário {user_id}")
                return True
        except Exception as exc:
            print(f"❌ Erro ao salvar tema personalizado: {exc}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def listar_temas_personalizados(self, user_id: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """Retorna todos os temas personalizados do usuário."""

        user_id = self._resolve_user_id(user_id)
        if user_id is None:
            return {}

        conn = self.get_connection()
        if not conn:
            return {}

        schema = get_schema() if callable(get_schema) else "opera"
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT nome_tema, cores_tema
                    FROM {schema}.usuario_temas_personalizados
                    WHERE usuario_id = %s
                    ORDER BY atualizado_em DESC
                    """,
                    (user_id,),
                )
                temas = {}
                for nome, cores in cursor.fetchall() or []:
                    try:
                        temas[nome] = cores if isinstance(cores, dict) else json.loads(cores)
                    except Exception:
                        continue
                return temas
        except Exception as exc:
            print(f"❌ Erro ao listar temas personalizados: {exc}")
            return {}
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def registrar_tema_atual(
        self,
        nome: str,
        paleta: Dict[str, Any],
        usar_personalizado: bool,
        settings: Dict,
        user_id: Optional[int] = None,
    ) -> None:
        """Atualiza preferências e salva o tema personalizado quando necessário."""

        user_id = self._resolve_user_id(user_id)
        if user_id is None:
            return

        settings = dict(settings)
        settings["theme"] = nome
        settings["usar_tema_personalizado"] = usar_personalizado
        if usar_personalizado:
            custom = settings.get("custom_themes", {})
            custom[nome] = paleta
            settings["custom_themes"] = custom
            self.salvar_tema_personalizado(nome, paleta, user_id=user_id)

        self.salvar_preferencias_usuario(settings, user_id=user_id)

    def _criar_preferencias_padrao(self, user_id: int) -> Dict:
        settings = {
            "theme": "Noite Urbana",
            "custom_themes": {},
            "excluded_default_themes": [],
            "usar_tema_personalizado": False,
            "aplicar_dashboard": True,
            "aplicar_tabelas": True,
            "aplicar_login": True,
        }
        self.salvar_preferencias_usuario(settings, user_id)
        return settings

    def _get_fallback_settings(self) -> Dict:
        print("⚠️ Usando fallback settings")
        return {
            "theme": "Noite Urbana",
            "custom_themes": {},
            "excluded_default_themes": [],
            "aplicar_dashboard": True,
            "aplicar_tabelas": True,
            "aplicar_login": True,
        }

    def get_user_id_by_username(self, username: str) -> Optional[int]:  # pragma: no cover
        conn = self.get_connection()
        if not conn:
            return None

        schema = get_schema() if callable(get_schema) else "opera"
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT id FROM {schema}.usuarios WHERE usuario = %s",
                    (username,),
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as exc:
            print(f"❌ Erro ao buscar ID do usuário: {exc}")
            return None
        finally:
            try:
                conn.close()
            except Exception:
                pass