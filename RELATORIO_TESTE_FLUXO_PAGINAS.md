# Relatório de Teste de Fluxo das Páginas

Data do teste: 25/06/2026  
Projeto: SISTEMA-GUIMMA / Sistema OPERA  
Banco testado: PostgreSQL local, schema `opera`, base `BANCO_OPERA`

## 1. Resumo executivo

Foram validadas as páginas cadastradas no `route_map.json`, os arquivos Python da pasta principal, o schema crítico do banco e dois fluxos operacionais com dados temporários:

- Rotas do menu: 47 verificadas.
- Arquivos de página compilados: 63/63 OK.
- Rotas com arquivo, import e classe esperada: 46/46 OK.
- Ação interna do menu: 1/1 OK (`Trocar Usuário`).
- Tabelas críticas por setor: todas encontradas.
- Colunas críticas para rastrear corte e atualizar estoque: OK.
- Fluxo de estoque com entrada, baixa e atualização: OK.
- Fluxo de corte até pagamento e busca profunda: OK.
- Registros temporários de teste: removidos, total remanescente 0.

Durante o teste foram corrigidos problemas reais encontrados:

- 6 rotas apontavam para classes inexistentes no `route_map.json`.
- O banco instalado tinha divergência entre estoque por `metros/kilos` e relatórios que esperavam `quantidade/categoria`.
- Foi criado bloco de migração no `3_CRIAR_TABELAS.sql` para completar colunas faltantes em bancos antigos.
- Foi criado gatilho `tr_sync_estoque_tecidos_compat` para manter `estoque_tecidos.quantidade` sincronizada com `metros`.
- Foi adicionada a página `Busca Profunda Corte` para rastrear o corte por código/ordem/ID.

## 2. Escopo testado

O teste cobriu:

- Carregamento do mapa de rotas.
- Existência de arquivos das páginas.
- Compilação Python de todas as páginas.
- Importação de todos os módulos das rotas.
- Existência das classes esperadas nas rotas.
- Conexão com PostgreSQL.
- Existência de tabelas por setor.
- Existência de colunas necessárias para estoque, corte, envio, retorno, acabamento, finalização, pagamento e permissões.
- Fluxo de estoque com dados temporários.
- Fluxo de produção/corte até pagamento com dados temporários.
- Rastreamento do corte pela nova página de busca profunda.

Não foi feito clique manual visual em cada tela dentro da interface gráfica. A validação foi automatizada por importação/compilação/schema e testes diretos de banco. Janelas de impressão reais também não foram acionadas em impressora física.

## 3. Evidências de execução

### 3.1 Rotas e classes

Resultado após correção do `route_map.json`:

- Total de rotas: 47.
- Compilação das rotas: 46 OK, 1 SKIP por ser ação interna.
- Importação das rotas: 46 OK, 1 SKIP por ser ação interna.
- Classe esperada: 46 OK, 1 SKIP por ser ação interna.
- Falhas remanescentes: nenhuma.

### 3.2 Compilação geral

Comando de validação compilou todos os arquivos `.py` em `PAGINAS_DO_SISTEMA`:

- Total: 63.
- OK: 63.
- Falhas: 0.

### 3.3 Banco/schema

Grupos críticos encontrados:

| Setor | Tabelas esperadas | Resultado |
|---|---:|---|
| Modelos | 4 | OK |
| Cortes | 4 | OK |
| Prestadores/serviços | 3 | OK |
| Mão de obra/acabamento | 5 | OK |
| Financeiro | 4 | OK |
| Estoque | 7 | OK |
| Usuários/permissões | 3 | OK |
| Planejamento | 3 | OK |

Colunas críticas verificadas:

