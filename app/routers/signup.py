from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.schemas.signup import SignupIn, SignupOut
from app.services.signup_service import create_signup

router = APIRouter()

@router.post("/signup", response_model=SignupOut)
def signup(payload: SignupIn, db: Session = Depends(get_db)):
    try:
        customer_id, identity_id = create_signup(db, payload)
        return {"customer_id": customer_id, "identity_id": identity_id}
    except IntegrityError:
        db.rollback()
        # Most likely: same (channel,value) already exists due to unique constraint
        raise HTTPException(status_code=409, detail="Identity already exists for that channel.")
