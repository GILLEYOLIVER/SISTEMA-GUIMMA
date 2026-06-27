const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

const HTML_HEADERS = {
  "content-type": "text/html; charset=utf-8",
  "cache-control": "no-store",
};

const SESSION_COOKIE = "sg_admin_session";
const SESSION_SECONDS = 8 * 60 * 60;

function json(data, status = 200, extraHeaders = {}) {
  const headers = new Headers(JSON_HEADERS);
  for (const [key, value] of Object.entries(extraHeaders)) {
    headers.set(key, value);
  }
  return new Response(JSON.stringify(data, null, 2), { status, headers });
}

function html(markup, status = 200) {
  return new Response(markup, { status, headers: HTML_HEADERS });
}

function normalizeEmail(value) {
  return String(value || "").trim().toLowerCase();
}

function nowIso() {
  return new Date().toISOString();
}

function addDaysIso(days) {
  const amount = Number.parseInt(days || "30", 10);
  const safeDays = Number.isFinite(amount) && amount > 0 ? amount : 30;
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + safeDays);
  date.setUTCHours(23, 59, 59, 0);
  return date.toISOString();
}

function parseDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function bearerToken(request) {
  const auth = request.headers.get("authorization") || "";
  const prefix = "Bearer ";
  if (!auth.startsWith(prefix)) return "";
  return auth.slice(prefix.length).trim();
}

