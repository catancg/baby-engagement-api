from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

@router.get("/unsubscribe")
def unsubscribe(
    channel: str = Query(...),
    value: str = Query(...),
    db: Session = Depends(get_db)
):
    result = db.execute(
        text("""
            select c.id
            from customers c
            join customer_identities ci on ci.customer_id = c.id
            where ci.channel = CAST(:channel AS channel_type)
            and ci.value = :value
        """),
        {"channel": channel, "value": value}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    customer_id = result[0]

    db.execute(
        text("""
            insert into consents (customer_id, channel, purpose, status, revoked_at, proof)
            values (:customer_id,
                    CAST(:channel AS channel_type),
                    'promotions'::consent_purpose,
                    'revoked'::consent_status,
                    now(),
                    '{}'::jsonb)
        """),
        {"customer_id": customer_id, "channel": channel}
    )

    db.commit()

    return {"message": "Te diste de baja correctamente."}
