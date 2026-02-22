import os
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin_key(x_admin_key: str | None = Header(default=None)):
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY not set")
    if x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.get("/summary", dependencies=[Depends(require_admin_key)])
def summary(db: Session = Depends(get_db)):
    counts = db.execute(text("""
        select
          (select count(*) from customers) as customers,
          (select count(*) from customer_identities) as identities,
          (select count(*) from consents) as consents,
          (select count(*) from message_outbox) as outbox
    """)).mappings().one()

    outbox_by_status = db.execute(text("""
        select status, count(*) as count
        from message_outbox
        group by status
        order by count(*) desc
    """)).mappings().all()

    # If you have the view; otherwise we’ll fallback to counts from consents
    try:
        consent_by_status = db.execute(text("""
            select status, count(*) as count
            from v_current_promotions_consent
            group by status
            order by count(*) desc
        """)).mappings().all()
    except Exception:
        consent_by_status = []

    return {
        "counts": dict(counts),
        "outbox_by_status": outbox_by_status,
        "current_promotions_consent_by_status": consent_by_status,
    }

@router.get("/outbox", dependencies=[Depends(require_admin_key)])
def outbox(
    status: str = Query(default="queued"),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows = db.execute(text("""
        select
          mo.id as outbox_id,
          mo.status,
          mo.template_key,
          mo.scheduled_for,
          mo.sent_at,
          mo.created_at,
          c.first_name,
          ci.channel,
          ci.value as recipient
        from message_outbox mo
        join customers c on c.id = mo.customer_id
        join customer_identities ci on ci.id = mo.to_identity_id
        where mo.status = :status
        order by mo.created_at desc
        limit :limit
    """), {"status": status, "limit": limit}).mappings().all()

    return {"status": status, "items": rows}

@router.get("/debug/identity", dependencies=[Depends(require_admin_key)])
def debug_identity(
    channel: str = Query(...),
    value: str = Query(...),
    db: Session = Depends(get_db),
):
    value_norm = value.strip()
    if channel.lower() == "instagram":
        value_norm = value_norm.lstrip("@")

    customer = db.execute(text("""
        select c.id as customer_id, c.first_name, c.created_at
        from customers c
        join customer_identities ci on ci.customer_id = c.id
        where ci.channel = CAST(:channel AS channel_type)
          and ci.value = :value
        limit 1
    """), {"channel": channel, "value": value_norm}).mappings().first()

    if not customer:
        raise HTTPException(status_code=404, detail="Identity not found")

    consent = None
    try:
        consent = db.execute(text("""
            select status, effective_at
            from v_current_promotions_consent
            where customer_id = :customer_id
              and channel = CAST(:channel AS channel_type)
              and purpose = 'promotions'
            limit 1
        """), {"customer_id": customer["customer_id"], "channel": channel}).mappings().first()
    except Exception:
        consent = None

    outbox_recent = db.execute(text("""
        select id as outbox_id, status, template_key, scheduled_for, sent_at, created_at
        from message_outbox
        where customer_id = :customer_id
          and channel = CAST(:channel AS channel_type)
        order by created_at desc
        limit 25
    """), {"customer_id": customer["customer_id"], "channel": channel}).mappings().all()

    return {
        "customer": customer,
        "current_promotions_consent": consent,
        "recent_outbox": outbox_recent,
    }
