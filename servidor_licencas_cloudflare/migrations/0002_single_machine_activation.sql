CREATE TABLE IF NOT EXISTS ativacoes_licenca (
  email TEXT PRIMARY KEY,
  machine_id TEXT NOT NULL,
  hostname TEXT DEFAULT '',
  system TEXT DEFAULT '',
  release TEXT DEFAULT '',
  architecture TEXT DEFAULT '',
  activated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ativacoes_licenca_machine_id
ON ativacoes_licenca(machine_id);
