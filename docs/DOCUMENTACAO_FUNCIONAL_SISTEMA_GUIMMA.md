# DOCUMENTAÇÃO FUNCIONAL — SISTEMA GUIMMA

## 1) O que é o Sistema Guimma

O **Sistema Guimma** é uma plataforma desktop para gestão completa do ciclo de produção têxtil/facção, cobrindo:
- cadastro técnico de modelos;
- planejamento e geração de ordens;
- corte, envio externo, retorno e acabamento;
- controle de estoque e compras;
- custos, pagamentos, recibos e fechamento mensal;
- relatórios gerenciais e operação multiusuário.

Em termos práticos, o sistema conecta **PCP + Produção + Estoque + Financeiro + Administração** em um único fluxo operacional.

---

## 2) Objetivo do sistema (para que ele serve)

O sistema serve para:
1. **Padronizar o processo produtivo** (do modelo até a finalização).
2. **Dar rastreabilidade** por OP, fase, prestador e status.
3. **Reduzir erros operacionais** com telas especializadas por etapa.
4. **Controlar custos reais e financeiros** com base no que foi produzido.
5. **Gerar visão executiva** por meio de dashboard e relatórios.

---

## 3) Fluxo macro de funcionamento

1. **Cadastrar base técnica** (modelos, clientes, facções, insumos).
2. **Planejar produção / MRP** (demanda, materiais, capacidade).
3. **Gerar e executar ordens de corte**.
4. **Controlar envio/retorno de produção externa**.
5. **Registrar acabamento e finalização**.
6. **Apurar custos e realizar pagamentos**.
7. **Emitir relatórios, recibos e acompanhar indicadores**.

---

## 4) Funcionalidades por módulo (tela a tela)

> Fonte da lista: `PAGINAS_DO_SISTEMA/route_map.json`.

### 4.1 Dashboard e visão gerencial
- **Dashboard** (`DASHBOARD.py`): visão consolidada de KPIs de produção, evolução e situação operacional.

### 4.2 Estoque
- **Entrada de Estoque** (`ENTRADA_ESTOQUE.py`): registra entradas de materiais e incrementa saldos.
- **Saída de Estoque** (`SAIDA_ESTOQUE.py`): registra baixas/consumos e mantém histórico de movimentações.
- **Relatórios** (`RELATORIO_ESTOQUE.py`): consultas e consolidações de posição de estoque.

### 4.3 Engenharia de produto e ordens
- **Cadastrar Modelo** (`CADASTRAR_MODELO.py`): cadastro técnico de modelos (insumos, composição e parâmetros).
- **Imprimir Ficha Técnica** (`IMPRIMIR_FICHAS_TECNICAS.py`): emissão de ficha técnica operacional.
- **Nova Ordem** (`NOVA_ORDEM.py`): criação de OP/ordem com vínculo aos dados de modelo/produção.
- **Ordens de Corte Impressão** (`REIMPRIMIR-ORDENS-DE-CORTE.py`): reimpressão de documentos de corte.
- **Cadastrar Corte** (`CADASTRO_DE_CORTE.py`): registro de cortes e dados produtivos iniciais.
- **Consultar Ordens** (`CONSULTAR_ORDENS.py`): busca e auditoria de ordens por filtros operacionais.

### 4.4 Compras e cadastros de apoio
- **Compras** (`COMPRAS.py`): gestão de pedidos e acompanhamento de aquisição.
- **Cadastro de Prestadores** (`CADASTRO_FACCOES.py`): cadastro de facções/prestadores externos.
- **Pesquisar Serviço** (`CONSULTAR_SERVICOS.py`): consulta de serviços e histórico operacional.
- **Clientes** (`CADASTRO_CLIENTES.py`): cadastro e manutenção de base de clientes.

### 4.5 Produção externa, mão de obra e retrabalho
- **Controle de Mão de Obra** (`CONTROLE_ENVIO_CORTES.py`): envio de produção para prestadores.
- **Registro Acabamento** (`CONTROLE_RETORNO_CORTE.py`): retorno da produção e conferência.
- **Finalizar Corte / Acabamento** (`FINALIZAR_CORTE_ACABAMENTO.py`): fechamento técnico da OP.
- **Retrabalho de Defeitos** (`RETRABALHO_DEFEITOS.py`): controle de defeitos, pendências e reprocessos.

