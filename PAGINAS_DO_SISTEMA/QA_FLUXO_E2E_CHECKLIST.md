# Checklist de QA - Fluxo E2E (Páginas ↔ Banco)

Este roteiro foi criado para validar, de ponta a ponta, a comunicação entre telas e banco de dados do Sistema Opera.

## 1) Pré-condições do ambiente

- [ ] Banco PostgreSQL em execução.
- [ ] `psycopg2` instalado no ambiente Python.
- [ ] Cliente `psql` disponível no PATH.
- [ ] `config.json` apontando para a instância correta do banco.
- [ ] Schema/tabelas criados via scripts em `SCRIPTS/`.

## 2) Smoke técnico inicial (obrigatório)

Executar:

```bash
python PAGINAS_DO_SISTEMA/flow_smoke_check.py
```

Critérios mínimos para avançar:
- [ ] Compilação sem erros.
- [ ] `route_map.json` íntegro (sem arquivo faltante).

## 3) Fluxo funcional por módulo (CRUD)

Para cada módulo abaixo, executar os 5 passos:
1. Abrir tela sem erro.
2. Cadastrar registro válido.
3. Consultar registro salvo (na própria tela).
4. Editar registro e validar atualização.
5. Excluir/inativar e validar estado final.

### 3.1 Cadastros base
- [ ] Clientes (`CADASTRO_CLIENTES.py`)
- [ ] Facções (`CADASTRO_FACCOES.py`)
- [ ] Usuários (`USUARIOS.py`)

### 3.2 Produção e corte
- [ ] Nova ordem (`NOVA_ORDEM.py`)
- [ ] Cadastro de corte (`CADASTRO_DE_CORTE.py`)
- [ ] Controle de envio (`CONTROLE_ENVIO_CORTES.py`)
- [ ] Retorno de corte (`CONTROLE_RETORNO_CORTE.py`)
- [ ] Finalização (`FINALIZAR_CORTE_ACABAMENTO.py`)

### 3.3 Estoque
- [ ] Entrada (`ENTRADA_ESTOQUE.py`)
- [ ] Saída (`SAIDA_ESTOQUE.py`)
- [ ] Relatório de estoque (`RELATORIO_ESTOQUE.py`)

### 3.4 Financeiro
- [ ] Contas a pagar (`CONTAS_A_PAGAR.py`)
- [ ] Adiantamentos (`ADIANTAMENTO_PAGE.py`)
- [ ] Pagamento de serviços (`PAGAMENTO_SERVICOS.py`)

## 4) Validação cruzada com banco

Para cada operação de gravação executada nas telas:
- [ ] Confirmar persistência com `SELECT` no PostgreSQL.
- [ ] Confirmar campos obrigatórios, datas e valores numéricos.
- [ ] Confirmar auditoria/log quando aplicável.

## 5) Regressão rápida antes de liberar

- [ ] Rodar novamente o smoke técnico.
- [ ] Reexecutar pelo menos 1 caso crítico de cada módulo.
- [ ] Validar geração de relatório principal sem erro.

## 6) Evidências recomendadas

- Captura de tela de cada etapa funcional crítica.
- Export de consultas SQL usadas para validação.
- Registro de data/hora, usuário testador e ambiente.
