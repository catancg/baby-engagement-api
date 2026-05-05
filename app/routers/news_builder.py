import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["news-builder"])

BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")
MAPS_URL = "https://www.google.com/maps/place/Pika+pika/@-33.0094136,-58.5212939,17z/data=!3m1!4b1!4m6!3m5!1s0x95baa96e7a3c9b9b:0xe3dcf248c61b47ba!8m2!3d-33.0094136!4d-58.5212939!16s%2Fg%2F11s5zh8086?entry=ttu&g_ep=EgoyMDI2MDIyNS4wIKXMDSoASAFQAw%3D%3D"
WHATSAPP_URL = "https://wa.me/5493446586123"
INSTAGRAM_URL = "https://instagram.com/pikapikagchu"
INSTAGRAM_HANDLE = "@pikapikagchu"
FACEBOOK_URL = "https://www.facebook.com/pika.pika.73295"

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_UPLOADS_DIR = TEMPLATES_DIR.parent / "static" / "uploads"
_SUPABASE_BUCKET = "email-images"
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_IMAGE_BYTES = 5 * 1024 * 1024

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def require_builder_key(x_admin_key: str | None = Header(default=None)):
    admin_key = os.getenv("ADMIN_API_KEY", "")
    builder_key = os.getenv("BUILDER_API_KEY", "")
    valid = {k for k in [admin_key, builder_key] if k}
    if not valid:
        raise HTTPException(status_code=500, detail="No API keys configured")
    if x_admin_key not in valid:
        raise HTTPException(status_code=401, detail="Unauthorized")


async def _save_image(content: bytes, filename: str, content_type: str) -> str:
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if supabase_url and service_key and "your_service_role_key" not in service_key:
        ext = Path(filename).suffix.lower() if filename else ".jpg"
        safe_name = f"{uuid.uuid4().hex}{ext}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{supabase_url}/storage/v1/object/{_SUPABASE_BUCKET}/{safe_name}",
                content=content,
                headers={"Authorization": f"Bearer {service_key}", "Content-Type": content_type},
            )
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"Supabase upload failed: {resp.text[:300]}")
        return f"{supabase_url}/storage/v1/object/public/{_SUPABASE_BUCKET}/{safe_name}"
    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower() if filename else ".jpg"
    local_name = f"{uuid.uuid4().hex}{ext}"
    (_UPLOADS_DIR / local_name).write_bytes(content)
    return f"/uploads/{local_name}"


def _render_news_html(payload: dict, to_email: str = "preview@example.com") -> str:
    base_url = BASE_URL.rstrip("/")
    unsubscribe_url = f"{base_url}/unsubscribe?channel=email&value={to_email}"
    template = jinja_env.get_template("news_email.html")
    return template.render(
        logo_url=f"{base_url}/static/logo.png",
        intro_text=payload.get("intro_text", ""),
        products=payload.get("products", []),
        promo_text=payload.get("promo_text", ""),
        closing_message=payload.get("closing_message", ""),
        maps_url=MAPS_URL,
        whatsapp_url=WHATSAPP_URL,
        instagram_url=INSTAGRAM_URL,
        instagram_handle=INSTAGRAM_HANDLE,
        facebook_url=FACEBOOK_URL,
        unsubscribe_url=unsubscribe_url,
    )


# ── Login ──────────────────────────────────────────────────────────────────────

@router.get("/news-builder-login", response_class=HTMLResponse)
def news_builder_login():
    page = jinja_env.get_template("builder_login.html")
    return HTMLResponse(content=page.render())


# ── Builder page ───────────────────────────────────────────────────────────────