| Tabela | Resultado |
|---|---|
| `estoque_tecidos` | OK: `metros`, `kilos`, `quantidade`, `categoria`, `tipo`, `status`, níveis de estoque |
| `cadastro_de_corte` | OK: código, ordem, descrição, data, total de peças |
| `envios_cortes` | OK: corte, ordem, código, descrição, status, total, valor |
| `entrada_acabamento` | OK: envio, chegada, pagamento, valor pago |
| `cortes_finalizados` | OK: corte, envio, retorno, código, status, pago, pagamento |
| `usuario_permissoes` | OK: ver, editar, imprimir, excluir, administrar |

### 3.4 Teste de estoque

Foi criado um item temporário em `estoque_tecidos`, depois removido.

Resultado:

- Inserção: `metros=10.000`, `quantidade=10.000`.
- Baixa: `metros=7.000`, `quantidade=7.000`.
- Atualização: `metros=15.000`, `quantidade=15.000`.
- Categoria gerada: `Tecidos`.
- Status gerado: `Normal`.
- Limpeza: OK.

Conclusão: entrada/baixa/atualização do saldo-base de tecidos está consistente com a compatibilidade dos relatórios.

### 3.5 Teste de corte até pagamento

Foi criado um fluxo temporário com código `TESTE_RELATORIO_CORTE_CODEX_20260625`, depois removido.

Etapas rastreadas pela busca profunda:

1. `cadastro_de_corte`
2. `controle_envio_cortes`
3. `envios_cortes`
4. `controle_retorno_cortes`
5. `entrada_acabamento`
6. `cortes_finalizados`
7. `pagamento_servicos`

Resultado:

- Eventos encontrados: 7.
- Pagamento vinculado via `pagamento_servicos_detalhe`: OK.
- Busca profunda por código: OK.
- Limpeza dos registros temporários: OK.

Conclusão: o corte consegue ser rastreado do cadastro até o pagamento quando os vínculos mínimos existem.

## 3.6 Rodada extensiva final como usuário - 25/06/2026 15:31

Objetivo: repetir o fluxo como operador final antes de entrega ao cliente, usando as telas e classes reais do sistema sempre que possível, com popups capturados para detectar erros de leitura, salvamento ou carregamento.

Resultado geral: APROVADO.

Evidências principais:

- Cadastro de prestadores: `CadastroFaccoesView.pesquisar_faccoes()` carregou 9 linhas sem erro, incluindo códigos alfanuméricos como `FAC001`.
- Estoque antes da rodada:
  - Tecidos: 13 itens.
  - Aviamentos: 11 itens.
  - Insumos: 7 itens.
  - Escritório: 6 itens.
  - Limpeza: 6 itens.
  - Outros: 6 itens.
- Entrada de estoque: a tela `EntradaEstoqueApp` carregou todos os 6 setores e cadastrou 1 produto novo em cada setor:
  - `TST-TEC-133183725`
  - `TST-AVI-133277948`
  - `TST-INS-133358700`
  - `TST-ESC-133429872`
  - `TST-LIM-133503567`
  - `TST-OUT-133576345`
- Estoque depois dos cadastros:
  - Tecidos: 14 itens.
  - Aviamentos: 12 itens.
  - Insumos: 8 itens.
  - Escritório: 7 itens.
  - Limpeza: 7 itens.
  - Outros: 7 itens.
- Saída de estoque: a tela `SaidaEstoqueApp` carregou todos os setores e registrou baixa em todos:
  - Tecidos: baixa de 0,10 metro, saldo retornado pela tela `12,40 m / 3,200 kg`.
  - Aviamentos, Insumos, Escritório, Limpeza e Outros: baixa de 1 unidade cada, saldo retornado pela tela `17`.
- Dashboard: `DashboardPage.atualizar_dashboard()` executou sem erro após a rodada.
- Ficha/ordem de corte: PDF gerado com sucesso em `C:\Users\User\AppData\Local\Temp\ORDEM_CORTE_DEMO-OC-20260625153134.pdf`.
- Relatório/impressão da busca profunda: HTML de impressão gerado e enviado para abertura em `C:\Users\User\AppData\Local\Temp\rastreamento_corte_wrde1m50.html`.

