import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.session import get_db
from app.schemas.signup import SignupRequest, validate_mx
from app.services.signup_service import create_signup

router = APIRouter(tags=["signup"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


@router.post("/signup")
@limiter.limit("10/minute")
def signup(request: Request, payload: SignupRequest, db: Session = Depends(get_db)):
    try:
        validate_mx(payload.email)
        customer_id, identity_id, is_new = create_signup(db, payload)
        db.commit()
        if not is_new:
            raise HTTPException(status_code=409, detail="already_registered")
        return {"ok": True, "customer_id": str(customer_id), "identity_id": str(identity_id)}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("SIGNUP ERROR: %s", repr(e))
        raise HTTPException(status_code=500, detail="Signup failed, please try again")
