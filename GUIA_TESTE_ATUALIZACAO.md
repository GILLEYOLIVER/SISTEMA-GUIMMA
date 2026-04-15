# Guia de teste do fluxo de atualização (OPERA)

Este guia explica **como o fluxo deve funcionar** e como você pode validar ponta a ponta.

## 1) O que o fluxo faz (resumo)

Quando você clica em **Atualizar Sistema**:

1. A tela chama o `OPERA_UPDATER.py` externo.
2. O updater valida pacote (`manifest.json`, versão, estrutura, hash opcional).
3. O updater cria/garante tabelas de controle no banco.
4. Registra histórico inicial (`app_update_history`).
5. Adquire lock (`app_update_lock`) para impedir atualização concorrente.
6. Gera backup dos arquivos (`backup_versoes/...`) e registra em `app_backups`.
7. Copia arquivos da release para a aplicação.
8. Executa migrações (`MIGRATIONS/*.py`) e registra cada uma em `schema_migrations`.
9. Atualiza `_schema_info`.
10. Finaliza como `CONCLUIDO`.
11. Em falha, restaura backup, marca rollback e finaliza como `RESTAURADO` (ou `FALHOU` se rollback falhar).

---

## 2) Pré-requisitos para testar

- Banco PostgreSQL acessível pela configuração atual do OPERA.
- Dependências Python instaladas no ambiente do app (incluindo `psycopg2`).
- Pasta da aplicação com permissão de escrita (para backup/cópia/`update_state.json`/`update_result.json`).

Pacote de teste recomendado:

```text
RELEASE_TESTE/
├── manifest.json
├── APP/
│   └── ...arquivos da aplicação...
└── MIGRATIONS/
    └── 001_teste_ok.py
```

### Exemplo mínimo de `manifest.json`

```json
{
  "version": "1.1.0",
  "channel": "stable",
  "requires_schema": true,
  "min_supported_version": "1.0.0"
}
```

> Se você incluir `package_sha256`, ele deve bater com o hash da árvore da pasta do pacote.

---

## 3) Teste de sucesso (happy path)

### 3.1 Executar atualização

Pelo CLI (equivalente ao que a tela chama):

```bash
python OPERA_UPDATER.py \
  --apply /CAMINHO/RELEASE_TESTE \
  --app-root /CAMINHO/DA/APLICACAO \
  --current-version 1.0.0 \
  --user-id 1 \
  --user-name admin
```

### 3.2 Resultado esperado em arquivos

- `update_state.json`: status final `completed`.
- `update_result.json`: `"ok": true` e nova versão.
- Nova pasta em `backup_versoes/` criada.

### 3.3 Resultado esperado no banco

1. `app_update_history`: uma linha da execução com status final `CONCLUIDO`.
2. `app_update_lock`: lock `OPERA_SYSTEM_UPDATE` deve terminar com `locked = false`.
3. `app_backups`: backup criado com `backup_nome` único.
4. `schema_migrations`: migrações com `SUCESSO`.
5. `_schema_info`: versão atualizada para a versão alvo.

Consultas úteis:

```sql
SELECT id, status, etapa_atual, version_from, version_to, rollback_executado, rollback_sucesso, iniciado_em, concluido_em
FROM opera.app_update_history
ORDER BY id DESC
LIMIT 5;

SELECT lock_name, locked, machine_name, process_id, version_target, acquired_at, expires_at
FROM opera.app_update_lock
WHERE lock_name = 'OPERA_SYSTEM_UPDATE';

SELECT id, backup_nome, version_origem, status, restore_usado, criado_em
FROM opera.app_backups
ORDER BY id DESC
LIMIT 5;

SELECT id, migration_name, status, erro, iniciado_em, finalizado_em
FROM opera.schema_migrations
ORDER BY id DESC
LIMIT 20;

SELECT schema_name, versao, atualizado_em
FROM opera._schema_info;
```

---

## 4) Teste de falha + rollback

## 4.1 Forçar falha

Crie uma migração em `MIGRATIONS/999_forcar_erro.py` com exceção proposital:

```python
raise RuntimeError("ERRO_FORCADO_TESTE")
```

Rode o mesmo comando de update.

### 4.2 Resultado esperado

- `update_result.json` com `"ok": false`.
- `update_state.json` com `restored_after_failure` (se rollback funcionou).
- `app_update_history` com status final `RESTAURADO` (ou `FALHOU` se rollback falhar).
- `rollback_executado = true` e `rollback_sucesso = true`.
- `app_update_lock.locked = false` após finalizar.

---

## 5) Teste de lock concorrente

Objetivo: validar que não permite duas atualizações simultâneas.

1. Dispare uma atualização longa (com migração que demora).
2. Antes de terminar, tente iniciar outra atualização.

Resultado esperado:

- Segunda tentativa deve falhar com mensagem de lock concorrente.
- Apenas uma execução ativa por vez.

---

## 6) Teste de validação de versão/hash

## 6.1 Versão mínima

No `manifest.json`, coloque:

```json
"min_supported_version": "9.0.0"
```

e rode com `--current-version 1.0.0`.

Esperado: falha de validação antes de copiar arquivos.

## 6.2 Hash inválido

Defina `package_sha256` incorreto.

Esperado: falha de integridade antes da aplicação.

---

## 7) Restauração manual

```bash
python OPERA_UPDATER.py --restore-latest --app-root /CAMINHO/DA/APLICACAO
```

Esperado:

- `update_result.json` com `ok: true`.
- `app_backups.restore_usado = true` para o backup restaurado.
- Entrada de histórico com status `RESTAURADO`.

---

## 8) Checklist final de aceitação

- [ ] Atualização de sucesso conclui com `CONCLUIDO`.
- [ ] Falha em migração executa rollback e marca `RESTAURADO`.
- [ ] Lock sempre é liberado ao final.
- [ ] Histórico e backups ficam rastreáveis no banco.
- [ ] Migrações ficam auditadas (`schema_migrations`).
- [ ] `_schema_info` reflete versão final.

