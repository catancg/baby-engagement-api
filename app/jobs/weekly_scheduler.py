from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
WEEKLY_SEND_HOUR_UTC = 13  # Monday 13:00 UTC

def next_monday_utc_at(hour_utc: int) -> datetime:
    now = datetime.now(timezone.utc)
    # Monday = 0 ... Sunday = 6
    days_ahead = (0 - now.weekday()) % 7
    candidate = (now + timedelta(days=days_ahead)).replace(
        hour=hour_utc, minute=0, second=0, microsecond=0
    )
    # If it's already past Monday@hour this week, schedule next week
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate


def queue_weekly_promo(db: Session):
    """
    Queues one weekly promo email per customer who:
      - has an email identity
      - has latest promotions consent = granted
    """

    # schedule time: "now" (or choose next Monday 10:00 etc.)
    scheduled_for = next_monday_utc_at(WEEKLY_SEND_HOUR_UTC)

    # Find an active weekly email campaign
    campaign = db.execute(text("""
        select id, template_key
        from campaigns
        where is_active = true
          and type = 'weekly_promo'
          and channel = 'email'
        limit 1
    """)).fetchone()

    if not campaign:
        return {"queued": 0, "reason": "No active weekly_promo email campaign"}

    campaign_id, template_key = campaign[0], campaign[1]

    # Insert into outbox using latest consent = granted (audit log style)
    # We dedupe via uq_outbox_dedupe index.
    result = db.execute(text("""
        with latest_consent as (
          select distinct on (customer_id, channel, purpose)
            customer_id, channel, purpose, status
          from consents
          where purpose = 'promotions'
            and channel = 'email'
          order by customer_id, channel, purpose, created_at desc
        ),
        eligible as (
          select c.id as customer_id, ci.id as identity_id
          from customers c
          join customer_identities ci
            on ci.customer_id = c.id
           and ci.channel = 'email'
          join latest_consent lc
            on lc.customer_id = c.id
           and lc.status = 'granted'
        )
        insert into message_outbox (
          campaign_id, customer_id, channel, to_identity_id,
          template_key, payload, scheduled_for, status
        )
        select
          :campaign_id,
          e.customer_id,
          'email'::channel_type,
          e.identity_id,
          :template_key,
          '{}'::jsonb,
          :scheduled_for,
          'queued'::outbox_status
        from eligible e
        on conflict (customer_id, channel, template_key, scheduled_for) do nothing
        returning id
    """), {
        "campaign_id": campaign_id,
        "template_key": template_key,
        "scheduled_for": scheduled_for,
    })

    queued = len(result.fetchall())
    db.commit()
    return {"queued": queued, "scheduled_for": scheduled_for.isoformat()}