@router.get("/admin/news-builder", response_class=HTMLResponse)
def news_builder_page():
    html = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>News Builder — Pika Pika</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, Arial; background: #f8f9fa; color: #222; height: 100vh; display: flex; flex-direction: column; }
    .topbar { background: #fff; border-bottom: 1px solid #e0e0e0; padding: 10px 20px; display: flex; align-items: center; gap: 20px; flex-shrink: 0; }
    .topbar h1 { font-size: 16px; font-weight: 700; color: #333; }
    .nav-links { display: flex; gap: 14px; font-size: 13px; }
    .nav-links a { color: #555; text-decoration: none; font-weight: 600; }
    .nav-links a:hover { text-decoration: underline; }
    .nav-links a.active { color: #1a73e8; }
    .main { display: flex; flex: 1; overflow: hidden; }

    /* FORM PANEL */
    .form-panel { width: 380px; flex-shrink: 0; overflow-y: auto; padding: 16px; background: #fff; border-right: 1px solid #e0e0e0; }
    .section { margin-bottom: 18px; }
    .section-title { font-size: 13px; font-weight: 700; color: #444; margin-bottom: 8px; text-transform: uppercase; letter-spacing: .4px; }
    textarea, input[type=text], input[type=number] {
      width: 100%; padding: 8px 10px; font-size: 14px; font-family: inherit;
      border: 1px solid #ddd; border-radius: 8px; background: #fafafa; outline: none;
      transition: border-color .15s;
    }
    textarea:focus, input:focus { border-color: #5B8C5A; background: #fff; }
    textarea { resize: vertical; min-height: 70px; }

    .product-block { border: 1.5px solid #e0e0e0; border-radius: 12px; padding: 12px; margin-bottom: 12px; background: #fafcfa; }
    .product-block-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    .product-block-title { font-size: 13px; font-weight: 700; color: #5B8C5A; }
    .btn-remove { background: none; border: none; color: #b00020; cursor: pointer; font-size: 13px; font-weight: 600; padding: 2px 6px; }
    .btn-remove:hover { text-decoration: underline; }

    .photo-section { margin-bottom: 10px; }
    .photo-preview { width: 100%; height: 120px; object-fit: cover; border-radius: 8px; margin-bottom: 6px; display: none; }
    .photo-url-row { display: flex; gap: 6px; margin-bottom: 6px; }
    .photo-url-row input { flex: 1; }
    .btn-pick { padding: 6px 10px; font-size: 12px; background: #f1f3f4; border: 1px solid #ccc; border-radius: 6px; cursor: pointer; white-space: nowrap; }
    .btn-pick:hover { background: #e0e0e0; }
    .field-row { margin-bottom: 8px; }
    .field-label { font-size: 12px; color: #666; margin-bottom: 3px; display: block; }
    .field-optional { font-size: 11px; color: #aaa; margin-left: 4px; }

    .btn-add { width: 100%; padding: 9px; border: 1.5px dashed #5B8C5A; border-radius: 10px; background: none; color: #5B8C5A; font-size: 13px; font-weight: 700; cursor: pointer; }
    .btn-add:hover { background: #eaf8ea; }
    .btn-add:disabled { border-color: #ccc; color: #aaa; cursor: not-allowed; }

    .promo-toggle { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; cursor: pointer; font-size: 14px; font-weight: 600; }
    .promo-toggle input { width: 16px; height: 16px; cursor: pointer; accent-color: #5B8C5A; }
    .cat-all-label { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; cursor: pointer; font-size: 14px; font-weight: 600; }
    .cat-all-label input { width: 16px; height: 16px; cursor: pointer; accent-color: #5B8C5A; }
    .cat-item { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; cursor: pointer; font-size: 13px; color: #444; }
    .cat-item input { width: 15px; height: 15px; cursor: pointer; accent-color: #5B8C5A; }

    .actions { display: flex; flex-direction: column; gap: 10px; padding-top: 8px; }
    .btn-preview { padding: 10px; background: #f1f3f4; border: 1px solid #ccc; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; }
    .btn-preview:hover { background: #e0e0e0; }
    .btn-queue { padding: 12px; background: #5B8C5A; color: #fff; border: none; border-radius: 10px; cursor: pointer; font-size: 15px; font-weight: 700; }
    .btn-queue:hover { background: #4a7549; }
    .btn-queue:disabled { background: #aaa; cursor: not-allowed; }
    .btn-clear { padding: 10px; background: #fff0f0; border: 1px solid #f5c6c6; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; color: #b00020; }
    .btn-clear:hover { background: #fde8e8; }
    .status-msg { font-size: 13px; text-align: center; min-height: 18px; }
    .status-msg.ok { color: #2e7d32; }
    .status-msg.err { color: #b00020; }

    /* PREVIEW PANEL */
    .preview-panel { flex: 1; overflow: hidden; display: flex; flex-direction: column; background: #e8eaed; }
    .preview-toolbar { background: #fff; border-bottom: 1px solid #e0e0e0; padding: 8px 16px; font-size: 13px; color: #555; flex-shrink: 0; }
    #previewFrame { flex: 1; width: 100%; border: none; background: #fff; }

    /* IMAGE PICKER MODAL */
    .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center; z-index: 100; }
    .modal { background: #fff; border-radius: 16px; width: 600px; max-width: 95vw; max-height: 80vh; display: flex; flex-direction: column; overflow: hidden; }
    .modal-header { padding: 16px 20px; font-size: 15px; font-weight: 700; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
    .modal-close { background: none; border: none; font-size: 20px; cursor: pointer; color: #555; }
    .modal-body { padding: 16px; overflow-y: auto; flex: 1; }
    .img-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; }
    .img-thumb { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 8px; cursor: pointer; border: 2px solid transparent; transition: border-color .15s; }
    .img-thumb:hover { border-color: #5B8C5A; }
    .modal-upload { margin-top: 14px; padding-top: 14px; border-top: 1px solid #eee; }
    .modal-upload label { display: inline-block; padding: 8px 16px; background: #5B8C5A; color: #fff; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; }
    .modal-upload input { display: none; }
    #uploadStatus { font-size: 12px; color: #555; margin-top: 6px; }
  </style>
</head>
<body>
<div class="topbar">
  <h1>🛍️ News Builder</h1>
  <div class="nav-links">
    <a href="/admin/ui">Dashboard</a>
    <a href="/admin/ui/customers">Clientes</a>
    <a href="/admin/email-builder">Email Builder</a>
    <a href="/admin/news-builder" class="active">News Builder</a>
  </div>
</div>

<div class="main">
  <!-- FORM -->
  <div class="form-panel">

    <div class="section">
      <div class="section-title">Asunto del email</div>
      <input type="text" id="subjectLine" value="Novedades en Pika Pika 🛍️" />
    </div>

    <div class="section">
      <div class="section-title">Texto introductorio</div>
      <textarea id="introText">Llegaron novedades a Pika Pika 🎉</textarea>
    </div>

    <div class="section">
      <div class="section-title">Productos</div>
      <div id="productsContainer"></div>
      <button class="btn-add" id="btnAddProduct" onclick="addProduct()">+ Agregar producto</button>
    </div>

    <div class="section">
      <label class="promo-toggle">
        <input type="checkbox" id="promoToggle" onchange="togglePromo()" />
        Incluir banner de promoción
      </label>
      <div id="promoSection" style="display:none;">
        <input type="text" id="promoText" placeholder="Ej: 15% de descuento presentando este email en el local" />
      </div>
    </div>

    <div class="section">
      <div class="section-title">Destinatarios</div>
      <label class="cat-all-label">
        <input type="checkbox" id="catAll" checked onchange="toggleCatAll()" />
        Todos los clientes
      </label>
      <div id="catSection" style="display:none;">
        <div id="catList"><span style="color:#aaa;font-size:12px;">Cargando...</span></div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">Mensaje de cierre <span style="font-weight:400;color:#aaa;font-size:11px;">(opcional)</span></div>
      <textarea id="closingMessage" rows="4" placeholder="Ej: Gracias por acompañarnos 💛&#10;Te esperamos en Pika Pika 🧸✨"></textarea>
    </div>

    <div class="actions">
      <button class="btn-preview" onclick="refreshPreview()">↻ Actualizar preview</button>
      <button class="btn-queue" id="btnQueue" onclick="queueEmails()">Enviar a todos los clientes</button>
      <button class="btn-clear" onclick="clearQueue()">Limpiar cola</button>
      <div class="status-msg" id="statusMsg"></div>
    </div>
  </div>

  <!-- PREVIEW -->
  <div class="preview-panel">
    <div class="preview-toolbar">Preview del email</div>
    <iframe id="previewFrame" title="Preview"></iframe>
  </div>
</div>

<!-- IMAGE PICKER MODAL -->
<div class="modal-overlay" id="pickerModal" style="display:none;">
  <div class="modal">
    <div class="modal-header">
      Elegir imagen
      <button class="modal-close" onclick="closePicker()">✕</button>
    </div>
    <div class="modal-body">
      <div class="img-grid" id="imgGrid"><p style="color:#888;font-size:13px;">Cargando...</p></div>
      <div class="modal-upload">
        <label>
          ⬆ Subir nueva imagen
          <input type="file" accept="image/*" onchange="uploadImage(event)" />
        </label>
        <div id="uploadStatus"></div>
      </div>
    </div>
  </div>
</div>

<script>
  const adminKey = sessionStorage.getItem('builderKey') || '';
  if (!adminKey) window.location.replace('/builder-login?next=/admin/news-builder');

  let products = [];
  let pickerTargetIdx = null;

  function getPayload() {
    return {
      subject_line: document.getElementById('subjectLine').value.trim(),
      intro_text: document.getElementById('introText').value.trim(),
      products: products.map(p => ({
        photo_url:   p.photoUrl   || '',
        name:        p.name        || '',
        description: p.description || '',
        price:       p.price       || '',
      })).filter(p => p.name),
      promo_text: document.getElementById('promoToggle').checked
        ? document.getElementById('promoText').value.trim()
        : '',
      closing_message: document.getElementById('closingMessage').value.trim(),
      categories: getCategories(),
    };
  }

  function renderProductBlocks() {
    const container = document.getElementById('productsContainer');
    container.innerHTML = '';
    products.forEach((p, i) => {
      const div = document.createElement('div');
      div.className = 'product-block';
      div.innerHTML = `
        <div class="product-block-header">
          <span class="product-block-title">Producto ${i + 1}</span>
          ${products.length > 1 ? `<button class="btn-remove" onclick="removeProduct(${i})">✕ Quitar</button>` : ''}
        </div>
        <div class="photo-section">
          ${p.photoUrl ? `<img class="photo-preview" src="${esc(p.photoUrl)}" style="display:block;" />` : ''}
          <div class="photo-url-row">
            <input type="text" placeholder="URL de la foto" value="${esc(p.photoUrl)}"
              oninput="products[${i}].photoUrl = this.value; updatePhotoPreview(${i}, this.value)" />
            <button class="btn-pick" onclick="openPicker(${i})">📷 Elegir</button>
          </div>
        </div>
        <div class="field-row">
          <label class="field-label">Nombre <span class="field-optional">(requerido)</span></label>
          <input type="text" placeholder="Ej: Cochecito Travel" value="${esc(p.name)}"
            oninput="products[${i}].name = this.value" />
        </div>
        <div class="field-row">
          <label class="field-label">Descripción <span class="field-optional">(opcional)</span></label>
          <input type="text" placeholder="Breve descripción del producto" value="${esc(p.description)}"
            oninput="products[${i}].description = this.value" />
        </div>
        <div class="field-row">
          <label class="field-label">Precio <span class="field-optional">(opcional)</span></label>
          <input type="text" placeholder="Ej: $85.000" value="${esc(p.price)}"
            oninput="products[${i}].price = this.value" />
        </div>`;
      container.appendChild(div);
    });
    document.getElementById('btnAddProduct').disabled = products.length >= 3;
  }

  function updatePhotoPreview(idx, url) {
    const block = document.querySelectorAll('.product-block')[idx];
    if (!block) return;
    let img = block.querySelector('.photo-preview');
    if (url) {
      if (!img) {
        img = document.createElement('img');
        img.className = 'photo-preview';
        block.querySelector('.photo-section').prepend(img);
      }
      img.src = url;
      img.style.display = 'block';
    } else if (img) {
      img.style.display = 'none';
    }
  }

  function addProduct() {
    if (products.length >= 3) return;
    products.push({ photoUrl: '', name: '', description: '', price: '' });
    renderProductBlocks();
  }

  function removeProduct(idx) {
    products.splice(idx, 1);
    renderProductBlocks();
  }

  function togglePromo() {
    const checked = document.getElementById('promoToggle').checked;
    document.getElementById('promoSection').style.display = checked ? 'block' : 'none';
  }

  async function refreshPreview() {
    try {
      const res = await fetch('/admin/news-builder/render', {
        method: 'POST',
        headers: { 'x-admin-key': adminKey, 'Content-Type': 'application/json' },
        body: JSON.stringify(getPayload()),
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const html = await res.text();
      const frame = document.getElementById('previewFrame');
      frame.srcdoc = html;
    } catch (e) {
      console.error('Preview error', e);
    }
  }

  async function queueEmails() {
    const btn = document.getElementById('btnQueue');
    const msg = document.getElementById('statusMsg');
    btn.disabled = true;
    msg.textContent = 'Encolando...';
    msg.className = 'status-msg';
    try {
      const res = await fetch('/admin/news-builder/queue', {
        method: 'POST',
        headers: { 'x-admin-key': adminKey, 'Content-Type': 'application/json' },
        body: JSON.stringify(getPayload()),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error');
      const catLabel = data.categories && data.categories.length
        ? ` (${data.categories.join(', ')})`
        : ' (todos los clientes)';
      msg.textContent = `✓ ${data.queued} emails encolados${catLabel}. Se envían en ~5 minutos.`;
      msg.className = 'status-msg ok';
    } catch (e) {
      msg.textContent = 'Error: ' + e.message;
      msg.className = 'status-msg err';
    } finally {
      btn.disabled = false;
    }
  }

  async function clearQueue() {
    const msg = document.getElementById('statusMsg');
    if (!confirm('¿Eliminar todos los emails en cola de News Builder?')) return;
    try {
      const res = await fetch('/admin/news-builder/clear-queue', {
        method: 'DELETE',
        headers: { 'x-admin-key': adminKey },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error');
      msg.textContent = `✓ ${data.deleted} emails eliminados de la cola.`;
      msg.className = 'status-msg ok';
    } catch (e) {
      msg.textContent = 'Error: ' + e.message;
      msg.className = 'status-msg err';
    }
  }

  // ── Image Picker ──────────────────────────────────────────────────────────

  function openPicker(productIdx) {
    pickerTargetIdx = productIdx;
    document.getElementById('pickerModal').style.display = 'flex';
    loadImages();
  }

  function closePicker() {
    document.getElementById('pickerModal').style.display = 'none';
    pickerTargetIdx = null;
  }

  async function loadImages() {
    const grid = document.getElementById('imgGrid');
    grid.innerHTML = '<p style="color:#888;font-size:13px;">Cargando...</p>';
    try {
      const res = await fetch('/admin/news-builder/images', {
        headers: { 'x-admin-key': adminKey },
      });
      const data = await res.json();
      const imgs = data.images || [];
      if (!imgs.length) { grid.innerHTML = '<p style="color:#888;font-size:13px;">Sin imágenes todavía.</p>'; return; }
      grid.innerHTML = imgs.map(img =>
        `<img class="img-thumb" src="${esc(img.url)}" title="${esc(img.name)}"
          onclick="selectImage('${esc(img.url)}')" />`
      ).join('');
    } catch (e) {
      grid.innerHTML = '<p style="color:#b00020;font-size:13px;">Error cargando imágenes.</p>';
    }
  }

  function selectImage(url) {
    if (pickerTargetIdx === null) return;
    products[pickerTargetIdx].photoUrl = url;
    renderProductBlocks();
    closePicker();
    refreshPreview();
  }

  async function uploadImage(event) {
    const file = event.target.files[0];
    if (!file) return;
    const status = document.getElementById('uploadStatus');
    status.textContent = 'Subiendo...';
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await fetch('/admin/news-builder/upload-image', {
        method: 'POST',
        headers: { 'x-admin-key': adminKey },
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error');
      status.textContent = '✓ Subida exitosa';
      if (pickerTargetIdx !== null) {
        products[pickerTargetIdx].photoUrl = data.url;
        renderProductBlocks();
        closePicker();
        refreshPreview();
      } else {
        loadImages();
      }
    } catch (e) {
      status.textContent = 'Error: ' + e.message;
    }
    event.target.value = '';
  }

  function esc(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ── Category filter ────────────────────────────────────────────────────────

  function toggleCatAll() {
    const all = document.getElementById('catAll').checked;
    document.getElementById('catSection').style.display = all ? 'none' : 'block';
  }

  function onCatChange() {
    const boxes = document.querySelectorAll('.cat-check');
    if (boxes.length && Array.from(boxes).every(b => b.checked)) {
      document.getElementById('catAll').checked = true;
      document.getElementById('catSection').style.display = 'none';
    }
  }

  function getCategories() {
    if (document.getElementById('catAll').checked) return [];
    return Array.from(document.querySelectorAll('.cat-check:checked')).map(b => b.value);
  }

  async function loadCategories() {
    try {
      const res = await fetch('/admin/news-builder/categories', { headers: { 'x-admin-key': adminKey } });
      const data = await res.json();
      const cats = data.categories || [];
      const list = document.getElementById('catList');
      if (!cats.length) {
        list.innerHTML = '<span style="color:#aaa;font-size:12px;">Sin categorías registradas.</span>';
        return;
      }
      list.innerHTML = cats.map(cat =>
        `<label class="cat-item">
          <input type="checkbox" class="cat-check" value="${esc(cat)}" onchange="onCatChange()" />
          ${esc(cat)}
        </label>`
      ).join('');
    } catch (e) {
      console.error('Failed to load categories', e);
    }
  }

  // Init
  addProduct();
  loadCategories();
  refreshPreview();
</script>
</body>
</html>"""
    return HTMLResponse(content=html)


# ── API endpoints ──────────────────────────────────────────────────────────────

@router.get("/admin/news-builder/categories", dependencies=[Depends(require_builder_key)])
async def news_list_categories(db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT DISTINCT interest_key FROM customer_interests ORDER BY interest_key"
    )).fetchall()
    return {"categories": [r[0] for r in rows]}


@router.post("/admin/news-builder/render", response_class=Response,
             dependencies=[Depends(require_builder_key)])
async def news_render(request: Request):
    payload = await request.json()
    html = _render_news_html(payload)
    return Response(content=html, media_type="text/html")


@router.post("/admin/news-builder/queue", dependencies=[Depends(require_builder_key)])
async def news_queue(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()

    subject_line = payload.get("subject_line", "Novedades en Pika Pika 🛍️")
    intro_text = payload.get("intro_text", "")
    products = payload.get("products", [])[:3]
    promo_text = payload.get("promo_text", "")
    closing_message = payload.get("closing_message", "")
    categories = payload.get("categories", [])  # [] = all customers

    if not intro_text and not products:
        raise HTTPException(status_code=422, detail="Intro text or at least one product required")

    # Fetch all known categories for the unrecognized-interest fallback
    all_cat_rows = db.execute(text(
        "SELECT DISTINCT interest_key FROM customer_interests"
    )).fetchall()
    all_categories = [r[0] for r in all_cat_rows]

    # Use category filter only when categories are specified and DB has known categories
    use_filter = bool(categories) and bool(all_categories)

    scheduled_for = datetime.now(timezone.utc) + timedelta(minutes=5)
    batch_id = str(uuid.uuid4())

    store_payload = json.dumps({
        "subject_line": subject_line,
        "intro_text": intro_text,
        "products": products,
        "promo_text": promo_text,
        "closing_message": closing_message,
        "categories": categories,
        "batch_id": batch_id,
    })

    base_sql = """
        INSERT INTO message_outbox (
            id, customer_id, to_identity_id, template_key, channel,
            payload, status, scheduled_for, created_at
        )
        SELECT
            gen_random_uuid(), ci.customer_id, ci.id,
            'news_v1', 'email',
            CAST(:payload AS jsonb), 'queued', :scheduled_for, now()
        FROM customer_identities ci
        JOIN (
            SELECT DISTINCT ON (c2.customer_id) c2.customer_id, c2.status
            FROM consents c2
            WHERE c2.channel = 'email' AND c2.purpose = 'promotions'
            ORDER BY c2.customer_id, c2.created_at DESC
        ) latest ON latest.customer_id = ci.customer_id
        WHERE ci.channel = 'email'
          AND latest.status = 'granted'
    """

    params: dict = {
        "payload": store_payload,
        "scheduled_for": scheduled_for,
        "intro_text": intro_text,
    }

    if use_filter:
        # Include customers who match at least one selected category,
        # OR have no recognized interests (no interests at all, or only unknown keys).
        base_sql += """
          AND (
              EXISTS (
                  SELECT 1 FROM customer_interests ki
                  WHERE ki.customer_id = ci.customer_id
                    AND ki.interest_key = ANY(string_to_array(:categories_str, ','))
              )
              OR NOT EXISTS (
                  SELECT 1 FROM customer_interests ki
                  WHERE ki.customer_id = ci.customer_id
                    AND ki.interest_key = ANY(string_to_array(:all_categories_str, ','))
              )
          )
        """
        params["categories_str"] = ",".join(categories)
        params["all_categories_str"] = ",".join(all_categories)

    base_sql += """
          AND NOT EXISTS (
              SELECT 1 FROM message_outbox mo2
              WHERE mo2.to_identity_id = ci.id
                AND mo2.template_key = 'news_v1'
                AND mo2.status = 'queued'
                AND mo2.payload->>'intro_text' = :intro_text
          )
    """

    result = db.execute(text(base_sql), params)
    db.commit()
    return {
        "queued": result.rowcount,
        "batch_id": batch_id,
        "scheduled_for": scheduled_for.isoformat(),
        "categories": categories or None,
    }


@router.delete("/admin/news-builder/clear-queue", dependencies=[Depends(require_builder_key)])
async def news_clear_queue(db: Session = Depends(get_db)):
    result = db.execute(text("""
        DELETE FROM message_outbox
        WHERE status = 'queued'
          AND template_key = 'news_v1'
          AND channel = 'email'
    """))
    db.commit()
    return {"deleted": result.rowcount}


@router.post("/admin/news-builder/upload-image", dependencies=[Depends(require_builder_key)])
async def news_upload_image(file: UploadFile = File(...)):
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported type '{file.content_type}'")
    content = await file.read()
    if len(content) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 5 MB limit")
    url = await _save_image(content, file.filename or "upload.jpg", file.content_type)
    return {"url": url}


@router.get("/admin/news-builder/images", dependencies=[Depends(require_builder_key)])
async def news_list_images():
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url or not service_key:
        return {"images": []}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{supabase_url}/storage/v1/object/list/{_SUPABASE_BUCKET}",
                json={"prefix": "", "limit": 100, "offset": 0,
                      "sortBy": {"column": "created_at", "order": "desc"}},
                headers={"Authorization": f"Bearer {service_key}", "Content-Type": "application/json"},
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=repr(e))
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Could not list images: {resp.text[:200]}")
    files = resp.json()
    images = [
        {"name": f["name"],
         "url": f"{supabase_url}/storage/v1/object/public/{_SUPABASE_BUCKET}/{f['name']}",
         "updated_at": f.get("updated_at", "")}
        for f in files if f.get("name")
    ]
    return {"images": images}
