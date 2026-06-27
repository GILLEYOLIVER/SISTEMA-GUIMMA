-- Exemplos para testar no banco D1.
-- Ajuste os emails/datas antes de usar em cliente real.

INSERT INTO clientes_licencas (
  email,
  customer_name,
  plan,
  status,
  valid_until,
  notes
) VALUES (
  'cliente@empresa.com.br',
  'Cliente Exemplo',
  'mensal',
  'active',
  '2026-07-27T23:59:59Z',
  'Cliente de teste'
)
ON CONFLICT(email) DO UPDATE SET
  customer_name = excluded.customer_name,
  plan = excluded.plan,
  status = excluded.status,
  valid_until = excluded.valid_until,
  notes = excluded.notes,
  updated_at = CURRENT_TIMESTAMP;