function safeEqual(a, b) {
  const left = String(a || "");
  const right = String(b || "");
  if (left.length !== right.length) return false;
  let result = 0;
  for (let index = 0; index < left.length; index += 1) {
    result |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return result === 0;
}

function getCookie(request, name) {
  const cookie = request.headers.get("cookie") || "";
  for (const part of cookie.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return rest.join("=");
  }
  return "";
}

async function hmacHex(secret, message) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(message));
  return [...new Uint8Array(signature)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function createSessionValue(env, expiresAt) {
  const secret = String(env.ADMIN_TOKEN || "").trim();
  const signature = await hmacHex(secret, String(expiresAt));
  return `${expiresAt}.${signature}`;
}

async function validSession(request, env) {
  const secret = String(env.ADMIN_TOKEN || "").trim();
  if (!secret) return false;
  const value = getCookie(request, SESSION_COOKIE);
  const [expiresAtText, signature] = value.split(".");
  const expiresAt = Number.parseInt(expiresAtText || "0", 10);
  if (!expiresAt || !signature || expiresAt < Math.floor(Date.now() / 1000)) {
    return false;
  }
  const expected = await hmacHex(secret, String(expiresAt));
  return safeEqual(signature, expected);
}

async function requireAdmin(request, env) {
  const expected = String(env.ADMIN_TOKEN || "").trim();
  if (!expected) return false;
  if (safeEqual(bearerToken(request), expected)) return true;
  return validSession(request, env);
}

function sessionCookie(value, maxAge = SESSION_SECONDS) {
  return `${SESSION_COOKIE}=${value}; Max-Age=${maxAge}; Path=/; HttpOnly; Secure; SameSite=Strict`;
}

function clearSessionCookie() {
  return `${SESSION_COOKIE}=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Strict`;
}

async function readJson(request) {
  try {
    return await request.json();
  } catch (_error) {
    return null;
  }
}

async function logConsulta(env, payload) {
  try {
    await env.DB.prepare(
      `INSERT INTO consultas_licenca (
        email,
        machine_id,
        hostname,
        system,
        release,
        architecture,
        decision,
        message
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
    )
      .bind(
        payload.email || "",
        payload.machine_id || "",
        payload.hostname || "",
        payload.system || "",
        payload.release || "",
        payload.architecture || "",
        payload.decision || "",
        payload.message || ""
      )
      .run();
  } catch (_error) {
    // Log nunca deve impedir o cliente de receber resposta.
  }
}

function publicLicenseResponse(row, decision, message, activation = null) {
  return {
    status: decision,
    valid_until: row?.valid_until || null,
    customer_email: row?.email || "",
    customer_name: row?.customer_name || "",
    plan: row?.plan || "",
    message,
    activation: activation
      ? {
          machine_id: activation.machine_id || "",
          hostname: activation.hostname || "",
          system: activation.system || "",
          activated_at: activation.activated_at || "",
          last_seen_at: activation.last_seen_at || "",
        }
      : null,
  };
}

function normalizeMachine(value) {
  const machine = value || {};
  return {
    machine_id: String(machine.machine_id || "").trim(),
    hostname: String(machine.hostname || "").trim(),
    system: String(machine.system || "").trim(),
    release: String(machine.release || "").trim(),
    architecture: String(machine.architecture || "").trim(),
  };
}

async function activationForEmail(env, email) {
  return env.DB.prepare(
    `SELECT email, machine_id, hostname, system, release, architecture, activated_at, last_seen_at
       FROM ativacoes_licenca
      WHERE email = ?`
  )
    .bind(email)
    .first();
}

async function ensureMachineActivation(env, email, machine) {
  if (!machine.machine_id) {
    return {
      ok: false,
      decision: "invalid_machine",
      message: "ID do computador nao informado.",
      activation: null,
    };
  }

  let activation = await activationForEmail(env, email);
  if (!activation) {
    await env.DB.prepare(
      `INSERT OR IGNORE INTO ativacoes_licenca (
        email,
        machine_id,
        hostname,
        system,
        release,
        architecture,
        activated_at,
        last_seen_at
      ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)`
    )
      .bind(
        email,
        machine.machine_id,
        machine.hostname,
        machine.system,
        machine.release,
        machine.architecture
      )
      .run();
    activation = await activationForEmail(env, email);
  }

  if (!activation || activation.machine_id !== machine.machine_id) {
    return {
      ok: false,
      decision: "already_active",
      message:
        "Licenca ja ativa em outro computador. Desative a licenca no computador atual antes de ativar neste.",
      activation,
    };
  }

  await env.DB.prepare(
    `UPDATE ativacoes_licenca
        SET hostname = ?,
            system = ?,
            release = ?,
            architecture = ?,
            last_seen_at = CURRENT_TIMESTAMP
      WHERE email = ? AND machine_id = ?`
  )
    .bind(
      machine.hostname,
      machine.system,
      machine.release,
      machine.architecture,
      email,
      machine.machine_id
    )
    .run();

  return {
    ok: true,
    decision: "active",
    message: "Assinatura ativa neste computador.",
    activation: await activationForEmail(env, email),
  };
}

async function checkLicense(request, env) {
  const body = await readJson(request);
  if (!body) {
    return json({ status: "invalid_request", message: "JSON invalido." }, 400);
  }

  const email = normalizeEmail(body.customer_email || body.email);
  if (!email || !email.includes("@")) {
    return json({ status: "invalid_request", message: "Email do cliente invalido." }, 400);
  }

  const row = await env.DB.prepare(
    `SELECT email, customer_name, plan, status, valid_until
       FROM clientes_licencas
      WHERE email = ?`
  )
    .bind(email)
    .first();

  const machine = normalizeMachine(body.machine);
  const logBase = {
    email,
    machine_id: machine.machine_id,
    hostname: machine.hostname,
    system: machine.system,
    release: machine.release,
    architecture: machine.architecture,
  };

  if (!row) {
    const message = "Email nao encontrado.";
    await logConsulta(env, { ...logBase, decision: "not_found", message });
    return json({
      status: "not_found",
      valid_until: null,
      customer_email: email,
      customer_name: "",
      plan: "",
      message,
    });
  }

  const status = String(row.status || "").toLowerCase();
  if (status !== "active" && status !== "trial") {
    const message = "Licenca nao ativa.";
    await logConsulta(env, { ...logBase, decision: status || "inactive", message });
    return json(publicLicenseResponse(row, status || "inactive", message));
  }

  const validUntil = parseDate(row.valid_until);
  if (!validUntil) {
    const message = "Licenca sem data de validade.";
    await logConsulta(env, { ...logBase, decision: "inactive", message });
    return json(publicLicenseResponse(row, "inactive", message));
  }

  if (validUntil.getTime() < Date.now()) {
    const message = "Licenca vencida.";
    await logConsulta(env, { ...logBase, decision: "expired", message });
    return json(publicLicenseResponse(row, "expired", message));
  }

  const activation = await ensureMachineActivation(env, email, machine);
  if (!activation.ok) {
    await logConsulta(env, {
      ...logBase,
      decision: activation.decision,
      message: activation.message,
    });
    return json(publicLicenseResponse(row, activation.decision, activation.message, activation.activation));
  }

  const decision = status === "trial" ? "trial" : "active";
  const message = activation.message;
  await logConsulta(env, { ...logBase, decision, message });
  return json(publicLicenseResponse(row, decision, message, activation.activation));
}

async function deactivateLicense(request, env) {
  const body = await readJson(request);
  if (!body) {
    return json({ status: "invalid_request", message: "JSON invalido." }, 400);
  }

  const email = normalizeEmail(body.customer_email || body.email);
  if (!email || !email.includes("@")) {
    return json({ status: "invalid_request", message: "Email do cliente invalido." }, 400);
  }

  const machine = normalizeMachine(body.machine);
  const logBase = {
    email,
    machine_id: machine.machine_id,
    hostname: machine.hostname,
    system: machine.system,
    release: machine.release,
    architecture: machine.architecture,
  };

  if (!machine.machine_id) {
    const message = "ID do computador nao informado.";
    await logConsulta(env, { ...logBase, decision: "invalid_machine", message });
    return json({ status: "invalid_machine", customer_email: email, message });
  }

  const activation = await activationForEmail(env, email);
  if (!activation) {
    const message = "Nenhum computador ativo para esta licenca.";
    await logConsulta(env, { ...logBase, decision: "deactivated", message });
    return json({ status: "deactivated", customer_email: email, message });
  }

  if (activation.machine_id !== machine.machine_id) {
    const message = "Esta licenca esta ativa em outro computador e nao pode ser desativada por este.";
    await logConsulta(env, { ...logBase, decision: "deactivate_denied", message });
    return json(publicLicenseResponse({ email }, "deactivate_denied", message, activation));
  }

  await env.DB.prepare(
    `DELETE FROM ativacoes_licenca
      WHERE email = ? AND machine_id = ?`
  )
    .bind(email, machine.machine_id)
    .run();

  const message = "Licenca desativada neste computador.";
  await logConsulta(env, { ...logBase, decision: "deactivated", message });
  return json({ status: "deactivated", customer_email: email, message });
}

async function adminLogin(request, env) {
  const expected = String(env.ADMIN_PASSWORD || "").trim();
  if (!expected) {
    return json({ ok: false, error: "senha_admin_nao_configurada" }, 500);
  }

  const body = await readJson(request);
  const password = String(body?.password || "");
  if (!safeEqual(password, expected)) {
    return json({ ok: false, error: "senha_invalida" }, 401);
  }

  const expiresAt = Math.floor(Date.now() / 1000) + SESSION_SECONDS;
  const value = await createSessionValue(env, expiresAt);
  return json(
    {
      ok: true,
      expires_at: new Date(expiresAt * 1000).toISOString(),
    },
    200,
    { "Set-Cookie": sessionCookie(value) }
  );
}

function adminLogout() {
  return json({ ok: true }, 200, { "Set-Cookie": clearSessionCookie() });
}

async function adminSession(request, env) {
  return json({ ok: await requireAdmin(request, env) });
}

function adminPage() {
  return html(`<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sistema Guimma - Licencas Admin</title>
  <style>
    :root {
      --bg: #f4f7fb;
      --panel: #ffffff;
      --ink: #111827;
      --muted: #64748b;
      --border: #d8dee9;
      --primary: #2563eb;
      --success: #15803d;
      --danger: #b91c1c;
      --warning: #b45309;
      --slate: #475569;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
    }
    .shell {
      width: min(980px, calc(100vw - 28px));
      margin: 28px auto;
    }
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 16px;
    }
    h1 {
      margin: 0;
      font-size: 25px;
      line-height: 1.1;
    }
    .subtitle {
      margin-top: 6px;
      color: var(--muted);
      font-size: 13px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      padding: 20px;
    }
    .grid {
      display: grid;
      grid-template-columns: 150px 1fr;
      gap: 12px 14px;
      align-items: center;
    }
    label {
      font-weight: 700;
      font-size: 13px;
    }
    input {
      width: 100%;
      border: 1px solid var(--border);
      background: #f8fafc;
      color: var(--ink);
      font-size: 15px;
      padding: 11px 12px;
      outline: none;
    }
    input:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, .12);
    }
    .days {
      max-width: 120px;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }
    button {
      border: 0;
      color: #fff;
      padding: 11px 14px;
      font-weight: 700;
      cursor: pointer;
      min-height: 40px;
      background: var(--slate);
    }
    button:hover { filter: brightness(.92); }
    button:disabled {
      opacity: .55;
      cursor: wait;
    }
    .primary { background: var(--primary); }
    .success { background: var(--success); }
    .danger { background: var(--danger); }
    .warning { background: var(--warning); }
    .ghost {
      background: #e5e7eb;
      color: var(--ink);
    }
    .result {
      margin-top: 16px;
      background: #f8fafc;
      border: 1px solid var(--border);
      min-height: 220px;
      padding: 16px;
      white-space: pre-wrap;
      font: 13px/1.5 Menlo, Consolas, monospace;
    }
    .login {
      max-width: 460px;
      margin: 12vh auto 0;
    }
    .hidden { display: none; }
    .footer {
      margin-top: 12px;
      color: var(--muted);
      font-size: 12px;
    }
    @media (max-width: 720px) {
      .grid { grid-template-columns: 1fr; }
      .header { align-items: flex-start; }
      button { width: 100%; }
      .days { max-width: 100%; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section id="login-view" class="panel login hidden">
      <h1>Sistema Guimma</h1>
      <div class="subtitle">Painel administrativo de licencas</div>
      <div style="height:18px"></div>
      <label for="password">Senha administrativa</label>
      <input id="password" type="password" autocomplete="current-password" autofocus>
      <div class="actions">
        <button id="login-button" class="primary">Entrar</button>
      </div>
      <div id="login-error" class="footer"></div>
    </section>

    <section id="admin-view" class="hidden">
      <div class="header">
        <div>
          <h1>Administrar Licencas</h1>
          <div class="subtitle">Ative, renove, bloqueie e libere troca de computador por email.</div>
        </div>
        <button id="logout-button" class="ghost">Sair</button>
      </div>

      <section class="panel">
        <div class="grid">
          <label for="email">Email do cliente</label>
          <input id="email" type="email" autocomplete="off" placeholder="cliente@email.com">

          <label for="name">Nome do cliente</label>
          <input id="name" type="text" autocomplete="off" placeholder="Opcional">

          <label for="days">Dias</label>
          <input id="days" class="days" type="number" min="1" value="30">
        </div>

        <div class="actions">
          <button id="consult-button">Consultar</button>
          <button id="activate-button" class="success">Ativar</button>
          <button id="renew-button" class="primary">Renovar</button>
          <button id="block-button" class="danger">Desativar/Bloquear</button>
          <button id="release-button" class="warning">Liberar computador</button>
        </div>
      </section>

      <section id="result" class="result">Digite o email do cliente e escolha uma acao.</section>
      <div class="footer">Desativar/Bloquear corta o acesso. Liberar computador mantem a assinatura, mas permite ativar em outro PC.</div>
    </section>
  </main>

  <script>
    const byId = (id) => document.getElementById(id);
    const loginView = byId('login-view');
    const adminView = byId('admin-view');
    const result = byId('result');
    const buttons = Array.from(document.querySelectorAll('button'));

    function showLogin(message) {
      loginView.classList.remove('hidden');
      adminView.classList.add('hidden');
      byId('login-error').textContent = message || '';
    }

    function showAdmin() {
      loginView.classList.add('hidden');
      adminView.classList.remove('hidden');
      byId('email').focus();
    }

    function setBusy(value) {
      buttons.forEach((button) => { button.disabled = value; });
    }

    function setResult(text) {
      result.textContent = text;
    }

    async function api(path, options) {
      const response = await fetch(path, Object.assign({
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
      }, options || {}));
      const text = await response.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch (_error) { data = { message: text }; }
      if (!response.ok) {
        throw new Error(data.error || data.message || 'Operacao recusada pelo servidor.');
      }
      return data;
    }

    function emailValue() {
      const email = byId('email').value.trim().toLowerCase();
      if (!email || !email.includes('@')) {
        throw new Error('Informe um email valido.');
      }
      return email;
    }

    function daysValue() {
      const days = Number.parseInt(byId('days').value || '30', 10);
      return Number.isFinite(days) && days > 0 ? days : 30;
    }

    function summary(data) {
      const customer = data.customer || {};
      const activation = data.activation || {};
      if (!customer.email) return 'Cliente nao encontrado.';
      const lines = [
        'Email: ' + (customer.email || ''),
        'Nome: ' + (customer.customer_name || '-'),
        'Plano: ' + (customer.plan || '-'),
        'Status: ' + (customer.status || '-'),
        'Validade: ' + (customer.valid_until || '-'),
      ];
      if (activation.machine_id) {
        lines.push(
          '',
          'Computador ativo:',
          'ID: ' + activation.machine_id,
          'Nome: ' + (activation.hostname || '-'),
          'Sistema: ' + (activation.system || '-'),
          'Ativado em: ' + (activation.activated_at || '-'),
          'Ultimo uso: ' + (activation.last_seen_at || '-')
        );
      } else {
        lines.push('', 'Computador ativo: nenhum');
      }
      return lines.join('\\n');
    }

    async function consult() {
      const email = emailValue();
      const data = await api('/api/admin/customers/get?email=' + encodeURIComponent(email), { method: 'GET' });
      setResult(summary(data));
      return data;
    }

    async function runAction(action) {
      setBusy(true);
      try {
        await action();
      } catch (error) {
        setResult('Erro:\\n' + error.message);
        alert(error.message);
      } finally {
        setBusy(false);
      }
    }

    byId('login-button').addEventListener('click', async () => {
      setBusy(true);
      try {
        await api('/api/admin/login', {
          method: 'POST',
          body: JSON.stringify({ password: byId('password').value }),
        });
        byId('password').value = '';
        showAdmin();
      } catch (_error) {
        showLogin('Senha invalida.');
      } finally {
        setBusy(false);
      }
    });

    byId('password').addEventListener('keydown', (event) => {
      if (event.key === 'Enter') byId('login-button').click();
    });

    byId('logout-button').addEventListener('click', () => runAction(async () => {
      await api('/api/admin/logout', { method: 'POST', body: '{}' });
      showLogin('');
    }));

    byId('consult-button').addEventListener('click', () => runAction(consult));

    byId('activate-button').addEventListener('click', () => runAction(async () => {
      await api('/api/admin/customers/upsert', {
        method: 'POST',
        body: JSON.stringify({
          customer_email: emailValue(),
          customer_name: byId('name').value.trim(),
          plan: 'mensal',
          status: 'active',
          days: daysValue(),
        }),
      });
      const data = await consult();
      setResult('Licenca ativada.\\n\\n' + summary(data));
    }));

    byId('renew-button').addEventListener('click', () => runAction(async () => {
      await api('/api/admin/customers/extend', {
        method: 'POST',
        body: JSON.stringify({ customer_email: emailValue(), days: daysValue() }),
      });
      const data = await consult();
      setResult('Licenca renovada por ' + daysValue() + ' dias.\\n\\n' + summary(data));
    }));

    byId('block-button').addEventListener('click', () => runAction(async () => {
      if (!confirm('Bloquear o acesso desta licenca?')) return;
      await api('/api/admin/customers/upsert', {
        method: 'POST',
        body: JSON.stringify({
          customer_email: emailValue(),
          customer_name: byId('name').value.trim(),
          plan: 'mensal',
          status: 'inactive',
          days: daysValue(),
        }),
      });
      const data = await consult();
      setResult('Licenca bloqueada.\\n\\n' + summary(data));
    }));

    byId('release-button').addEventListener('click', () => runAction(async () => {
      if (!confirm('Liberar o computador ativo desta licenca?')) return;
      await api('/api/admin/customers/release', {
        method: 'POST',
        body: JSON.stringify({ customer_email: emailValue() }),
      });
      const data = await consult();
      setResult('Computador liberado.\\n\\n' + summary(data));
    }));

    (async () => {
      try {
        const session = await api('/api/admin/session', { method: 'GET' });
        if (session.ok) showAdmin();
        else showLogin('');
      } catch (_error) {
        showLogin('');
      }
    })();
  </script>
</body>
</html>`);
}

async function upsertCustomer(request, env) {
  if (!(await requireAdmin(request, env))) {
    return json({ error: "nao_autorizado" }, 401);
  }
  const body = await readJson(request);
  if (!body) return json({ error: "JSON invalido." }, 400);

  const email = normalizeEmail(body.customer_email || body.email);
  if (!email || !email.includes("@")) {
    return json({ error: "Email invalido." }, 400);
  }

  const status = String(body.status || "active").trim().toLowerCase();
  const validUntil = body.valid_until || addDaysIso(body.days || env.LICENSE_VALID_DAYS);
  const customerName = String(body.customer_name || body.name || "").trim();
  const plan = String(body.plan || "mensal").trim();
  const notes = String(body.notes || "").trim();

  await env.DB.prepare(
    `INSERT INTO clientes_licencas (
      email,
      customer_name,
      plan,
      status,
      valid_until,
      last_payment_at,
      notes,
      updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(email) DO UPDATE SET
      customer_name = excluded.customer_name,
      plan = excluded.plan,
      status = excluded.status,
      valid_until = excluded.valid_until,
      last_payment_at = excluded.last_payment_at,
      notes = excluded.notes,
      updated_at = CURRENT_TIMESTAMP`
  )
    .bind(email, customerName, plan, status, validUntil, nowIso(), notes)
    .run();

  return json({
    ok: true,
    customer_email: email,
    status,
    valid_until: validUntil,
  });
}

async function extendCustomer(request, env) {
  if (!(await requireAdmin(request, env))) {
    return json({ error: "nao_autorizado" }, 401);
  }
  const body = await readJson(request);
  if (!body) return json({ error: "JSON invalido." }, 400);

  const email = normalizeEmail(body.customer_email || body.email);
  const days = Number.parseInt(body.days || env.LICENSE_VALID_DAYS || "30", 10);
  if (!email || !email.includes("@")) {
    return json({ error: "Email invalido." }, 400);
  }

  const row = await env.DB.prepare(
    `SELECT valid_until FROM clientes_licencas WHERE email = ?`
  )
    .bind(email)
    .first();

  const baseDate = row?.valid_until ? parseDate(row.valid_until) : null;
  const start = baseDate && baseDate.getTime() > Date.now() ? baseDate : new Date();
  start.setUTCDate(start.getUTCDate() + (Number.isFinite(days) && days > 0 ? days : 30));
  start.setUTCHours(23, 59, 59, 0);
  const validUntil = start.toISOString();

  await env.DB.prepare(
    `INSERT INTO clientes_licencas (
      email,
      status,
      valid_until,
      last_payment_at,
      updated_at
    ) VALUES (?, 'active', ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(email) DO UPDATE SET
      status = 'active',
      valid_until = excluded.valid_until,
      last_payment_at = excluded.last_payment_at,
      updated_at = CURRENT_TIMESTAMP`
  )
    .bind(email, validUntil, nowIso())
    .run();

  return json({ ok: true, customer_email: email, status: "active", valid_until: validUntil });
}

async function getCustomer(request, env) {
  if (!(await requireAdmin(request, env))) {
    return json({ error: "nao_autorizado" }, 401);
  }
  const url = new URL(request.url);
  const email = normalizeEmail(url.searchParams.get("email"));
  if (!email || !email.includes("@")) {
    return json({ error: "Email invalido." }, 400);
  }

  const row = await env.DB.prepare(
    `SELECT email, customer_name, plan, status, valid_until, last_payment_at, notes, created_at, updated_at
       FROM clientes_licencas
      WHERE email = ?`
  )
    .bind(email)
    .first();

  const activation = await activationForEmail(env, email);
  return json({ customer: row || null, activation: activation || null });
}

async function releaseCustomerActivation(request, env) {
  if (!(await requireAdmin(request, env))) {
    return json({ error: "nao_autorizado" }, 401);
  }
  const body = await readJson(request);
  if (!body) return json({ error: "JSON invalido." }, 400);

  const email = normalizeEmail(body.customer_email || body.email);
  if (!email || !email.includes("@")) {
    return json({ error: "Email invalido." }, 400);
  }

  const machineId = String(body.machine_id || "").trim();
  let result;
  if (machineId) {
    result = await env.DB.prepare(
      `DELETE FROM ativacoes_licenca
        WHERE email = ? AND machine_id = ?`
    )
      .bind(email, machineId)
      .run();
  } else {
    result = await env.DB.prepare(
      `DELETE FROM ativacoes_licenca
        WHERE email = ?`
    )
      .bind(email)
      .run();
  }

  return json({
    ok: true,
    customer_email: email,
    released: Boolean(result?.meta?.changes),
  });
}

async function listRecentChecks(request, env) {
  if (!(await requireAdmin(request, env))) {
    return json({ error: "nao_autorizado" }, 401);
  }
  const url = new URL(request.url);
  const email = normalizeEmail(url.searchParams.get("email"));
  const limit = Math.min(Number.parseInt(url.searchParams.get("limit") || "50", 10), 200);

  let stmt;
  if (email) {
    stmt = env.DB.prepare(
      `SELECT email, machine_id, hostname, system, decision, message, created_at
         FROM consultas_licenca
        WHERE email = ?
        ORDER BY created_at DESC
        LIMIT ?`
    ).bind(email, limit);
  } else {
    stmt = env.DB.prepare(
      `SELECT email, machine_id, hostname, system, decision, message, created_at
         FROM consultas_licenca
        ORDER BY created_at DESC
        LIMIT ?`
    ).bind(limit);
  }

  const result = await stmt.all();
  return json({ checks: result.results || [] });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/") {
      return json({
        ok: true,
        service: "Sistema Guimma Licencas",
        endpoints: ["/api/licenses/check", "/api/licenses/deactivate", "/admin"],
      });
    }

    if (request.method === "GET" && url.pathname === "/admin") {
      return adminPage();
    }

    if (request.method === "POST" && url.pathname === "/api/admin/login") {
      return adminLogin(request, env);
    }

    if (request.method === "POST" && url.pathname === "/api/admin/logout") {
      return adminLogout();
    }

    if (request.method === "GET" && url.pathname === "/api/admin/session") {
      return adminSession(request, env);
    }

    if (request.method === "POST" && url.pathname === "/api/licenses/check") {
      return checkLicense(request, env);
    }

    if (request.method === "POST" && url.pathname === "/api/licenses/deactivate") {
      return deactivateLicense(request, env);
    }

    if (request.method === "POST" && url.pathname === "/api/admin/customers/upsert") {
      return upsertCustomer(request, env);
    }

    if (request.method === "POST" && url.pathname === "/api/admin/customers/extend") {
      return extendCustomer(request, env);
    }

    if (request.method === "GET" && url.pathname === "/api/admin/customers/get") {
      return getCustomer(request, env);
    }

    if (request.method === "POST" && url.pathname === "/api/admin/customers/release") {
      return releaseCustomerActivation(request, env);
    }

    if (request.method === "GET" && url.pathname === "/api/admin/checks") {
      return listRecentChecks(request, env);
    }

    return json({ error: "rota_nao_encontrada" }, 404);
  },
};
