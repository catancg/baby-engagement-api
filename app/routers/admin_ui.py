import os
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi import Query
router = APIRouter(prefix="/admin", tags=["admin-ui"])

def require_admin_key(x_admin_key: str | None):
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY not set")
    if x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.get("/ui", response_class=HTMLResponse)
def admin_ui(key: str | None = Query(default=None),
    x_admin_key: str | None = Header(default=None),
):
    admin_key = key or x_admin_key
    require_admin_key(admin_key)

    # JS will call the API endpoints using the same x-admin-key
    html = f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Pika Pika Admin</title>
  <style>
    body {{ font-family: system-ui, Arial; margin: 20px; }}
    .row {{ display:flex; gap:12px; flex-wrap:wrap; }}
    .card {{ border:1px solid #ddd; border-radius:10px; padding:12px; min-width:260px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ border-bottom:1px solid #eee; padding:8px; text-align:left; font-size:14px; }}
    input, select, button {{ padding:8px; font-size:14px; }}
    button {{ cursor:pointer; }}
    .muted {{ color:#666; }}
    code {{ background:#f5f5f5; padding:2px 4px; border-radius:6px; }}
    .error {{ color:#b00020; white-space:pre-wrap; }}
  </style>
</head>
<body>
  <h2>Admin Dashboard — Pika Pika</h2>
  <p class="muted">Este panel usa tu <code>x-admin-key</code> (ya validada en el server).</p>

  <div class="row">
    <div class="card">
      <h3>Resumen</h3>
      <div id="summary">Cargando...</div>
      <div id="summaryErr" class="error"></div>
      <button onclick="loadSummary()">Actualizar</button>
    </div>

    <div class="card">
      <h3>Outbox</h3>
      <div class="row">
        <select id="statusSel">
          <option value="queued">queued</option>
          <option value="sent">sent</option>
          <option value="failed">failed</option>
        </select>
        <button onclick="loadOutbox()">Ver</button>
      </div>
      <div id="outboxErr" class="error"></div>
    </div>

    <div class="card">
      <h3>Debug por identidad</h3>
      <div class="row">
        <select id="chanSel">
          <option value="email">email</option>
          <option value="whatsapp">whatsapp</option>
          <option value="instagram">instagram</option>
        </select>
        <input id="valInput" placeholder="email o teléfono o @usuario" style="flex:1;" />
      </div>
      <button onclick="debugIdentity()" style="margin-top:8px;">Buscar</button>
      <div id="debugErr" class="error"></div>
    </div>
  </div>

  <h3 style="margin-top:20px;">Resultados</h3>
  <div id="results"></div>

<script>
  const ADMIN_KEY = "{admin_key}";

  async function apiGet(path) {{
    const res = await fetch(path, {{
      headers: {{
        "x-admin-key": ADMIN_KEY
      }}
    }});
    const text = await res.text();
    if (!res.ok) throw new Error(`HTTP ${{res.status}}: ${{text}}`);
    return JSON.parse(text);
  }}

  function renderKv(obj) {{
    return "<table>" + Object.entries(obj).map(([k,v]) =>
      `<tr><th>${{k}}</th><td>${{v}}</td></tr>`
    ).join("") + "</table>";
  }}

  async function loadSummary() {{
    document.getElementById("summaryErr").innerText = "";
    document.getElementById("summary").innerText = "Cargando...";
    try {{
      const data = await apiGet("/admin/summary");
      const counts = data.counts || {{}};
      const outbox = (data.outbox_by_status || []).map(x => `${{x.status}}: ${{x.count}}`).join("<br>");
      const cons = (data.current_promotions_consent_by_status || []).map(x => `${{x.status}}: ${{x.count}}`).join("<br>") || "(view no disponible)";
      document.getElementById("summary").innerHTML =
        `<b>Counts</b>${{renderKv(counts)}}<br><b>Outbox</b><br>${{outbox}}<br><br><b>Consent</b><br>${{cons}}`;
    }} catch(e) {{
      document.getElementById("summary").innerText = "";
      document.getElementById("summaryErr").innerText = String(e);
    }}
  }}

  async function loadOutbox() {{
    document.getElementById("outboxErr").innerText = "";
    const status = document.getElementById("statusSel").value;
    try {{
      const data = await apiGet(`/admin/outbox?status=${{encodeURIComponent(status)}}&limit=50`);
      const items = data.items || [];
      const rows = items.map(it => `
        <tr>
          <td>${{it.outbox_id}}</td>
          <td>${{it.recipient}}</td>
          <td>${{it.template_key}}</td>
          <td>${{it.status}}</td>
          <td>${{it.scheduled_for || ""}}</td>
          <td>${{it.sent_at || ""}}</td>
        </tr>`).join("");
      document.getElementById("results").innerHTML = `
        <h4>Outbox: ${{status}} (últimos 50)</h4>
        <table>
          <thead><tr>
            <th>outbox_id</th><th>recipient</th><th>template</th><th>status</th><th>scheduled_for</th><th>sent_at</th>
          </tr></thead>
          <tbody>${{rows || "<tr><td colspan='6'>(sin datos)</td></tr>"}}</tbody>
        </table>`;
    }} catch(e) {{
      document.getElementById("outboxErr").innerText = String(e);
    }}
  }}

  async function debugIdentity() {{
    document.getElementById("debugErr").innerText = "";
    const channel = document.getElementById("chanSel").value;
    const value = document.getElementById("valInput").value.trim();
    if (!value) {{
      document.getElementById("debugErr").innerText = "Ingresá un valor.";
      return;
    }}
    try {{
      const data = await apiGet(`/admin/debug/identity?channel=${{encodeURIComponent(channel)}}&value=${{encodeURIComponent(value)}}`);
      const cust = data.customer || {{}};
      const consent = data.current_promotions_consent || null;
      const outbox = data.recent_outbox || [];
      const outboxRows = outbox.map(it => `
        <tr>
          <td>${{it.outbox_id}}</td>
          <td>${{it.status}}</td>
          <td>${{it.template_key}}</td>
          <td>${{it.scheduled_for || ""}}</td>
          <td>${{it.sent_at || ""}}</td>
          <td>${{it.created_at || ""}}</td>
        </tr>`).join("");

      document.getElementById("results").innerHTML = `
        <h4>Debug</h4>
        <b>Customer</b>${{renderKv(cust)}}<br>
        <b>Current promotions consent</b><br>${{consent ? renderKv(consent) : "(no disponible)"}}
        <br><br>
        <b>Recent outbox</b>
        <table>
          <thead><tr>
            <th>outbox_id</th><th>status</th><th>template</th><th>scheduled_for</th><th>sent_at</th><th>created_at</th>
          </tr></thead>
          <tbody>${{outboxRows || "<tr><td colspan='6'>(sin datos)</td></tr>"}}</tbody>
        </table>`;
    }} catch(e) {{
      document.getElementById("debugErr").innerText = String(e);
    }}
  }}

  loadSummary();
</script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@router.get("/ui/customers", response_class=HTMLResponse)
def admin_ui_customers(
    key: str | None = Query(default=None),
    x_admin_key: str | None = Header(default=None),
):
    admin_key = key or x_admin_key
    require_admin_key(admin_key)

    html = f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Clientes — Pika Pika Admin</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, Arial; margin: 0; padding: 20px; background: #f8f9fa; color: #222; }}
    h2 {{ margin: 0 0 4px; }}
    .nav {{ margin-bottom: 16px; font-size: 13px; }}
    .nav a {{ color: #555; text-decoration: none; }}
    .nav a:hover {{ text-decoration: underline; }}
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
  <div class="nav"><a href="/admin/ui?key={admin_key}">← Admin principal</a></div>
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
  const ADMIN_KEY = "{admin_key}";
  let allCustomers = [];
  let sortKey = "created_at";
  let sortAsc = false;

  const INTEREST_LABELS = {{
    baby_items: "Baby Items",
    toys: "Juguetes",
    cochesitos: "Cochesitos",
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
</body>
</html>
"""
    return HTMLResponse(content=html)
