# Licenciamento do Sistema Guimma

Esta pasta contem o app/agente separado que valida a assinatura do cliente.

Fluxo previsto:

1. O cliente paga a mensalidade.
2. O gateway de pagamento avisa o seu servidor por webhook.
3. O seu servidor marca a licenca como ativa e calcula a validade, normalmente 30 dias.
4. O app `Sistema Guimma Licenca` consulta o servidor quando nao existir licenca local valida ou quando a licenca local vencer.
5. Na primeira validacao aprovada, o servidor prende a licenca ao ID deste computador.
6. O agente grava um `license_state.json` local, selado para este computador.
7. O Sistema Guimma le esse estado antes do login e libera o uso offline ate a data `valid_until`.

Comportamento de renovacao:

- Se a licenca local ainda esta valida, o sistema abre sem consultar a internet.
- Se a licenca local venceu, o licenciador consulta o servidor.
- Se o servidor confirmar pagamento ativo, grava uma nova validade de 30 dias.
- O botao `Validar agora` força uma consulta imediata ao servidor.
- A mesma licenca nao pode ficar ativa em dois computadores ao mesmo tempo.
- Para trocar de computador, clique em `Desativar` no computador atual e depois valide no novo.

Arquivos principais:

- `app.py`: interface visual para informar servidor/email do cliente e validar manualmente.
- `admin_app.py`: interface administrativa para voce ativar, bloquear, renovar e liberar computador por email.
- `admin_client.py`: cliente da API administrativa do Cloudflare.
- `agent.py`: modo de segundo plano, usado ao iniciar o computador.
- `runtime.py`: usado pelo Sistema Guimma para decidir se pode abrir.
- `store.py`: grava e valida o estado local da licenca.
- `machine.py`: gera o ID do computador.
- `autorun.py`: instala/remover inicializacao automatica no macOS, Windows e Linux.

Tela administrativa:

- `Ativar`: cria ou reativa a assinatura do email pelo numero de dias informado.
- `Renovar`: soma mais dias a uma assinatura existente.
- `Desativar/Bloquear`: bloqueia o acesso por falta de pagamento ou cancelamento.
- `Liberar computador`: mantem a assinatura ativa, mas libera a troca para outro computador.
- `Consultar`: mostra status, validade e o computador atualmente ativo.

Importante: o app administrativo usa o token secreto do Cloudflare. Ele e somente para uso interno e nao deve ser enviado para clientes.

Contrato esperado do servidor:

`POST /api/licenses/check`

Entrada:

```json
{
  "app": "SistemaGuimma",
  "customer_email": "cliente@empresa.com.br",
  "machine": {
    "machine_id": "...",
    "hostname": "...",
    "system": "Darwin",
    "release": "...",
    "architecture": "..."
  }
}
```

Se a licenca ja estiver ativa em outro computador, o servidor retorna:

```json
{
  "status": "already_active",
  "message": "Licenca ja ativa em outro computador. Desative a licenca no computador atual antes de ativar neste."
}
```

`POST /api/licenses/deactivate`

Entrada:

```json
{
  "app": "SistemaGuimma",
  "customer_email": "cliente@empresa.com.br",
  "machine": {
    "machine_id": "..."
  }
}
```

Resposta:

```json
{
  "status": "deactivated",
  "customer_email": "cliente@empresa.com.br",
  "message": "Licenca desativada neste computador."
}
```

Resposta:

```json
{
  "status": "active",
  "valid_until": "2026-07-27T23:59:59Z",
  "customer_email": "cliente@empresa.com.br",
  "customer_name": "Cliente Exemplo",
  "plan": "mensal",
  "message": "Assinatura ativa"
}
```

Comandos uteis em desenvolvimento:

```bash
python3 -m licenciamento.app
python3 -m licenciamento.agent --status
python3 -m licenciamento.agent --sync-once --server-url https://sistema-guimma-licencas.sistemaguimma.workers.dev --customer-email cliente@empresa.com.br --enable
python3 -m licenciamento.agent --deactivate --customer-email cliente@empresa.com.br
python3 -m licenciamento.agent --install-autostart
```

Observacao importante: esta primeira versao sela o estado local para evitar alteracao simples do arquivo. A etapa comercial ideal e o servidor tambem assinar a resposta com chave privada, deixando no cliente apenas a chave publica.
