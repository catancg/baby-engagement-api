from apscheduler.schedulers.blocking import BlockingScheduler
from app.db.session import SessionLocal
from app.jobs.weekly_scheduler import queue_weekly_promo

def run_weekly():
    db = SessionLocal()
    try:
        info = queue_weekly_promo(db)
        print("Weekly queue:", info)
        db.commit()
    except Exception as e:
        db.rollback()
        print("SCHEDULER ERROR:", repr(e))
    finally:
        db.close()

if __name__ == "__main__":
    sched = BlockingScheduler(timezone="UTC")
    sched.add_job(run_weekly, "cron", day_of_week="mon", hour=13, minute=0)
    print("Scheduler started (weekly promo cron).")
    sched.start()