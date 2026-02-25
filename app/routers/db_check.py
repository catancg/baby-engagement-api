from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db

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