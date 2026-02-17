from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone

from app.schemas.signup import SignupIn

def create_signup(db: Session, data: SignupIn) -> tuple[str, str]:
    # 1) Create customer
    customer_id = db.execute(
        text("""
            insert into customers (first_name, source)
            values (:first_name, 'qr')
            returning id
        """),
        {"first_name": data.first_name.strip()},
    ).scalar_one()

    # 2) Create identity
    identity_id = db.execute(
        text("""
            insert into customer_identities (customer_id, channel, value, is_primary)
            values (:customer_id, CAST(:channel AS channel_type), :value, true)
            returning id
        """),
        {"customer_id": customer_id, "channel": data.channel, "value": data.value.strip()},
    ).scalar_one()

    # 3) Consent
    if data.consent_promotions:
        db.execute(
            text("""
                insert into consents (customer_id, channel, purpose, status, granted_at, proof)
                values (:customer_id,
                        CAST(:channel AS channel_type),
                        'promotions'::consent_purpose,
                        'granted'::consent_status,
                        now(),
                        jsonb_build_object('method','qr_form','version','v1'))
            """),
            {"customer_id": customer_id, "channel": data.channel},
        )

    # 4) Baby stage attribute (optional)
    if data.baby_stage:
        db.execute(
            text("""
                insert into customer_attributes (customer_id, key, value)
                values (:customer_id, 'baby_stage', to_jsonb(CAST(:stage AS text)))
                on conflict (customer_id, key) do update
                set value = excluded.value, updated_at = now()
            """),
            {"customer_id": customer_id, "stage": data.baby_stage},
        )

    db.commit()
    return str(customer_id), str(identity_id)