Fluxo completo de corte gravado para rastreio:

- Código do corte: `DEMO-CORTE-20260625153134`.
- Ordem: `DEMO-OC-20260625153134`.
- Etapas gravadas:
  - ordem de corte/ficha.
  - cadastro de corte.
  - envio legado.
  - envio para prestador.
  - retorno parcial.
  - retorno total.
  - entrada/acabamento.
  - finalização.
  - finalização completa.
  - peças finalizadas.
  - adiantamento.
  - pagamento de serviços.
  - pagamento de corte/acabamento.
- Busca profunda pelo código retornou 13 eventos e nenhuma etapa obrigatória ficou faltando.
- Etapa atual exibida após ajuste: `Pagamento de corte/acabamento (Ativo)`.

Erros capturados nesta rodada:

- `messagebox.showerror`: 0 ocorrências.
- Falhas de carregamento: 0.
- Falhas de salvamento: 0.
- Falhas de baixa de estoque: 0.
- Falhas de geração de PDF/relatório: 0.

Correções feitas durante esta rodada:

- `CADASTRO_FACCOES.py`: carregamento e geração de código agora aceitam códigos alfanuméricos (`FAC001`, `BOR001`, etc.) sem tentar converter tudo para inteiro.
- `BUSCA_PROFUNDA_CORTE.py`: booleano `estornado=false` agora aparece como `Ativo`, não como `Pendente`, evitando interpretação errada de pagamento.

## 4. Páginas e rotas testadas

