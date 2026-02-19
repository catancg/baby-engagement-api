from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

@router.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    v = db.execute(text("select 1 as ok")).mappings().one()
    return {"db": v["ok"]}
