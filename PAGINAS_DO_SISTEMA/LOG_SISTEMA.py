# -*- coding: utf-8 -*-
"""
MÓDULO DE LOG DE ERROS - OPERA FASHION
Centraliza o registro de erros, informações e auditoria de todo o sistema
"""
import os
import sys
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, Union
import json
from pathlib import Path


class SistemaLogger:
    """
    Classe principal para gerenciamento de logs do sistema OPERA
    """

    # Níveis de log
    NIVEL_DEBUG = "DEBUG"
    NIVEL_INFO = "INFO"
    NIVEL_WARNING = "WARNING"
    NIVEL_ERROR = "ERROR"
    NIVEL_CRITICAL = "CRITICAL"

    # Categorias de log
    CATEGORIA_SISTEMA = "SISTEMA"
    CATEGORIA_BANCO_DADOS = "BANCO_DADOS"
    CATEGORIA_USUARIO = "USUARIO"
    CATEGORIA_SEGURANCA = "SEGURANCA"
    CATEGORIA_NEGOCIO = "NEGOCIO"
    CATEGORIA_PAGINA = "PAGINA"
    CATEGORIA_IMPRESSAO = "IMPRESSAO"
    CATEGORIA_BACKUP = "BACKUP"

    def __init__(self, app_dir: str = None):
        """
        Inicializa o sistema de logs

        Args:
            app_dir: Diretório principal do aplicativo
        """
        self.app_dir = app_dir or os.path.dirname(__file__)
        self.logs_dir = os.path.join(self.app_dir, "logs")
        self._setup_diretorios()
        self._configurar_logging()
        self.usuario_atual = "Sistema"
        self.pagina_atual = "MenuPrincipal"
        self.hierarquia_usuario = ""

    def _setup_diretorios(self):
        """Cria a estrutura de diretórios para logs"""
        try:
            os.makedirs(self.logs_dir, exist_ok=True)

            # Subdiretórios por categoria
            categorias = [
                "sistema", "banco_dados", "usuario", "seguranca",
                "negocio", "paginas", "impressao", "backup"
            ]

            for categoria in categorias:
                os.makedirs(os.path.join(self.logs_dir, categoria), exist_ok=True)

        except Exception as e:
            print(f"ERRO CRÍTICO: Não foi possível criar diretórios de log: {e}")

    def _configurar_logging(self):
        """Configura o sistema de logging do Python"""
        try:
            # Formato padrão para logs
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            # Logger principal
            self.logger = logging.getLogger('OPERA_SYSTEM')
            self.logger.setLevel(logging.DEBUG)
            self.logger.propagate = False

            # Remove handlers existentes para evitar duplicação
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)

            # Handler para arquivo geral
            log_geral = os.path.join(self.logs_dir, "sistema_geral.log")
            file_handler = logging.FileHandler(log_geral, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

            # Handler para erros
            log_erros = os.path.join(self.logs_dir, "erros_criticos.log")
            error_handler = logging.FileHandler(log_erros, encoding='utf-8')
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            self.logger.addHandler(error_handler)

            # Handler para console (sempre ativo para aparecer no console / PyCharm)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        except Exception as e:
            print(f"ERRO CRÍTICO: Falha na configuração do logging: {e}")

    def _is_development(self) -> bool:
        """Verifica se está em ambiente de desenvolvimento"""
        return any(x in sys.argv[0] for x in ['debug', 'develop', 'test']) or \
            os.environ.get('OPERA_DEBUG') == '1'

    def set_usuario(self, usuario: str, hierarquia: str = ""):
        """Define o usuário atual para os logs"""
        self.usuario_atual = usuario
        self.hierarquia_usuario = hierarquia

    def set_pagina(self, pagina: str):
        """Define a página atual para os logs"""
        self.pagina_atual = pagina

    def _get_log_file(self, categoria: str, nivel: str) -> str:
        """Retorna o caminho do arquivo de log específico"""
        data_hoje = datetime.now().strftime("%Y-%m-%d")

        # Mapeamento de categorias para diretórios
        categoria_dir = {
            self.CATEGORIA_SISTEMA: "sistema",
            self.CATEGORIA_BANCO_DADOS: "banco_dados",
            self.CATEGORIA_USUARIO: "usuario",
            self.CATEGORIA_SEGURANCA: "seguranca",
            self.CATEGORIA_NEGOCIO: "negocio",
            self.CATEGORIA_PAGINA: "paginas",
            self.CATEGORIA_IMPRESSAO: "impressao",
            self.CATEGORIA_BACKUP: "backup"
        }

        dir_categoria = categoria_dir.get(categoria, "sistema")
        nome_arquivo = f"{data_hoje}_{nivel.lower()}.log"

        return os.path.join(self.logs_dir, dir_categoria, nome_arquivo)

    def _escrever_log_detalhado(self, nivel: str, categoria: str, mensagem: str,
                                detalhes: Dict[str, Any] = None):
        """Escreve log detalhado em arquivo específico"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            log_file = self._get_log_file(categoria, nivel)

            log_entry = {
                "timestamp": timestamp,
                "nivel": nivel,
                "categoria": categoria,
                "usuario": self.usuario_atual,
                "hierarquia": self.hierarquia_usuario,
                "pagina": self.pagina_atual,
                "mensagem": mensagem,
                "detalhes": detalhes or {}
            }

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        except Exception as e:
            print(f"FALHA AO ESCREVER LOG: {e}")

    def debug(self, mensagem: str, categoria: str = CATEGORIA_SISTEMA,
              detalhes: Dict[str, Any] = None):
        """Registro de nível DEBUG"""
        self.logger.debug(f"[{categoria}] {mensagem}")
        self._escrever_log_detalhado(self.NIVEL_DEBUG, categoria, mensagem, detalhes)

    def info(self, mensagem: str, categoria: str = CATEGORIA_SISTEMA,
             detalhes: Dict[str, Any] = None):
        """Registro de nível INFO"""
        self.logger.info(f"[{categoria}] {mensagem}")
        self._escrever_log_detalhado(self.NIVEL_INFO, categoria, mensagem, detalhes)

    def warning(self, mensagem: str, categoria: str = CATEGORIA_SISTEMA,
                detalhes: Dict[str, Any] = None):
        """Registro de nível WARNING"""
        self.logger.warning(f"[{categoria}] {mensagem}")
        self._escrever_log_detalhado(self.NIVEL_WARNING, categoria, mensagem, detalhes)

    def error(self, mensagem: str, categoria: str = CATEGORIA_SISTEMA,
              detalhes: Dict[str, Any] = None, exc_info: bool = True):
        """Registro de nível ERROR"""
        self.logger.error(f"[{categoria}] {mensagem}", exc_info=exc_info)

        # Adiciona traceback se disponível
        if exc_info and sys.exc_info()[0] is not None:
            traceback_str = traceback.format_exc()
            if detalhes is None:
                detalhes = {}
            detalhes['traceback'] = traceback_str

        self._escrever_log_detalhado(self.NIVEL_ERROR, categoria, mensagem, detalhes)

    def critical(self, mensagem: str, categoria: str = CATEGORIA_SISTEMA,
                 detalhes: Dict[str, Any] = None):
        """Registro de nível CRITICAL"""
        self.logger.critical(f"[{categoria}] {mensagem}")

        # Adiciona traceback se disponível
        if sys.exc_info()[0] is not None:
            traceback_str = traceback.format_exc()
            if detalhes is None:
                detalhes = {}
            detalhes['traceback'] = traceback_str

        self._escrever_log_detalhado(self.NIVEL_CRITICAL, categoria, mensagem, detalhes)

    def log_excecao(self, mensagem: str, excecao: Exception,
                    categoria: str = CATEGORIA_SISTEMA,
                    detalhes: Dict[str, Any] = None):
        """Registro especializado para exceções"""
        if detalhes is None:
            detalhes = {}

        detalhes.update({
            'tipo_excecao': type(excecao).__name__,
            'mensagem_excecao': str(excecao),
            'traceback': traceback.format_exc()
        })

        self.error(mensagem, categoria, detalhes)

    def log_banco_dados(self, operacao: str, tabela: str = "",
                        query: str = "", parametros: tuple = None,
                        sucesso: bool = True, mensagem: str = ""):
        """Registro especializado para operações de banco de dados"""
        detalhes = {
            'operacao': operacao,
            'tabela': tabela,
            'query': query,
            'parametros': str(parametros) if parametros else None,
            'sucesso': sucesso
        }

        nivel = self.NIVEL_INFO if sucesso else self.NIVEL_ERROR
        mensagem_completa = f"DB {operacao.upper()} {tabela}: {mensagem or ('Sucesso' if sucesso else 'Falha')}"

        if sucesso:
            self.info(mensagem_completa, self.CATEGORIA_BANCO_DADOS, detalhes)
        else:
            self.error(mensagem_completa, self.CATEGORIA_BANCO_DADOS, detalhes)

    def log_usuario(self, acao: str, detalhes: Dict[str, Any] = None):
        """Registro especializado para ações de usuário"""
        mensagem = f"Ação do usuário: {acao}"
        self.info(mensagem, self.CATEGORIA_USUARIO, detalhes)

    def log_seguranca(self, evento: str, nivel: str = NIVEL_INFO,
                      detalhes: Dict[str, Any] = None):
        """Registro especializado para eventos de segurança"""
        if nivel == self.NIVEL_INFO:
            self.info(f"Segurança: {evento}", self.CATEGORIA_SEGURANCA, detalhes)
        elif nivel == self.NIVEL_WARNING:
            self.warning(f"Segurança: {evento}", self.CATEGORIA_SEGURANCA, detalhes)
        elif nivel == self.NIVEL_ERROR:
            self.error(f"Segurança: {evento}", self.CATEGORIA_SEGURANCA, detalhes)
        else:
            self.info(f"Segurança: {evento}", self.CATEGORIA_SEGURANCA, detalhes)

    def log_pagina(self, pagina: str, acao: str, sucesso: bool = True,
                   detalhes: Dict[str, Any] = None):
        """Registro especializado para ações em páginas"""
        mensagem = f"Página {pagina}: {acao} - {'Sucesso' if sucesso else 'Falha'}"

        if sucesso:
            self.info(mensagem, self.CATEGORIA_PAGINA, detalhes)
        else:
            self.error(mensagem, self.CATEGORIA_PAGINA, detalhes)

    def get_estatisticas(self, data_inicio: str = None, data_fim: str = None) -> Dict[str, Any]:
        """
        Retorna estatísticas dos logs no período

        Args:
            data_inicio: Data inicial no formato YYYY-MM-DD
            data_fim: Data final no formato YYYY-MM-DD

        Returns:
            Dicionário com estatísticas
        """
        try:
            # Implementação básica - pode ser expandida
            estatisticas = {
                "total_erros": 0,
                "total_warnings": 0,
                "total_info": 0,
                "erros_por_categoria": {},
                "usuarios_ativos": set(),
                "paginas_com_erros": set()
            }

            return estatisticas

        except Exception as e:
            self.error("Erro ao calcular estatísticas de log", detalhes={"erro": str(e)})
            return {}

    def limpar_logs_antigos(self, dias_manter: int = 30):
        """
        Remove logs mais antigos que o número especificado de dias

        Args:
            dias_manter: Número de dias para manter os logs
        """
        try:
            from datetime import datetime, timedelta
            data_limite = datetime.now() - timedelta(days=dias_manter)

            for root, dirs, files in os.walk(self.logs_dir):
                for file in files:
                    if file.endswith('.log'):
                        file_path = os.path.join(root, file)
                        # Tenta extrair data do nome do arquivo
                        try:
                            data_str = file.split('_')[0]
                            file_date = datetime.strptime(data_str, "%Y-%m-%d")
                            if file_date < data_limite:
                                os.remove(file_path)
                                self.info(f"Log antigo removido: {file_path}")
                        except (ValueError, IndexError):
                            # Se não consegue extrair data, usa data de modificação
                            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                            if file_mtime < data_limite:
                                os.remove(file_path)
                                self.info(f"Log antigo removido: {file_path}")

        except Exception as e:
            self.error("Erro ao limpar logs antigos", detalhes={"erro": str(e)})


# Instância global do logger
_logger_instance: Optional[SistemaLogger] = None


def get_logger(app_dir: str = None) -> SistemaLogger:
    """
    Retorna a instância global do logger (singleton)

    Args:
        app_dir: Diretório do aplicativo

    Returns:
        Instância do SistemaLogger
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = SistemaLogger(app_dir)
    return _logger_instance


def inicializar_logger(app_dir: str = None) -> SistemaLogger:
    """
    Inicializa e retorna o logger (alias para get_logger)

    Args:
        app_dir: Diretório do aplicativo

    Returns:
        Instância do SistemaLogger
    """
    return get_logger(app_dir)


# Funções de conveniência para uso rápido
def log_debug(mensagem: str, categoria: str = SistemaLogger.CATEGORIA_SISTEMA,
              detalhes: Dict[str, Any] = None, app_dir: str = None):
    get_logger(app_dir).debug(mensagem, categoria, detalhes)


def log_info(mensagem: str, categoria: str = SistemaLogger.CATEGORIA_SISTEMA,
             detalhes: Dict[str, Any] = None, app_dir: str = None):
    get_logger(app_dir).info(mensagem, categoria, detalhes)


def log_warning(mensagem: str, categoria: str = SistemaLogger.CATEGORIA_SISTEMA,
                detalhes: Dict[str, Any] = None, app_dir: str = None):
    get_logger(app_dir).warning(mensagem, categoria, detalhes)


def log_error(mensagem: str, categoria: str = SistemaLogger.CATEGORIA_SISTEMA,
              detalhes: Dict[str, Any] = None, app_dir: str = None):
    get_logger(app_dir).error(mensagem, categoria, detalhes)


def log_critical(mensagem: str, categoria: str = SistemaLogger.CATEGORIA_SISTEMA,
                 detalhes: Dict[str, Any] = None, app_dir: str = None):
    get_logger(app_dir).critical(mensagem, categoria, detalhes)


def log_excecao(mensagem: str, excecao: Exception,
                categoria: str = SistemaLogger.CATEGORIA_SISTEMA,
                detalhes: Dict[str, Any] = None, app_dir: str = None):
    get_logger(app_dir).log_excecao(mensagem, excecao, categoria, detalhes)


# Decorator para logging automático de funções
def log_function_call(categoria: str = SistemaLogger.CATEGORIA_SISTEMA):
    """
    Decorator para log automático de chamadas de função
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger()
            func_name = func.__name__
            logger.debug(f"Chamando função: {func_name}", categoria,
                         {"args": str(args), "kwargs": str(kwargs)})

            try:
                result = func(*args, **kwargs)
                logger.debug(f"Função concluída: {func_name}", categoria,
                             {"resultado": str(result)})
                return result
            except Exception as e:
                logger.log_excecao(f"Erro na função: {func_name}", e, categoria)
                raise

        return wrapper

    return decorator


if __name__ == "__main__":
    # Teste básico do módulo
    logger = inicializar_logger()
    logger.info("Módulo de log inicializado com sucesso!")
    logger.log_usuario("Teste de usuário", {"acao": "login", "ip": "127.0.0.1"})

    try:
        # Simula um erro para teste
        raise ValueError("Este é um erro de teste")
    except Exception as e:
        logger.log_excecao("Erro durante teste", e)