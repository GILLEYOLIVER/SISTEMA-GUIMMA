# 📘 SISTEMA OPERA  
**ERP Profissional para Moda, Produção, Corte, Facções e Gestão Integrada**

O **SISTEMA OPERA** é um ERP moderno desenvolvido em **Python + CustomTkinter + PostgreSQL**, projetado para gestão completa de empresas do setor de **confecção, moda, corte, produção, facções, estoque e financeiro**.

Ele possui **interface moderna**, **sistema avançado de temas**, **permissões por usuário**, **pré-carregamento inteligente**, módulos integrados e arquitetura otimizada para **alto desempenho em Windows e macOS**.

---

## 📌 Índice

- [Sobre o Sistema](#-sobre-o-sistema)
- [Tecnologias Utilizadas](#%EF%B8%8F-tecnologias-utilizadas)
- [Principais Funcionalidades](#-principais-funcionalidades)
- [Novas Funcionalidades e Módulos](#-novas-funcionalidades-e-módulos)
- [Arquitetura do Sistema](#-arquitetura-do-sistema)
- [Banco de Dados PostgreSQL](#%EF%B8%8F-banco-de-dados-postgresql)
  - [Tabelas principais](#tabelas-principais)
  - [Novas Tabelas Implementadas](#novas-tabelas-implementadas)
- [Sistema de Permissões](#-sistema-de-permissões)
- [Sistema de Temas](#-sistema-de-temas)
- [Pré-Carregamento (Splash)](#-pré-carregamento-splash)
- [Backup Automático](#-backup-automático)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Módulo DEFpy - Ordem de Corte](#-módulo-defpy---ordem-de-corte)
- [Como Rodar o Sistema](#%EF%B8%8F-como-rodar-o-sistema)
- [Requisitos](#-requisitos)
- [Configurações Extras](#-configurações-extras)
- [Instalador para Windows e macOS](#-instalador-para-windows-e-macos)
- [Notas sobre Testes nas Mensagens](#-notas-sobre-testes-nas-mensagens)
- [Contribuições](#-contribuições)
- [Licença](#-licença)

---

## 🧵 Sobre o Sistema

O **SISTEMA OPERA** foi criado para atender empresas do setor têxtil e confecção, oferecendo controle total sobre:

- Corte e produção  
- Modelos e grades  
- Facções externas  
- Mão de obra  
- Custos  
- Estoque  
- Relatórios  
- Ordens de produção  
- Administração de usuários  
- Permissões completas  
- Temas personalizados  
- Auditoria de ações  

---

## 🛠️ Tecnologias Utilizadas

| Tecnologia   | Descrição                          |
|-------------|-------------------------------------|
| **Python**  | Lógica e backend do sistema         |
| **CustomTkinter** | Interface gráfica moderna    |
| **PIL / Pillow**  | Manipulação de imagens e ícones |
| **PostgreSQL**    | Banco de dados relacional    |
| **psycopg2 / asyncpg** | Conexão com o banco     |
| **ReportLab**     | Geração de PDFs              |
| **Threading**     | Pré-carregamento inteligente |
| **JSON**          | Preferências e cache         |

---

## ⭐ Principais Funcionalidades

- ✔️ **Login seguro com auditoria**
- ✔️ **Dashboard profissional** com indicadores de produção e financeiro
- ✔️ **Menu lateral moderno** com ícones e acesso rápido aos módulos operacionais
- ✔️ **Temas personalizados por usuário**
- ✔️ **Sistema completo de permissões**
- ✔️ **Backup automático do banco**
- ✔️ **Carregamento de páginas dinâmico**
- ✔️ **Sistema de cache inteligente**
- ✔️ **Relatórios e módulos de produção integrados**
- ✔️ **Logs completos no PostgreSQL**
- ✔️ **Splash Screen com barra dinâmica de progresso**

---

## 🆕 Novas Funcionalidades e Módulos

- **Controle de estoque completo**  
  Entrada, saída e balanço com histórico detalhado:  
  `ENTRADA_ESTOQUE.py`, `SAIDA_ESTOQUE.py`, `RELATORIO_ESTOQUE.py`.

- **Precificação de produtos**  
  Cálculo de custos, margens e simulações:  
  `PRECIFICACAO_PRODUTO.py`.

- **Gestão financeira ampliada**  
  Contas a pagar, adiantamentos e pagamentos de serviços:  
  `CONTAS_A_PAGAR.py`, `ADIANTAMENTO_PAGE.py`, `PAGAMENTO_SERVICOS.py`.

- **Administração de facções e serviços externos**  
  Cadastro, consulta e relatórios para parceiros produtivos:  
  `CADASTRO_FACCOES.py`, `CONSULTAR_SERVICOS.py`, `RELATORIO_SERVICOS_EXTERNOS.py`.

- **Operações de corte e produção**  
  Cadastro e acompanhamento de ordens, envio e retorno de cortes, finalização e relatórios:  
  `CADASTRO_DE_CORTE.py`, `CONTROLE_ENVIO_CORTES.py`, `CONTROLE_RETORNO_CORTE.py`,  
  `FINALIZAR_CORTE_ACABAMENTO.py`, `RELATORIO_ACABAMENTO.py`, `RELATORIO_MODELOS_PRODUZIDOS.py`.

- **Ferramentas de auditoria e logging**  
  Monitoramento centralizado de eventos do sistema:  
  `LOG_SISTEMA.py` + persistência de logs no banco.

- **Rotinas de limpeza e manutenção**  
  Utilitário de inicialização limpa para resolver inconsistências de configuração:  
  `start_clean.py`.

---

## 🧩 Arquitetura do Sistema

Arquitetura **modular**, com:

- Carregamento dinâmico de páginas  
- Tema global aplicado no menu e em todos os módulos  
- Permissões automáticas por usuário e por página  
- Organização em camadas: interface, serviços, banco de dados e utilitários  

---

## 🗄️ Banco de Dados PostgreSQL

### Tabelas principais

Algumas das tabelas centrais:

- `usuarios`
- `usuario_permissoes`
- `usuario_preferencias`
- `temas_personalizados`
- `auditoria`
- `modelos`
- `ordens`
- `producao`
- `faccoes`
- `materiais`
- `estoque`
- `backup_logs`

### 📊 Novas Tabelas Implementadas

#### Gestão de Corte e Ordem de Produção

- **`ordem_grade_preferencias` (Tabela 48)**  
  Armazena preferências de grade por usuário com porcentagens personalizadas para tamanhos **PP–G3**.

- **`ordem_corte_ficha`**  
  Guarda fichas completas de ordem de corte com todas as informações de produção.

- **`cadastro_de_corte`**  
  Registro centralizado de ordens de corte emitidas.

#### Sistema de Porcentagens

- **`config_porcentagem_modelo`**  
  Configurações padrão de porcentagem por modelo.

- **Campos de porcentagem nas tabelas de modelos**  
  - `cadastro_modelos_cabecalho`  
  - `ficha_tecnica_cabecalho`  

---

## 🔐 Sistema de Permissões

- Permissões **por página** e por usuário:
  - Ver
  - Editar
  - Excluir
  - Imprimir
  - Administrar

- Aplicação automática em todas as páginas, integrando com:
  - `USUARIOS.py`
  - `MENU_PRINCIPAL.py`
  - Tabela `usuario_permissoes` no PostgreSQL

---

## 🎨 Sistema de Temas

- Temas padrão completos
- Temas personalizados por usuário
- Aplicação global automática (Menu + páginas internas)
- Editor visual de cores integrado
- Persistência de tema em `usuario_preferencias` e `temas_personalizados`

---

## ⚡ Pré-Carregamento (Splash)

- Tela de **Splash Screen** com:
  - Barra de progresso dinâmica real
  - Mensagens de status por módulo
  - Fechamento automático ao atingir **100%**
- Otimizado para:
  - Pré-carregar conexões
  - Carregar ícones, temas e configurações

---

## 💾 Backup Automático

- Mantém até **300 versões** de backup
- Remove o backup mais antigo automaticamente
- Funciona em **Windows** e **macOS**
- Integração com:
  - Diretório `backup_banco/`
  - Logs em `backup_logs` no PostgreSQL

---

## 📁 Estrutura do Projeto

```text
SISTEMA OPERA/
│── MENU_PRINCIPAL.py
│── LOGUIN.py
│── SPLASH.py
│── BANCO_DE_DADOS_PG.py
│── USUARIOS.py
│── TEMAS.py
│── DEF.py     # Módulo completo de Ordem de Corte
│── icons/
│── backup_banco/
│── config.json
│── README.md
```

---

## 🔧 Módulo DEF.py - Ordem de Corte

O módulo `DEF.py` implementa um sistema completo de gestão de **ordens de corte**, com as seguintes características:

### ✅ Funcionalidades Principais

- Interface moderna com **CustomTkinter**
- Busca inteligente de modelos por **código ou descrição**
- **Grade de corte configurável** com 8 tamanhos (PP a G3)
- Sistema de **preferências de grade por usuário**
- Integração com **PostgreSQL**
- Geração automática de **PDF para impressão**
- Validação e formatação automática de dados

### 🎯 Características Técnicas

- **Formatação inteligente de números**  
  Converte automaticamente valores como `"34.00"` para `"34"` (inteiros) quando apropriado.
- **Persistência de preferências**  
  Salva configurações de grade por usuário em tabela dedicada.
- **Carregamento dinâmico**  
  Busca modelos diretamente do banco de dados.
- **Temas personalizáveis**  
  Integração completa com o sistema de temas do OPERA.
- **Backup automático**  
  Salva ordens no banco de dados.
- **Logs detalhados**  
  Registra operações para auditoria.

### 🔄 Fluxo de Trabalho

1. Busca de modelo por código ou descrição  
2. Preenchimento automático dos dados  
3. Configuração das porcentagens de grade (com opção de salvar como preferência)  
4. Definição de cortador, auxiliar e datas  
5. Geração de PDF para impressão  
6. Salvamento automático no banco de dados  

---

## ▶️ Como Rodar o Sistema

### 1. Instale as dependências

```bash
pip install -r requirements.txt
```

### 2. Configure o PostgreSQL e variáveis de ambiente

Ajuste a **DSN** e o **schema**:

```bash
OPERA_PG_DSN="postgres://user:senha@localhost:5432/BANCO_OPERA"
OPERA_PG_SCHEMA="opera"
```

> Substitua `user`, `senha`, `localhost` e `BANCO_OPERA` conforme a sua configuração.

### 3. Execute o sistema principal

```bash
python LOGUIN.py
```

### 4. Executar o módulo de Ordem de Corte separadamente

```bash
python DEF.py
```

---

## 💻 Requisitos

- **Python 3.12+**
- **PostgreSQL 14+**
- **Windows 10/11** ou **macOS Sonoma+**

---

## ⚙️ Configurações Extras

- Cache avançado de dados
- Preferências por usuário (tema, configurações visuais, etc.)
- Ajustes finos em `config.json`
- Formatação automática de números no módulo de corte

---


## 🧪 Notas sobre Testes nas Mensagens

Em português claro:

> ⚠️ **Not run (not requested)** significa que os testes automatizados **não foram executados por opção** de quem solicitou a entrega.

- Não é erro nem falha de teste.  
- Apenas registra que os testes ficaram de fora naquela execução.

Também foi conferido que o arquivo `DEF.py` está completo, com:

- ✅ Sistema de preferências de grade por usuário  
- ✅ Formatação inteligente de números (inteiros vs. decimais)  
- ✅ Integração completa com banco de dados  
- ✅ Geração de PDF para impressão  
- ✅ Interface responsiva e moderna  

---

## 🤝 Contribuições

Pull requests são bem-vindos.

Sugestões, melhorias e correções podem ser discutidas via issues ou diretamente em PRs.

---

## 📄 Licença

Projeto **proprietário**.  
Uso permitido somente com autorização.