| Página | Arquivo | Classe/Ação | Resultado |
|---|---|---|---|
| Dashboard | `DASHBOARD.py` | `DashboardPage` | OK |
| Entrada de Estoque | `ENTRADA_ESTOQUE.py` | `EntradaEstoqueApp` | OK |
| Saída de Estoque | `SAIDA_ESTOQUE.py` | `SaidaEstoqueApp` | OK |
| Relatórios | `RELATORIO_ESTOQUE.py` | `AdvancedStockReport` | OK |
| Cadastrar Modelo | `CADASTRAR_MODELO.py` | `CadastroModelosApp` | OK |
| Imprimir Ficha Técnica | `IMPRIMIR_FICHAS_TECNICAS.py` | `ImprimirFichasTecnicasPage` | OK |
| Nova Ordem | `NOVA_ORDEM.py` | `OrdemCorte` | OK |
| Ordens de Corte Impressão | `REIMPRIMIR-ORDENS-DE-CORTE.py` | `OrdensCorteImpressao` | OK |
| Cadastrar Corte | `CADASTRO_DE_CORTE.py` | `CadastroOrdemCorte` | OK |
| Consultar Ordens | `CONSULTAR_ORDENS.py` | `OrdemCorteFinalizada` | OK |
| Busca Profunda Corte | `BUSCA_PROFUNDA_CORTE.py` | `BuscaProfundaCortePage` | OK |
| Compras | `COMPRAS.py` | `ComprasPage` | OK |
| Cadastro de Prestadores | `CADASTRO_FACCOES.py` | `CadastroFaccoesView` | OK |
| Pesquisar Serviço | `CONSULTAR_SERVICOS.py` | `HistoricoServicosPage` | OK |
| Clientes | `CADASTRO_CLIENTES.py` | `ClientesPage` | OK |
| Retrabalho de Defeitos | `RETRABALHO_DEFEITOS.py` | `RetrabalhoDefeitosPage` | OK |
| Controle de Mão de Obra | `CONTROLE_ENVIO_CORTES.py` | `EnvioCortes` | OK |
| MRP | `MRP_PLANEJAMENTO.py` | `MRPPage` | OK |
| Planejamento de Produção | `PLANEJAMENTO_PRODUCAO.py` | `PlanejamentoProducaoPage` | OK |
| Custos Reais | `RELATORIO_CUSTOS_REAIS.py` | `RelatorioCustosReaisPage` | OK |
| Registro Acabamento | `CONTROLE_RETORNO_CORTE.py` | `RetornoCortes` | OK |
| Finalizar Corte / Acabamento | `FINALIZAR_CORTE_ACABAMENTO.py` | `FinalizacaoCortes` | OK |
| Pagamento de Serviços | `PAGAMENTO_SERVICOS.py` | `PagamentoModernUI` | OK |
| Recibos de Pagamentos | `RECIBOS_PAGAMENTOS.py` | `RecibosPagamentosPage` | OK |
| Custo Produto | `PRECIFICACAO_PRODUTO.py` | `PrecificacaoProdutoPage` | OK |
| Folha Pagamento | `FOLHA_PAGAMENTO_SERVICOS.py` | `FolhaPagamentoServicosPage` | OK |
| Fechamento Mensal | `FECHAMENTO_MENSAL.py` | `FechamentoMensalPage` | OK |
| Contas a Pagar | `CONTAS_A_PAGAR.py` | `ContasAPagarPage` | OK |
| Adiantamento | `ADIANTAMENTO_PAGE.py` | `PagamentoAdiantamentoPage` | OK |
| Adiantamentos Pendentes | `ADIANTAMENTO_PENDENTE.py` | `AdiantamentosPendentesPage` | OK |
| Produção | `RELATORIO_ENVIO_DETALHADO.py` | `RelatorioEnvioDetalhado` | OK |
| Serviços Externos | `RELATORIO_SERVICOS_EXTERNOS.py` | `RelatorioServicosExternosPage` | OK |
| Modelos Produzidos | `RELATORIO_MODELOS_PRODUZIDOS.py` | `RelatorioModelosProduzidosPage` | OK |
| Acabamento | `RELATORIO_ACABAMENTO.py` | `RelatorioAcabamentoPage` | OK |
| Logs e Atividades | `USUARIOS.py` | `UsuariosPage` | OK |
| Usuários | `USUARIOS.py` | `UsuariosPage` | OK |
| Backup | `BACKUP.py` | `BackupPage` | OK |
| Temas | `TEMAS.py` | `TemasPage` | OK |
| Atualizar Sistema | `ATUALIZAR_SISTEMA.py` | `AtualizarSistemaPage` | OK |
| Interna | `PRODUCAO_INTERNA.py` | `ProducaoInternaPage` | OK |
| Enviados | `PRODUCAO_ENVIADOS.py` | `ProducaoEnviadosPage` | OK |
| Retorno | `PRODUCAO_RETORNO.py` | `ProducaoRetornoPage` | OK |
| Finalizados | `PRODUCAO_FINALIZADOS.py` | `ProducaoFinalizadosPage` | OK |
| Gerenciar | `BANCO_DADOS_FABRICA.py` | `BancoDadosFabricaApp` | OK |
| RELATORIOS | `RELATORIO_ENVIO_DETALHADO.py` | `RelatorioEnvioDetalhado` | OK |
| Trocar Usuário | Ação interna | `trocar_usuario` | OK |
| Ordens Planejadas | `ORDENS_PLANEJADAS.py` | `OrdensPlanejadasPage` | OK |

## 5. Fluxo operacional por setor

### Dashboard

Status: OK técnico.  
Validação: rota, importação, classe, banco conectado.  
Observação: atualização visual de cards/gráficos deve ser conferida manualmente com dados reais de produção.

### Modelos e ficha técnica

Status: OK técnico.  
Rotas corrigidas:

- `Cadastrar Modelo`: classe real `CadastroModelosApp`.
- `Imprimir Ficha Técnica`: classe real `ImprimirFichasTecnicasPage`.

Observação: teste validou carregamento técnico. Impressão/PDF da ficha deve ser testada visualmente com um modelo real preenchido.

### Ordens e cortes

Status: OK técnico e OK no fluxo sintético.

Fluxo coberto:

- Cadastro de corte.
- Envio de corte.
- Retorno.
- Entrada/acabamento.
- Finalização.
- Pagamento.
- Rastreamento pela Busca Profunda Corte.

Correção feita:

- `Consultar Ordens`: classe real `OrdemCorteFinalizada`.
- Nova rota `Busca Profunda Corte` criada e validada.

### Prestadores e serviços

Status: OK técnico.

Correção feita:

- `Pesquisar Serviço`: classe real `HistoricoServicosPage`.

Observação: cadastro real de prestador não foi criado neste relatório para evitar alterar base operacional.

### Estoque

Status: OK técnico e OK no fluxo sintético.

Fluxo coberto:

- Entrada temporária de tecido.
- Baixa de metros.
- Atualização de saldo.
- Sincronização `quantidade = metros`.
- Limpeza do item de teste.

Correção/migração feita:

- `estoque_tecidos` agora possui colunas compatíveis com relatórios: `quantidade`, `categoria`, `tipo`, `status`.
- Gatilho mantém `quantidade` sincronizada quando `metros` muda.

### Mão de obra e acabamento

Status: OK técnico e OK no fluxo sintético.

Correção feita:

- `Registro Acabamento`: classe real `RetornoCortes`.

Observação: o fluxo sintético validou vínculos principais. Conferência visual de grade por tamanho deve ser feita com corte real.

### Financeiro

Status: OK técnico e OK no vínculo de pagamento sintético.

Fluxo coberto:

- Criação temporária de pagamento em `pagamento_servicos`.
- Vínculo em `pagamento_servicos_detalhe`.
- Marcação de corte finalizado como pago.
- Rastreamento do pagamento pela busca profunda.

Observação: recibos e impressão de pagamento foram validados por rota/importação, não por impressora física.

### Relatórios e impressões

Status: OK técnico.

Páginas com funções de impressão/exportação localizadas por análise de código:

- Consultar Ordens / ordem de corte em PDF.
- Ordens de Corte Impressão.
- Imprimir Ficha Técnica.
- Controle de Mão de Obra.
- Finalização de Corte / relatório HTML/PDF.
- Pagamento de Serviços / recibos.
- Adiantamentos Pendentes / PDF.
- Relatórios de estoque, produção, acabamento, serviços externos e modelos produzidos.
- Usuários / relatório de atividades HTML.
- Busca Profunda Corte / relatório HTML imprimível.

Observação: a geração visual dos PDFs/HTMLs deve ser validada em ambiente com dados reais e impressora/visualizador configurados.

## 6. Problemas encontrados e correções aplicadas

| Problema | Impacto | Correção |
|---|---|---|
| 6 classes incorretas no `route_map.json` | Páginas podiam depender de fallback ao abrir | Rotas atualizadas para classes reais |
| `estoque_tecidos` sem `quantidade/categoria` no banco instalado | Relatórios antigos poderiam quebrar | Migração adicionada e aplicada |
| `quantidade` podia ficar divergente de `metros` | Dashboard/relatórios poderiam mostrar saldo errado | Gatilho criado para sincronizar |
| Necessidade de rastrear corte por código | Não havia visão única do fluxo completo | Página `Busca Profunda Corte` criada |
| Permissão da nova página ausente | Usuários comuns não veriam a tela | Permissão `busca_profunda_corte` adicionada |

## 7. Riscos remanescentes

1. Teste gráfico completo não foi feito com cliques em cada tela.
2. Impressão física/PDF visual não foi validada página por página.
3. O banco local estava sem dados reais de produção; fluxos foram testados com dados temporários.
4. Existe aviso de ambiente Python: `PyFPDF` e `fpdf2` aparecem instalados ao mesmo tempo. Isso pode causar conflito em geração de PDF.
5. Algumas páginas possuem lógica extensa e consultas dinâmicas; mesmo com import/schema OK, podem existir erros apenas em botões específicos com dados reais.

