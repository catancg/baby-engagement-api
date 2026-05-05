import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
router = APIRouter(prefix="/admin", tags=["admin-ui"])

def require_admin_key(x_admin_key: str | None):
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY not set")
    if x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.get("/ui", response_class=HTMLResponse)
def admin_ui():
    html = f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Admin — Pika Pika</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, Arial; margin: 0; padding: 0; background: #f8f9fa; color: #222; }}
    .topbar {{ background: #fff; border-bottom: 1px solid #e0e0e0; padding: 10px 20px; display: flex; align-items: center; gap: 20px; }}
    .topbar h1 {{ font-size: 16px; font-weight: 700; color: #333; margin: 0; }}
    .nav-links {{ display: flex; gap: 14px; font-size: 13px; flex: 1; }}
    .nav-links a {{ color: #555; text-decoration: none; font-weight: 600; }}
    .nav-links a:hover {{ text-decoration: underline; }}
    .nav-links a.active {{ color: #1a73e8; }}
    .content {{ padding: 20px; }}
    h2 {{ margin: 0 0 4px; }}

    .summary-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
    .stat-card {{
      background: #fff; border: 1px solid #e0e0e0; border-radius: 10px;
      padding: 14px 20px; min-width: 120px; text-align: center;
    }}
    .stat-card .num {{ font-size: 28px; font-weight: 700; line-height: 1; }}
    .stat-card .lbl {{ font-size: 12px; color: #666; margin-top: 4px; text-transform: uppercase; letter-spacing: .5px; }}

    .tools-row {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }}
    .tool-card {{
      background: #fff; border: 1px solid #e0e0e0; border-radius: 10px;
      padding: 16px 18px; flex: 1; min-width: 260px;
    }}
    .tool-card h3 {{ margin: 0 0 12px; font-size: 15px; color: #333; }}
    .ctrl-row {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
    select, input[type=text] {{
      padding: 7px 10px; font-size: 14px; border: 1px solid #ccc;
      border-radius: 6px; background: #fff;
    }}
    input[type=text] {{ flex: 1; min-width: 160px; }}
    button {{
      padding: 7px 16px; font-size: 14px; border: none; border-radius: 6px;
      background: #1a73e8; color: #fff; cursor: pointer; font-weight: 600;
    }}
    button:hover {{ background: #1558c0; }}
    button.secondary {{ background: #f1f3f4; color: #333; }}
    button.secondary:hover {{ background: #e0e0e0; }}

    .tbl-wrap {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; overflow: auto; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    thead th {{ background: #fafafa; border-bottom: 2px solid #e0e0e0; padding: 9px 12px; text-align: left; font-weight: 600; white-space: nowrap; }}
    tbody tr:hover {{ background: #f5f8ff; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #f0f0f0; vertical-align: middle; }}
    .badge {{
      display: inline-block; font-size: 11px; font-weight: 600;
      padding: 2px 8px; border-radius: 12px;
    }}
    .b-queued  {{ background: #fff3cd; color: #856404; }}
    .b-sent    {{ background: #d1e7dd; color: #0a3622; }}
    .b-failed  {{ background: #f8d7da; color: #842029; }}
    .muted {{ color: #888; font-size: 13px; }}
    .error {{ color: #b00020; font-size: 13px; margin-top: 6px; white-space: pre-wrap; }}
    #resultsTitle {{ font-size: 15px; font-weight: 700; margin: 0 0 10px; color: #333; }}
  </style>
</head>
<body>
  <div class="topbar">
    <h1>Admin — Pika Pika</h1>
    <div class="nav-links">
      <a href="/admin/ui" class="active">Dashboard</a>
      <a href="/admin/ui/customers">Clientes</a>
      <a href="/admin/email-builder">Email Builder</a>
      <a href="/admin/news-builder">News Builder</a>
    </div>
  </div>
  <div class="content">
  <h2>Admin Dashboard — Pika Pika</h2>

  <div class="summary-row" id="summaryRow">
    <div class="stat-card"><div class="num" id="statCustomers">—</div><div class="lbl">Clientes</div></div>
    <div class="stat-card"><div class="num" id="statOutbox">—</div><div class="lbl">Outbox total</div></div>
    <div class="stat-card"><div class="num" id="statQueued">—</div><div class="lbl">En cola</div></div>
    <div class="stat-card"><div class="num" id="statSent">—</div><div class="lbl">Enviados</div></div>
    <div class="stat-card"><div class="num" id="statFailed">—</div><div class="lbl">Fallidos</div></div>
    <div class="stat-card"><div class="num" id="statConsent">—</div><div class="lbl">Con consentimiento</div></div>
  </div>
  <div id="summaryErr" class="error"></div>

  <div class="tools-row">
    <div class="tool-card">
      <h3>Outbox</h3>
      <div class="ctrl-row">
        <select id="statusSel">
          <option value="queued">queued</option>
          <option value="sent">sent</option>
          <option value="failed">failed</option>
        </select>
        <button onclick="loadOutbox()">Ver</button>
      </div>
      <div id="outboxErr" class="error"></div>
    </div>

    <div class="tool-card">
      <h3>Debug por identidad</h3>
      <div class="ctrl-row">
        <select id="chanSel">
          <option value="email">email</option>
          <option value="whatsapp">whatsapp</option>
          <option value="instagram">instagram</option>
        </select>
        <input type="text" id="valInput" placeholder="email o @usuario" />
        <button onclick="debugIdentity()">Buscar</button>
      </div>
      <div id="debugErr" class="error"></div>
    </div>
  </div>

  <div id="resultsSection" style="display:none;">
    <p id="resultsTitle"></p>
    <div class="tbl-wrap"><div id="results"></div></div>
  </div>

<script>
  const ADMIN_KEY = sessionStorage.getItem('builderKey') || '';
  if (!ADMIN_KEY) window.location.replace('/builder-login?next=/admin/ui');

  async function apiGet(path) {{
    const res = await fetch(path, {{ headers: {{ "x-admin-key": ADMIN_KEY }} }});
    const text = await res.text();
    if (!res.ok) throw new Error(`HTTP ${{res.status}}: ${{text}}`);
    return JSON.parse(text);
  }}

  function esc(s) {{
    return String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  }}

  function fmtDate(s) {{
    return s ? s.substring(0, 16).replace("T", " ") : "—";
  }}

  async function loadSummary() {{
    document.getElementById("summaryErr").textContent = "";
    try {{
      const data = await apiGet("/admin/summary");
      const c = data.counts || {{}};
      document.getElementById("statCustomers").textContent = c.customers ?? "—";
      document.getElementById("statOutbox").textContent    = c.outbox ?? "—";
      const byStatus = {{}};
      for (const x of (data.outbox_by_status || [])) byStatus[x.status] = x.count;
      document.getElementById("statQueued").textContent  = byStatus.queued  ?? 0;
      document.getElementById("statSent").textContent    = byStatus.sent    ?? 0;
      document.getElementById("statFailed").textContent  = byStatus.failed  ?? 0;
      const granted = (data.current_promotions_consent_by_status || []).find(x => x.status === "granted");
      document.getElementById("statConsent").textContent = granted ? granted.count : "—";
    }} catch(e) {{
      document.getElementById("summaryErr").textContent = String(e);
    }}
  }}

  async function loadOutbox() {{
    document.getElementById("outboxErr").textContent = "";
    const status = document.getElementById("statusSel").value;
    try {{
      const data = await apiGet(`/admin/outbox?status=${{encodeURIComponent(status)}}&limit=50`);
      const items = data.items || [];
      const rows = items.map(it => `<tr>
        <td class="muted" style="font-size:11px;">${{esc(it.outbox_id).substring(0,8)}}…</td>
        <td>${{esc(it.first_name || "")}}</td>
        <td>${{esc(it.recipient)}}</td>
        <td><span class="badge b-${{it.status}}">${{it.status}}</span></td>
        <td>${{esc(it.template_key)}}</td>
        <td class="muted">${{fmtDate(it.scheduled_for)}}</td>
        <td class="muted">${{fmtDate(it.sent_at)}}</td>
      </tr>`).join("");
      showResults(`Outbox: ${{status}} (últimos 50)`, `
        <table>
          <thead><tr><th>ID</th><th>Nombre</th><th>Email</th><th>Estado</th><th>Template</th><th>Programado</th><th>Enviado</th></tr></thead>
          <tbody>${{rows || "<tr><td colspan='7' class='muted' style='padding:16px;text-align:center;'>Sin datos</td></tr>"}}</tbody>
        </table>`);
    }} catch(e) {{
      document.getElementById("outboxErr").textContent = String(e);
    }}
  }}

  async function debugIdentity() {{
    document.getElementById("debugErr").textContent = "";
    const channel = document.getElementById("chanSel").value;
    const value = document.getElementById("valInput").value.trim();
    if (!value) {{ document.getElementById("debugErr").textContent = "Ingresá un valor."; return; }}
    try {{
      const data = await apiGet(`/admin/debug/identity?channel=${{encodeURIComponent(channel)}}&value=${{encodeURIComponent(value)}}`);
      const cust = data.customer || {{}};
      const consent = data.current_promotions_consent;
      const outbox = data.recent_outbox || [];
      const custRows = Object.entries(cust).map(([k,v]) =>
        `<tr><td style="font-weight:600;width:140px;">${{esc(k)}}</td><td>${{esc(v)}}</td></tr>`).join("");
      const outboxRows = outbox.map(it => `<tr>
        <td class="muted" style="font-size:11px;">${{esc(it.outbox_id).substring(0,8)}}…</td>
        <td><span class="badge b-${{it.status}}">${{it.status}}</span></td>
        <td>${{esc(it.template_key)}}</td>
        <td class="muted">${{fmtDate(it.scheduled_for)}}</td>
        <td class="muted">${{fmtDate(it.sent_at)}}</td>
        <td class="muted">${{fmtDate(it.created_at)}}</td>
      </tr>`).join("");

      showResults(`Debug: ${{value}}`, `
        <table style="margin-bottom:16px;">
          <thead><tr><th colspan="2">Cliente</th></tr></thead>
          <tbody>${{custRows}}</tbody>
        </table>
        <table style="margin-bottom:16px;">
          <thead><tr><th colspan="2">Consentimiento promociones</th></tr></thead>
          <tbody>${{consent
            ? Object.entries(consent).map(([k,v]) => `<tr><td style="font-weight:600;width:140px;">${{esc(k)}}</td><td>${{esc(v)}}</td></tr>`).join("")
            : "<tr><td colspan='2' class='muted'>Sin consentimiento</td></tr>"
          }}</tbody>
        </table>
        <table>
          <thead><tr><th>ID</th><th>Estado</th><th>Template</th><th>Programado</th><th>Enviado</th><th>Creado</th></tr></thead>
          <tbody>${{outboxRows || "<tr><td colspan='6' class='muted' style='padding:12px;'>Sin outbox</td></tr>"}}</tbody>
        </table>`);
    }} catch(e) {{
      document.getElementById("debugErr").textContent = String(e);
    }}
  }}

  function showResults(title, html) {{
    document.getElementById("resultsTitle").textContent = title;
    document.getElementById("results").innerHTML = html;
    document.getElementById("resultsSection").style.display = "block";
  }}

  loadSummary();
</script>
</div>
</body>
</html>
"""
    return HTMLResponse(content=html)


@router.get("/ui/customers", response_class=HTMLResponse)
def admin_ui_customers():
    html = f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Clientes — Pika Pika Admin</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, Arial; margin: 0; padding: 0; background: #f8f9fa; color: #222; }}
    .topbar {{ background: #fff; border-bottom: 1px solid #e0e0e0; padding: 10px 20px; display: flex; align-items: center; gap: 20px; }}
    .topbar h1 {{ font-size: 16px; font-weight: 700; color: #333; margin: 0; }}
    .nav-links {{ display: flex; gap: 14px; font-size: 13px; flex: 1; }}
    .nav-links a {{ color: #555; text-decoration: none; font-weight: 600; }}
    .nav-links a:hover {{ text-decoration: underline; }}
    .nav-links a.active {{ color: #1a73e8; }}
    .content {{ padding: 20px; }}
    h2 {{ margin: 0 0 4px; }}
    .summary-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
    .stat-card {{
      background: #fff; border: 1px solid #e0e0e0; border-radius: 10px;
      padding: 14px 20px; min-width: 130px; text-align: center;
    }}
    .stat-card .num {{ font-size: 32px; font-weight: 700; line-height: 1; }}
    .stat-card .lbl {{ font-size: 12px; color: #666; margin-top: 4px; text-transform: uppercase; letter-spacing: .5px; }}
    .stat-card.total {{ border-color: #aaa; }}
    .controls {{ display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; align-items: center; }}
    input[type=search] {{ padding: 8px 12px; font-size: 14px; border: 1px solid #ccc; border-radius: 6px; width: 280px; }}
    select {{ padding: 8px; font-size: 14px; border: 1px solid #ccc; border-radius: 6px; }}
    .tbl-wrap {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; overflow: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    thead th {{ background: #fafafa; border-bottom: 2px solid #e0e0e0; padding: 10px 12px; text-align: left; font-weight: 600; white-space: nowrap; cursor: pointer; user-select: none; }}
    thead th:hover {{ background: #f0f0f0; }}
    tbody tr:hover {{ background: #f5f8ff; }}
    td {{ padding: 9px 12px; border-bottom: 1px solid #f0f0f0; vertical-align: middle; }}
    .badge {{
      display: inline-block; font-size: 11px; font-weight: 600;
      padding: 2px 8px; border-radius: 12px; margin: 2px 2px 2px 0;
      white-space: nowrap;
    }}
    .b-baby_items  {{ background: #dbeafe; color: #1e40af; }}
    .b-toys        {{ background: #fef9c3; color: #854d0e; }}
    .b-cochesitos  {{ background: #dcfce7; color: #166534; }}
    .b-cunas       {{ background: #fce7f3; color: #9d174d; }}
    .b-other       {{ background: #f3f4f6; color: #374151; }}
    .muted {{ color: #888; font-size: 13px; }}
    .error {{ color: #b00020; }}
    #count-info {{ font-size: 13px; color: #555; }}
    .sort-arrow {{ font-size: 10px; margin-left: 4px; }}
  </style>
</head>
<body>
  <div class="topbar">
    <h1>Admin — Pika Pika</h1>
    <div class="nav-links">
      <a href="/admin/ui">Dashboard</a>
      <a href="/admin/ui/customers" class="active">Clientes</a>
      <a href="/admin/email-builder">Email Builder</a>
      <a href="/admin/news-builder">News Builder</a>
    </div>
  </div>
  <div class="content">
  <h2>Clientes &amp; Intereses — Pika Pika</h2>

  <div class="summary-row" id="summaryRow">
    <div class="stat-card total">
      <div class="num" id="statTotal">—</div>
      <div class="lbl">Total clientes</div>
    </div>
  </div>

  <div class="controls">
    <input type="search" id="searchBox" placeholder="Buscar por nombre o email…" oninput="applyFilter()" />
    <select id="filterInterest" onchange="applyFilter()">
      <option value="">Todos los intereses</option>
      <option value="baby_items">baby_items</option>
      <option value="toys">toys</option>
      <option value="cochesitos">cochesitos</option>
      <option value="cunas">cunas</option>
      <option value="__none__">Sin intereses</option>
    </select>
    <span id="count-info"></span>
  </div>

  <div id="errorBox" class="error"></div>

  <div class="tbl-wrap">
    <table id="custTable">
      <thead>
        <tr>
          <th onclick="sortBy('first_name')">Nombre <span class="sort-arrow" id="arr-first_name"></span></th>
          <th onclick="sortBy('email')">Email <span class="sort-arrow" id="arr-email"></span></th>
          <th onclick="sortBy('created_at')">Registro <span class="sort-arrow" id="arr-created_at"></span></th>
          <th>Intereses</th>
        </tr>
      </thead>
      <tbody id="custBody">
        <tr><td colspan="4" class="muted">Cargando...</td></tr>
      </tbody>
    </table>
  </div>

<script>
  const ADMIN_KEY = sessionStorage.getItem('builderKey') || '';
  if (!ADMIN_KEY) window.location.replace('/builder-login?next=/admin/ui/customers');
  let allCustomers = [];
  let sortKey = "created_at";
  let sortAsc = false;

  const INTEREST_LABELS = {{
    baby_items: "Baby Items",
    toys: "Juguetes",
    cochesitos: "Cochecitos",
    cunas: "Cunas",
  }};

  async function load() {{
    try {{
      const res = await fetch("/admin/customers/interests?limit=500", {{
        headers: {{ "x-admin-key": ADMIN_KEY }}
      }});
      if (!res.ok) throw new Error(`HTTP ${{res.status}}`);
      const data = await res.json();

      // Summary cards
      const total = data.customers.length;
      document.getElementById("statTotal").textContent = total;
      const row = document.getElementById("summaryRow");
      const COLORS = {{
        baby_items: "#dbeafe", toys: "#fef9c3",
        cochesitos: "#dcfce7", cunas: "#fce7f3"
      }};
      for (const c of data.interest_counts) {{
        const card = document.createElement("div");
        card.className = "stat-card";
        card.style.borderColor = COLORS[c.interest_key] || "#e0e0e0";
        card.innerHTML = `<div class="num">${{c.customer_count}}</div><div class="lbl">${{INTEREST_LABELS[c.interest_key] || c.interest_key}}</div>`;
        row.appendChild(card);
      }}

      allCustomers = data.customers;
      applyFilter();
    }} catch(e) {{
      document.getElementById("errorBox").textContent = "Error: " + e.message;
      document.getElementById("custBody").innerHTML = "";
    }}
  }}

  function applyFilter() {{
    const q = document.getElementById("searchBox").value.toLowerCase();
    const fi = document.getElementById("filterInterest").value;

    let list = allCustomers.filter(c => {{
      if (q) {{
        const name = (c.first_name || "").toLowerCase();
        const email = (c.email || "").toLowerCase();
        if (!name.includes(q) && !email.includes(q)) return false;
      }}
      if (fi === "__none__") return !c.interests || c.interests.length === 0;
      if (fi) return c.interests && c.interests.includes(fi);
      return true;
    }});

    list = sortList(list);
    renderTable(list);
    document.getElementById("count-info").textContent =
      list.length === allCustomers.length
        ? `${{list.length}} clientes`
        : `${{list.length}} de ${{allCustomers.length}} clientes`;
  }}

  function sortList(list) {{
    return [...list].sort((a, b) => {{
      let va = a[sortKey] ?? "";
      let vb = b[sortKey] ?? "";
      if (typeof va === "string") va = va.toLowerCase();
      if (typeof vb === "string") vb = vb.toLowerCase();
      if (va < vb) return sortAsc ? -1 : 1;
      if (va > vb) return sortAsc ? 1 : -1;
      return 0;
    }});
  }}

  function sortBy(key) {{
    if (sortKey === key) {{ sortAsc = !sortAsc; }}
    else {{ sortKey = key; sortAsc = true; }}
    ["first_name", "email", "created_at"].forEach(k => {{
      document.getElementById("arr-" + k).textContent =
        k === sortKey ? (sortAsc ? "▲" : "▼") : "";
    }});
    applyFilter();
  }}

  function renderTable(list) {{
    const tbody = document.getElementById("custBody");
    if (!list.length) {{
      tbody.innerHTML = `<tr><td colspan="4" class="muted">Sin resultados.</td></tr>`;
      return;
    }}
    tbody.innerHTML = list.map(c => {{
      const interests = (c.interests || []);
      const badges = interests.length
        ? interests.map(i => `<span class="badge b-${{i}}">${{INTEREST_LABELS[i] || i}}</span>`).join("")
        : `<span class="muted">—</span>`;
      const date = c.created_at ? c.created_at.substring(0, 10) : "—";
      return `<tr>
        <td>${{escHtml(c.first_name || "")}}</td>
        <td class="muted">${{escHtml(c.email || "")}}</td>
        <td class="muted">${{date}}</td>
        <td>${{badges}}</td>
      </tr>`;
    }}).join("");
  }}

  function escHtml(s) {{
    return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  }}

  // default sort arrow
  document.getElementById("arr-created_at").textContent = "▼";
  load();
</script>
</div>
</body>
</html>
"""
    return HTMLResponse(content=html)
