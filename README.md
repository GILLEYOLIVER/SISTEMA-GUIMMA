
# 📘 README – SISTEMA OPERA  
### ERP Profissional para Moda, Produção, Corte, Facções e Gestão Integrada

O **SISTEMA OPERA** é um ERP moderno desenvolvido em **Python + CustomTkinter + PostgreSQL**, projetado para gestão completa de empresas do setor de **confecção, moda, corte, produção, facções, estoque e financeiro**.

Ele possui interface moderna, sistema avançado de temas, permissões por usuário, pré-carregamento inteligente, módulos integrados e arquitetura otimizada para alto desempenho em **Windows e macOS**.

---

# 📌 ÍNDICE
- Sobre o Sistema
- Tecnologias Utilizadas
- Principais Funcionalidades
- Arquitetura do Sistema
- Banco de Dados PostgreSQL
- Sistema de Permissões
- Sistema de Temas
- Pré-Carregamento (Splash)
- Backup Automático
- Estrutura do Projeto
- Como Rodar o Sistema
- Requisitos
- Configurações Extras
- Contribuições
- Licença

---

# 🧵 Sobre o Sistema

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

# 🛠️ Tecnologias Utilizadas

| Tecnologia | Descrição |
|-----------|-----------|
| **Python** | Lógica e backend do sistema |
| **CustomTkinter** | Interface gráfica moderna |
| **PIL/Pillow** | Manipulação de imagens e ícones |
| **PostgreSQL** | Banco de dados |
| **psycopg2 / asyncpg** | Conexão com o banco |
| **ReportLab** | Geração de PDFs |
| **Threading** | Pré-carregamento inteligente |
| **JSON** | Preferências e cache |

---

# ⭐ Principais Funcionalidades

✔️ Login seguro com auditoria
✔️ Dashboard profissional com indicadores de produção e financeiro
✔️ Menu lateral moderno com ícones e acesso rápido aos módulos operacionais
✔️ Temas personalizados por usuário
✔️ Permissões completas
✔️ Backup automático
✔️ Carregamento de páginas dinâmico
✔️ Sistema de cache inteligente
✔️ Relatórios e módulos de produção
✔️ Logs completos no PostgreSQL
✔️ Splash Screen com barra dinâmica

## 🆕 Novas funcionalidades e módulos

- **Controle de estoque completo**: entrada, saída e balanço com histórico detalhado (`ENTRADA_ESTOQUE.py`, `SAIDA_ESTOQUE.py`, `RELATORIO_ESTOQUE.py`).
- **Precificação de produtos**: cálculo de custos, margens e simulações em `PRECIFICACAO_PRODUTO.py`.
- **Gestão financeira ampliada**: módulos dedicados a contas a pagar, adiantamentos e pagamentos de serviços (`CONTAS_A_PAGAR.py`, `ADIANTAMENTO_PAGE.py`, `PAGAMENTO_SERVICOS.py`).
- **Administração de facções e serviços externos**: cadastro, consulta e relatórios para parceiros produtivos (`CADASTRO_FACCOES.py`, `CONSULTAR_SERVICOS.py`, `RELATORIO_SERVICOS_EXTERNOS.py`).
- **Operações de corte e produção**: cadastro e acompanhamento de ordens, envio e retorno de cortes, finalização e relatórios detalhados (`CADASTRO_DE_CORTE.py`, `CONTROLE_ENVIO_CORTES.py`, `CONTROLE_RETORNO_CORTE.py`, `FINALIZAR_CORTE_ACABAMENTO.py`, `RELATORIO_ACABAMENTO.py`, `RELATORIO_MODELOS_PRODUZIDOS.py`).
- **Ferramentas de auditoria e logging**: monitoramento centralizado de eventos do sistema em `LOG_SISTEMA.py` e persistência de logs no banco.
- **Rotinas de limpeza e manutenção**: utilitário de inicialização limpa para resolver inconsistências de configuração (`start_clean.py`).

---

# 🧩 Arquitetura do Sistema

Arquitetura modular com carregamento dinâmico, tema global e permissões automáticas.

---

# 🗄️ Banco de Dados PostgreSQL

Tabelas principais:  
`usuarios`, `usuario_permissoes`, `usuario_preferencias`, `temas_personalizados`, `auditoria`, `modelos`, `ordens`, `producao`, `faccoes`, `materiais`, `estoque`, `backup_logs`.

---

# 🔐 Sistema de Permissões

Permissões por página: **Ver, Editar, Excluir, Imprimir, Administrar**.

Aplicação automática em todas as páginas.

---

# 🎨 Sistema de Temas

- Temas padrão completos  
- Temas personalizados por usuário  
- Aplicação global automática  
- Editor visual de cores  

---

# ⚡ Pré-Carregamento (Splash)

Barra dinâmica real, carregamento de módulos e fechamento automático ao atingir 100%.

---

# 💾 Backup Automático

- Mantém até 300 versões  
- Remove o backup mais antigo automaticamente  
- Funciona em Windows e macOS  

---

# 📁 Estrutura do Projeto

```
SISTEMA OPERA/
│── MENU_PRINCIPAL.py
│── LOGUIN.py
│── SPLASH.py
│── BANCO_DE_DADOS_PG.py
│── USUARIOS.py
│── TEMAS.py
│── icons/
│── backup_banco/
│── config.json
│── README.md
```

---

# ▶️ Como Rodar o Sistema

1. Instale dependências:  
```
pip install -r requirements.txt
```

2. Configure o PostgreSQL e ajuste:  
```
OPERA_PG_DSN="postgres://user:senha@localhost:5432/BANCO_OPERA"
OPERA_PG_SCHEMA="opera"
```

3. Execute:
```
python LOGUIN.py
```

---

# 🧪 Notas sobre testes nas mensagens

Em português claro:

- ⚠️ **Not run (not requested)** significa que os testes automatizados não foram executados por opção de quem solicitou a entrega.
- Não é erro nem falha de teste; apenas registra que os testes ficaram de fora naquela execução.

Também conferimos que o arquivo `MENU_PRINCIPAL.py` está completo (sem truncamento) e termina corretamente com a chamada ao `main()`, garantindo o carregamento normal do menu principal.

# 💻 Requisitos

- Python 3.12+  
- PostgreSQL 14+  
- Windows 10/11 ou macOS Sonoma+  

---

# ⚙️ Configurações Extras

- Cache avançado  
- Preferências por usuário  
- Ajustes no `config.json`  

---

# 🤝 Contribuições

Pull requests são bem-vindos.

---

# 📄 Licença

Projeto proprietário. Uso permitido somente com autorização.
