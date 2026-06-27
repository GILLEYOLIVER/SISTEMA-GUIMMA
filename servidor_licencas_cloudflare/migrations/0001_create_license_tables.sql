CREATE TABLE IF NOT EXISTS clientes_licencas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  customer_name TEXT DEFAULT '',
  plan TEXT DEFAULT 'mensal',
  status TEXT NOT NULL DEFAULT 'inactive',
  valid_until TEXT,
  last_payment_at TEXT,
  notes TEXT DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clientes_licencas_email
ON clientes_licencas(email);

CREATE INDEX IF NOT EXISTS idx_clientes_licencas_status
ON clientes_licencas(status);

CREATE TABLE IF NOT EXISTS consultas_licenca (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  machine_id TEXT DEFAULT '',
  hostname TEXT DEFAULT '',
  system TEXT DEFAULT '',
  release TEXT DEFAULT '',
  architecture TEXT DEFAULT '',
  decision TEXT NOT NULL,
  message TEXT DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_consultas_licenca_email
ON consultas_licenca(email);

CREATE INDEX IF NOT EXISTS idx_consultas_licenca_created_at
ON consultas_licenca(created_at);
