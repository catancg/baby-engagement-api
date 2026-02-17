from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.jobs.weekly_scheduler import queue_weekly_promo

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/queue-weekly")
def admin_queue_weekly(db: Session = Depends(get_db)):
    return queue_weekly_promo(db)
