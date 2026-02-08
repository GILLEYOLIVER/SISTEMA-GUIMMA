# -*- coding: utf-8 -*-
"""
DATABASE_LOGGER.py - Sistema de Logs Automático para OPERA
"""

import functools
from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn_cursor


def log_action(acao: str, pagina: str, detalhe_template: str = None):
    """
    Decorator para registrar logs automaticamente em qualquer função
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Executa a função original
            result = func(*args, **kwargs)

            try:
                # Tenta extrair o usuário dos argumentos
                usuario = None

                # Procura usuário nos argumentos nomeados
                if 'usuario' in kwargs:
                    usuario = kwargs['usuario']
                elif 'usuario_logado' in kwargs:
                    usuario = kwargs['usuario_logado']
                elif 'current_user' in kwargs:
                    usuario = kwargs['current_user']

                # Procura usuário nos argumentos posicionais (geralmente o primeiro)
                if not usuario and len(args) > 0:
                    if isinstance(args[0], str) and len(args[0]) < 100:
                        usuario = args[0]

                # Se não encontrou usuário, usa 'Sistema'
                if not usuario:
                    usuario = 'Sistema'

                # Monta detalhe dinâmico
                detalhe = detalhe_template
                if detalhe_template and result:
                    try:
                        # Tenta preencher template com resultado
                        if isinstance(result, dict):
                            detalhe = detalhe_template.format(**result)
                        elif isinstance(result, (str, int, float)):
                            detalhe = detalhe_template.format(result=result)
                    except:
                        detalhe = detalhe_template

                # Registra o log no banco
                with get_conn_cursor() as (conn, cursor):
                    cursor.execute("""
                        SELECT opera.registrar_log_usuario(%s, %s, %s, %s)
                    """, (usuario, acao, pagina, detalhe))
                    conn.commit()

            except Exception as e:
                # Não quebra a aplicação se o log falhar
                print(f"[LOG ERROR] {e}")
                pass

            return result

        return wrapper

    return decorator