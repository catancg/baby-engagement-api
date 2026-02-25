from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
from app.db.session import get_db
from app.schemas.signup import SignupRequest
from app.services.signup_service import create_signup
import json

router = APIRouter(tags=["signup"])

#@router.post("/signup")
#def signup(payload: SignupRequest, db: Session = Depends(get_db)):
#    customer_id, identity_id = create_signup(db, payload)
#    return {"ok": True, "customer_id": str(customer_id), "identity_id": str(identity_id)}
#
#from fastapi import HTTPException
#from sqlalchemy import text

@router.post("/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    try:
        db_info = db.execute(text("select current_database() as db, current_schema() as schema")).first()
        print("DB INFO:", dict(db_info._mapping) if db_info else None)

        print("SIGNUP PAYLOAD:", payload.model_dump())

        

        # 1) customer
        customer_id = db.execute(
            text("""
                insert into customers (first_name)
                values (:first_name)
                returning id
            """),
            {"first_name": payload.name.strip()},
        ).scalar_one()
        print("INSERT customer_id:", customer_id)

        # 2) identity
        identity_id = db.execute(
            text("""
                insert into customer_identities (customer_id, channel, value, is_primary)
                values (:customer_id, 'email'::channel_type, :value, true)
                returning id
            """),
            {"customer_id": customer_id, "value": payload.email.strip().lower()},
        ).scalar_one()
        print("INSERT identity_id:", identity_id)
        # 2.5) Save interests (jsonb array) as customer attribute
        if getattr(payload, "interests", None):
            db.execute(
                text("""
                    insert into customer_attributes (customer_id, key, value)
                    values (:customer_id, 'interests', to_jsonb(CAST(:interests AS json)))
                    on conflict (customer_id, key) do update
                    set value = excluded.value,
                        updated_at = now()
                """),
                {
                    "customer_id": customer_id,
                    "interests": json.dumps(payload.interests),
                },
            )
            print("INSERT interests:", payload.interests)
        # 3) consent (optional)
        if getattr(payload, "consent_promotions", True):
            db.execute(
                text("""
                    insert into consents (customer_id, channel, purpose, status)
                    values (:customer_id, 'email'::channel_type, 'promotions', 'granted')
                """),
                {"customer_id": customer_id},
            )
            print("INSERT consent granted")

        db.commit()
        print("COMMIT DONE")

        return {"ok": True, "customer_id": str(customer_id), "identity_id": str(identity_id)}

    except Exception as e:
        db.rollback()
        print("SIGNUP ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=f"signup failed: {repr(e)}")