from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
import uuid
from fastapi import APIRouter, Depends, HTTPException


router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/db")
def debug_db(db: Session = Depends(get_db)):
    row = db.execute(text("""
        select
          current_database() as db,
          current_schema() as schema,
          inet_server_addr() as server_ip,
          inet_server_port() as server_port,
          current_user as db_user
    """)).mappings().first()
    return dict(row)


router = APIRouter(prefix="/db-check", tags=["db-check"])

@router.post("/insert-proof")
def insert_proof(db: Session = Depends(get_db)):
    try:
        db.begin()

        email = f"proof-{uuid.uuid4().hex[:8]}@example.com"

        customer_id = db.execute(text("""
            insert into customers (first_name)
            values (:first_name)
            returning id
        """), {"first_name": "PROOF"}).scalar_one()

        identity_id = db.execute(text("""
            insert into customer_identities (customer_id, channel, value, is_primary)
            values (:customer_id, 'email'::channel_type, :value, true)
            returning id
        """), {"customer_id": customer_id, "value": email}).scalar_one()

        db.commit()
        return {"ok": True, "customer_id": str(customer_id), "identity_id": str(identity_id), "email": email}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"insert-proof failed: {repr(e)}")