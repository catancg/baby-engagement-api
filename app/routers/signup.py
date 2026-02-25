from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.signup import SignupRequest
from app.services.signup_service import create_signup

router = APIRouter(tags=["signup"])

@router.post("/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    customer_id, identity_id = create_signup(db, payload)
    return {"ok": True, "customer_id": str(customer_id), "identity_id": str(identity_id)}