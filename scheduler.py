from apscheduler.schedulers.blocking import BlockingScheduler
from app.db.session import SessionLocal
from app.jobs.weekly_scheduler import queue_weekly_promo

def run_weekly():
    db = SessionLocal()
    try:
        info = queue_weekly_promo(db)
        print("Weekly queue:", info)
    finally:
        db.close()

if __name__ == "__main__":
    sched = BlockingScheduler(timezone="UTC")
    # Every Monday at 13:00 UTC (10:00 Argentina typically, adjust if you prefer)
    sched.add_job(run_weekly, "cron", day_of_week="mon", hour=13, minute=0)
    print("Scheduler started (weekly promo cron).")
    sched.start()
