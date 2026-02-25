import os
import time
from app.db.session import SessionLocal
from app.jobs.outbox_worker import fetch_next_batch, mark_sent, mark_failed
from app.email.templates import render_email
from app.email.smtp import send_smtp

MODE = os.getenv("WORKER_MODE", "DRY_RUN").upper()  # DRY_RUN | TEST | LIVE

def run():
    print(f"Worker started. MODE={MODE}. Polling outbox...")

    while True:
        db = SessionLocal()
        try:
            db.begin()
            batch = fetch_next_batch(db, batch_size=25)

            if not batch:
                db.commit()
                time.sleep(3)
                continue

            for outbox_id, template_key, to_email in batch:
                try:
                    subject, body = render_email(template_key, {"email": to_email})

                    if MODE == "DRY_RUN":
                        print(f"DRY_RUN -> Would send {outbox_id} to: {to_email} template: {template_key}")
                        # IMPORTANT: do not mark as sent; but also avoid infinite spam:
                        # mark_failed or "mark_deferred" is better long-term.
                        # For now: sleep a little so logs don't spam
                        time.sleep(0.2)

                    else:
                        send_smtp(to_email, subject, body)

                        if MODE in ("TEST", "LIVE"):
                            mark_sent(db, outbox_id)

                        print("SENT", outbox_id, "->", to_email)

                except Exception as e:
                    mark_failed(db, outbox_id, repr(e))
                    print("FAILED", outbox_id, "->", to_email, "error:", repr(e))

            db.commit()

        except Exception as e:
            db.rollback()
            print("WORKER LOOP ERROR:", repr(e))
            time.sleep(2)
        finally:
            db.close()

if __name__ == "__main__":
    run()