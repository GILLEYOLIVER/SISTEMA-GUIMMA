# Servidor de Licencas - Sistema Guimma

Servidor Cloudflare Worker + banco Cloudflare D1 para validar licencas por email.
Cada email pode ter apenas um computador ativo por vez.

Painel web administrativo:

```text
https://sistema-guimma-licencas.sistemaguimma.workers.dev/admin
```

O painel permite consultar, ativar, renovar, bloquear e liberar o computador vinculado a uma licenca.
A senha administrativa fica no segredo `ADMIN_PASSWORD` do Worker.

O licenciador do Sistema Guimma chama:

```text
POST /api/licenses/check
```

com:

```json
{
  "app": "SistemaGuimma",
  "customer_email": "cliente@empresa.com.br",
  "machine": {
    "machine_id": "...",
    "hostname": "...",
    "system": "Darwin"
  }
}
```

e recebe:

```json
{
  "status": "active",
  "valid_until": "2026-07-27T23:59:59Z",
  "customer_email": "cliente@empresa.com.br",
  "customer_name": "Cliente Exemplo",
  "plan": "mensal",
  "message": "Assinatura ativa neste computador.",
  "activation": {
    "machine_id": "...",
    "hostname": "macbook",
    "system": "Darwin",
    "activated_at": "2026-06-27 03:20:00",
    "last_seen_at": "2026-06-27 03:20:00"
  }
}
```

Se o mesmo email ja estiver ativo em outro computador, o retorno sera:

```json
{
  "status": "already_active",
  "message": "Licenca ja ativa em outro computador. Desative a licenca no computador atual antes de ativar neste."
}
```

## Como publicar

Use Node/Wrangler. Neste Mac, se `node` nao estiver no PATH normal, use o runtime do Codex ou instale Node via Homebrew depois.

1. Entrar na pasta:

```bash
cd servidor_licencas_cloudflare
```

2. Instalar dependencias:

```bash
pnpm install
```

3. Login na Cloudflare:

```bash
pnpm wrangler login
```

O navegador vai abrir. Digite seu email/senha direto na Cloudflare.

4. Criar banco D1:

```bash
pnpm wrangler d1 create sistema_guimma_licencas
```

Copie o `database_id` gerado e coloque em `wrangler.toml`.

5. Criar as tabelas:

```bash
pnpm wrangler d1 migrations apply sistema_guimma_licencas --remote
```

6. Criar token administrativo:

```bash
pnpm wrangler secret put ADMIN_TOKEN
```

Digite um token grande, por exemplo uma frase/senha longa. Esse token serve para cadastrar/renovar clientes pela API admin.

7. Criar senha do painel web:

```bash
pnpm wrangler secret put ADMIN_PASSWORD
```

8. Publicar:

```bash
pnpm wrangler deploy
```

O deploy vai gerar uma URL parecida com:

```text
https://sistema-guimma-licencas.SEUSUBDOMINIO.workers.dev
```

No licenciador, a URL do servidor deve ser essa URL base.

## Cadastrar cliente manualmente

Depois do deploy, troque `URL_DO_WORKER` e `SEU_TOKEN_ADMIN`:

```bash
curl -X POST "URL_DO_WORKER/api/admin/customers/upsert" \
  -H "Authorization: Bearer SEU_TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "cliente@empresa.com.br",
    "customer_name": "Cliente Exemplo",
    "plan": "mensal",
    "status": "active",
    "days": 30,
    "notes": "Primeiro teste"
  }'
```

## Renovar por mais 30 dias

```bash
curl -X POST "URL_DO_WORKER/api/admin/customers/extend" \
  -H "Authorization: Bearer SEU_TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "cliente@empresa.com.br",
    "days": 30
  }'
```

## Liberar computador pelo painel/admin

Use isso apenas em atendimento, por exemplo quando o computador do cliente quebrou e ele nao consegue clicar em `Desativar`.

```bash
curl -X POST "URL_DO_WORKER/api/admin/customers/release" \
  -H "Authorization: Bearer SEU_TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "cliente@empresa.com.br"
  }'
```

## Testar consulta do licenciador

```bash
curl -X POST "URL_DO_WORKER/api/licenses/check" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "cliente@empresa.com.br",
    "machine": {
      "machine_id": "teste",
      "hostname": "macbook",
      "system": "Darwin"
    }
  }'
```

## Desativar no computador atual

```bash
curl -X POST "URL_DO_WORKER/api/licenses/deactivate" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "cliente@empresa.com.br",
    "machine": {
      "machine_id": "teste",
      "hostname": "macbook",
      "system": "Darwin"
    }
  }'
```

## Observacao de seguranca

Esta versao ja evita lista publica de emails e centraliza tudo em API + banco.
O proximo reforco recomendado e assinar a resposta do servidor, para o licenciador aceitar apenas respostas geradas por voce.