## 8. Recomendação de próximo ciclo

Para fechar homologação operacional, executar manualmente com um usuário administrador:

1. Cadastrar um modelo real.
2. Imprimir ficha técnica do modelo.
3. Criar ordem/corte real.
4. Cadastrar prestador real.
5. Enviar corte para prestador.
6. Registrar retorno/acabamento.
7. Finalizar corte.
8. Gerar pagamento.
9. Emitir recibo/relatório.
10. Pesquisar o código na `Busca Profunda Corte`.
11. Conferir Dashboard e relatórios após cada etapa.

Critério de aprovação recomendado:

- Código do corte aparece em todas as etapas corretas.
- Dashboard muda após cadastro/envio/finalização/pagamento.
- Relatórios mostram os mesmos totais das telas operacionais.
- Impressões/PDFs carregam os dados corretos.
- Estoque reduz/aumenta conforme entradas e baixas.
## Rodada Extensiva de Homologação - 25/06/2026

### Escopo executado

- Carregamento de todas as rotas pelo mesmo padrão do menu principal.
- Verificação de widgets principais das páginas, incluindo `Entry`, botões e tabelas.
- Leitura de todos os objetos do schema `opera`.
- Simulação de fluxo operacional com gravação, leitura, atualização e rollback.
- Teste de rastreamento do corte por código.
- Teste de geração de arquivos de impressão em HTML/PDF.
- Compilação de todos os arquivos Python em `PAGINAS_DO_SISTEMA`.

### Resultado de carregamento de páginas

- `route_map.json`: OK.
- Páginas carregáveis: 46.
- Ações especiais sem página própria: 1 (`Trocar Usuário`).
- Falhas finais de carregamento: 0.

Páginas carregadas na rodada:

- Dashboard
- Entrada de Estoque
- Saída de Estoque
- Relatórios
- Cadastrar Modelo
- Imprimir Ficha Técnica
- Nova Ordem
- Ordens de Corte Impressão
- Cadastrar Corte
- Consultar Ordens
- Busca Profunda Corte
- Compras
- Cadastro de Prestadores
- Pesquisar Serviço
- Clientes
- Retrabalho de Defeitos
- Controle de Mão de Obra
- MRP
- Planejamento de Produção
- Custos Reais
- Registro Acabamento
- Finalizar Corte / Acabamento
- Pagamento de Serviços
- Recibos de Pagamentos
- Custo Produto
- Folha Pagamento
- Fechamento Mensal
- Contas a Pagar
- Adiantamento
- Adiantamentos Pendentes
- Produção
- Serviços Externos
- Modelos Produzidos
- Acabamento
- Logs e Atividades
- Usuários
- Backup
- Temas
- Atualizar Sistema
- Interna
- Enviados
- Retorno
- Finalizados
- Gerenciar
- RELATORIOS
- Ordens Planejadas

### Resultado de leitura do banco

- Objetos lidos no schema: 73.
- Falhas de leitura em tabelas/views: 0.

Foram lidos todos os objetos encontrados em `information_schema.tables` para o schema `opera`, incluindo tabelas base e views.

### Fluxo operacional simulado

O teste simulou trabalho real do usuário com dados sintéticos e rollback ao final:

- Cadastro de prestador: salvar, carregar e atualizar.
- Cadastro de cliente: salvar e carregar.
- Compras: fornecedor, pedido e recebimento.
- Estoque de tecidos: entrada, sincronização `metros -> quantidade` e baixa.
- Estoque de aviamentos: entrada e baixa.
- Estoque de insumos: entrada e atualização.
- Saída de estoque: registro em `estoque_saida_log`.
- Cadastro de modelo: cabeçalho, tecido, aviamento e serviço.
- Ficha técnica: itens vinculados ao modelo.
- Cadastro de corte: ordem, tecido e lote.
- Controle de mão de obra: envio e grade por tamanho.
- Retorno/acabamento: retorno, entrada de acabamento e detalhes.
- Retrabalho de defeitos: salvar e finalizar defeito.
- Finalização do corte: registro em `cortes_finalizados`.
- Adiantamento de facção: salvar e carregar.
- Pagamento de serviços: salvar pagamento, detalhe e marcar como pago.
- Recibos/contas/folha/fechamento: leitura dos registros financeiros gerados.
- Usuários, permissões, temas e logs: salvar e carregar.

