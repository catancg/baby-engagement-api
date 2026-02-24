import os
import hmac
import hashlib
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter(prefix="/webhooks/meta", tags=["meta-webhooks"])

VERIFY_TOKEN = os.getenv("IG_WEBHOOK_VERIFY_TOKEN", "")
APP_SECRET = os.getenv("META_APP_SECRET", "")

# NEW: feature flag to make local testing easy
VERIFY_SIGNATURES = os.getenv("META_VERIFY_SIGNATURES", "true").lower() == "true"


def verify_signature(app_secret: str, signature_header: str | None, body: bytes) -> bool:
    """
    Meta sends:
      X-Hub-Signature-256: sha256=<hex>
    """
    # If we disabled verification, always allow
    if not VERIFY_SIGNATURES:
        return True

    # In prod you should have a secret; if missing, fail closed
    if not app_secret:
        return False

    # Must have the header
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    their_sig = signature_header.split("sha256=", 1)[1].strip()
    our_sig = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(their_sig, our_sig)

@router.get("")
async def verify_webhook(request: Request):
    print("FULL QUERY:", request.query_params)

    hub_mode = request.query_params.get("hub.mode")
    hub_verify_token = request.query_params.get("hub.verify_token")
    hub_challenge = request.query_params.get("hub.challenge")

    print("hub_mode:", hub_mode)
    print("hub_verify_token:", hub_verify_token)
    print("hub_challenge:", hub_challenge)

    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return hub_challenge or ""

    raise HTTPException(status_code=403, detail="Verification failed")
@router.post("")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()

    # Verify signature if configured
    sig = request.headers.get("x-hub-signature-256")
    print("META SIG HEADER:", sig)
    print("APP_SECRET set?:", bool(APP_SECRET), "len:", len(APP_SECRET or ""))
    print("RAW BODY len:", len(raw))
    if not verify_signature(APP_SECRET, sig, raw):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    entries = payload.get("entry", [])

    captured = []

    try:
        for entry in entries:
            for ev in entry.get("messaging", []):
                sender = ev.get("sender", {}).get("id")
                message = ev.get("message", {}) or {}
                text_msg = (message.get("text") or "").strip()

                if not sender:
                    continue

                channel = "instagram"  # later: detect facebook vs instagram
                sender_value = str(sender)

                # 1) Find existing identity (prevents duplicate customers)
                row = db.execute(
                    text("""
                        select ci.id as identity_id, ci.customer_id
                        from customer_identities ci
                        where ci.channel = :channel::channel_type
                          and ci.value = :value
                        limit 1
                    """),
                    {"channel": channel, "value": sender_value},
                ).first()

                if row:
                    identity_id = row.identity_id
                    customer_id = row.customer_id
                else:
                    # 2) Create customer
                    customer_id = db.execute(
                        text("""
                            insert into customers (first_name)
                            values (:first_name)
                            returning id
                        """),
                        {"first_name": "IG Lead"},
                    ).scalar_one()

                    # 3) Create identity (NO reassignment on conflict)
                    identity_id = db.execute(
                        text("""
                            insert into customer_identities (customer_id, channel, value, is_primary)
                            values (:customer_id, :channel::channel_type, :value, true)
                            on conflict (channel, value) do nothing
                            returning id
                        """),
                        {"customer_id": customer_id, "channel": channel, "value": sender_value},
                    ).scalar_one_or_none()

                    # If a race happened and identity already existed, fetch it
                    if identity_id is None:
                        row2 = db.execute(
                            text("""
                                select ci.id as identity_id, ci.customer_id
                                from customer_identities ci
                                where ci.channel = :channel::channel_type
                                  and ci.value = :value
                                limit 1
                            """),
                            {"channel": channel, "value": sender_value},
                        ).first()
                        if not row2:
                            raise RuntimeError("Identity insert race: could not fetch existing identity")
                        identity_id = row2.identity_id
                        customer_id = row2.customer_id

                # 4) Consent only if explicit keyword
                if text_msg.lower() in {"alta", "si", "si promos", "acepto"}:
                    db.execute(
                        text("""
                            insert into consents (customer_id, channel, purpose, status, source)
                            values (:customer_id, :channel::channel_type, 'promotions', 'granted', 'ig_dm')
                        """),
                        {"customer_id": customer_id, "channel": channel},
                    )

                captured.append({
                    "channel": channel,
                    "sender_id": sender_value,
                    "text": text_msg,
                    "customer_id": str(customer_id),
                    "identity_id": str(identity_id),
                })

        db.commit()
        return {"ok": True, "captured": captured}

    except Exception:
        db.rollback()
        raise