### 4.6 PCP e planejamento
- **MRP** (`MRP_PLANEJAMENTO.py`): planejamento de materiais e necessidade de reposição.
- **Planejamento de Produção** (`PLANEJAMENTO_PRODUCAO.py`): programação de produção e capacidade.
- **Ordens Planejadas** (`ORDENS_PLANEJADAS.py`): gestão de OP planejadas e abertura integrada na Nova Ordem.

### 4.7 Custos e financeiro
- **Custos Reais** (`RELATORIO_CUSTOS_REAIS.py`): apuração de custo realizado por operação/categoria.
- **Pagamento de Serviços** (`PAGAMENTO_SERVICOS.py`): processamento de pagamentos a prestadores.
- **Recibos de Pagamentos** (`RECIBOS_PAGAMENTOS.py`): emissão e rastreio de comprovantes.
- **Custo Produto** (`PRECIFICACAO_PRODUTO.py`): suporte à formação de preço por composição de custos.
- **Folha Pagamento** (`FOLHA_PAGAMENTO_SERVICOS.py`): consolidação de folha por serviços/prestadores.
- **Fechamento Mensal** (`FECHAMENTO_MENSAL.py`): fechamento financeiro periódico.
- **Contas a Pagar** (`CONTAS_A_PAGAR.py`): controle de compromissos financeiros e vencimentos.
- **Adiantamento** (`ADIANTAMENTO_PAGE.py`): registro de adiantamentos.
- **Adiantamentos Pendentes** (`ADIANTAMENTO_PENDENTE.py`): acompanhamento de saldos/pendências de adiantamento.

### 4.8 Relatórios operacionais de produção
- **Produção** (`RELATORIO_ENVIO_DETALHADO.py`): relatório detalhado do fluxo de envio e status.
- **Serviços Externos** (`RELATORIO_SERVICOS_EXTERNOS.py`): visão consolidada de produção externa.
- **Modelos Produzidos** (`RELATORIO_MODELOS_PRODUZIDOS.py`): produtividade por modelo.
- **Acabamento** (`RELATORIO_ACABAMENTO.py`): análise de etapa final/acabamento.
- **RELATORIOS** (`RELATORIO_ENVIO_DETALHADO.py`): atalho adicional para relatórios operacionais.

### 4.9 Subvisões de produção
- **Interna** (`PRODUCAO_INTERNA.py`): acompanhamento da produção interna.
- **Enviados** (`PRODUCAO_ENVIADOS.py`): acompanhamento de lotes enviados.
- **Retorno** (`PRODUCAO_RETORNO.py`): acompanhamento de lotes retornados.
- **Finalizados** (`PRODUCAO_FINALIZADOS.py`): acompanhamento de lotes finalizados.

### 4.10 Administração e suporte do sistema
- **Usuários** (`USUARIOS.py`): gestão de usuários, permissões e logs.
- **Logs e Atividades** (`USUARIOS.py`): visão/auditoria de ações no sistema.
- **Trocar Usuário** (`MENU_PRINCIPAL`): alternância de sessão de usuário.
- **Temas** (`TEMAS.py`): personalização visual e aplicação de temas.
- **Backup** (`BACKUP.py`): backup operacional dos dados/artefatos.
- **Atualizar Sistema** (`ATUALIZAR_SISTEMA.py`): atualização de versão da aplicação.
- **Gerenciar** (`BANCO_DADOS_FABRICA.py`): rotinas de gestão de dados de fábrica/banco.

---

## 5) Funcionalidades transversais (presentes em várias telas)

- **Internacionalização (PT/EN/ES)** em páginas e mensagens.
- **Tema claro/escuro e paletas personalizadas**.
- **Controle de permissões por usuário/hierarquia**.
- **Logs de atividade** para auditoria.
- **Integração com PostgreSQL** via camada central de banco.
- **Roteamento por `route_map.json`** para carregamento dinâmico das telas.

---

## 6) Resultado prático para a empresa

Com o Sistema Guimma, a empresa passa a ter:
- processo produtivo mais previsível;
- visão de gargalos por etapa;
- melhor controle de estoque e custo;
- maior confiabilidade em pagamentos e fechamento;
- histórico operacional auditável por usuário e por OP.

---

## 7) Documento PDF demonstrativo

Este conteúdo também foi exportado em PDF para apresentação:

- `DOCUMENTACAO_FUNCIONAL_SISTEMA_GUIMMA.pdf`