### Rastreamento do corte

O rastreamento por código localizou o corte nas etapas:

- `cadastro_de_corte`
- `controle_envio_cortes`
- `envios_cortes`
- `controle_retorno_cortes`
- `entrada_acabamento`
- `cortes_finalizados`
- `pagamento_servicos`

Resultado: OK.

### Impressão e exportação

Testes executados sem acionar impressora física:

- Busca Profunda Corte: HTML de impressão gerado e conteúdo validado.
- Cadastro de Modelo/Ficha Técnica: PDF gerado e validado como não vazio.
- Compras: PDF gerado e validado como não vazio.

Artefatos de teste removidos após validação.

### Falhas encontradas durante a rodada

1. `USUARIOS.py` gerava `tuple index out of range` em consultas com `ILIKE '%login%'`.

   Causa: `_fetch_one` e `_fetch_all` executavam SQL sem parâmetros usando `params or ()`. Com SQL contendo `%`, o `psycopg2` tentava interpretar o `%` como placeholder.

   Correção aplicada: quando `params is None`, executar `cur.execute(sql)`; quando há parâmetros, executar `cur.execute(sql, params)`.

2. Teste de tema falhou inicialmente por JSON inválido.

   Causa: o teste enviou chaves antigas (`cor_fundo`, `cor_texto`). O contrato correto do banco exige `primaria`, `fundo` e `texto`.

   Correção no teste: payload ajustado para o contrato real da tela de Temas. Resultado final OK.

3. Teste de estoque falhou inicialmente por níveis inválidos.

   Causa: tentativa de inserir `estoque_ideal=0` e `estoque_minimo=5`. A regra correta exige níveis coerentes.

   Correção no teste: entrada refeita com `estoque_ideal >= estoque_minimo >= estoque_critico`. Resultado final OK.

4. Teste de saída de estoque falhou inicialmente por usar nomes genéricos de coluna.

   Causa: o teste tentou inserir em `tabela` e `quantidade_retirada`, mas a tabela real usa `tipo_estoque`, `item_id`, `quantidade`, `motivo`, `observacoes` e `usuario`.

   Correção no teste: registro refeiro no formato real da tela. Resultado final OK.

### Validações finais

- `python -m compileall -q PAGINAS_DO_SISTEMA`: OK.
- `python -m json.tool PAGINAS_DO_SISTEMA\route_map.json`: OK.
- Leitura de 73 objetos do banco: OK.
- Carregamento GUI de 46 páginas: OK.
- Busca profunda com permissão para admin: OK.
- Impressões testadas: OK.

### Ajuste pós-rodada: biblioteca de PDF

- Mantido `fpdf2==2.8.5`, conforme `requirements.txt`.
- Removido pacote antigo `fpdf 1.7.2`/PyFPDF do ambiente.
- Reinstalado `fpdf2` para restaurar corretamente o namespace `fpdf`.
- Dependências realinhadas ao projeto: `Pillow==12.1.0`, `fonttools==4.61.1`, `defusedxml==0.7.1`.
- Removido `pyimage2pdf`, que não era usado pelo sistema e prendia `Pillow==11.0.0`.
- Validação final: `from fpdf import FPDF` OK, PDF gerado sem warnings e `pip check` sem requisitos quebrados.

### Pendências observadas

- A tela de Backup registra que `ready_check` retorna `False`, mas a conexão direta com PostgreSQL funciona e a página carrega. Isso não bloqueou o teste, mas vale revisar depois como melhoria de diagnóstico.
