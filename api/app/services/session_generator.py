"""Generate lecture_sessions for every slot for every week of the current term.

Per brief §5.3: a scheduled job generates `lecture_sessions` for every slot
for every week of the current term.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.models import (
    LectureSession,
    Term,
    TimetableSlot,
)
from app.models.enums import SessionStatus

logger = logging.getLogger("app.sessions")


def generate_sessions_for_term(db: Session, term: Term | None = None) -> int:
    """Generate lecture_sessions for every slot, every week of the term.

    Idempotent: skips (offering_id, date) pairs that already exist.
    Returns the number of new sessions created.
    """
    if term is None:
        term = db.scalar(select(Term).where(Term.is_current.is_(True)))
        if not term:
            logger.warning("No current term; skipping session generation")
            return 0

    slots = db.scalars(select(TimetableSlot)).all()
    if not slots:
        return 0

    # Map (offering_id, date) → existing session date for dedup
    existing = {
        (str(s.offering_id), s.date.isoformat())
        for s in db.scalars(
            select(LectureSession).where(LectureSession.offering_id.in_(
                [s.offering_id for s in slots]
            ))
        ).all()
    }

    created = 0
    # Walk from term.start_date to term.end_date, 1 day at a time
    cur = term.start_date
    while cur <= term.end_date:
        for slot in slots:
            # weekday(): Monday=0..Sunday=6. Our slots use 0=Sunday..4=Thursday.
            python_weekday = cur.weekday()
            slot_weekday_sun0 = (python_weekday + 1) % 7  # convert Mon=0 → Sun=0
            if slot_weekday_sun0 != slot.weekday:
                continue
            key = (str(slot.offering_id), cur.isoformat())
            if key in existing:
                continue
            starts_at = datetime.combine(cur, slot.start_time)
            ends_at = datetime.combine(cur, slot.end_time)
            db.add(
                LectureSession(
                    offering_id=slot.offering_id,
                    slot_id=slot.id,
                    date=cur,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    status=SessionStatus.scheduled,
                )
            )
            created += 1
        cur += timedelta(days=1)
    db.commit()
    logger.info("Generated %d lecture sessions for term %s", created, term.name)
    return created


def run() -> int:
    """CLI entrypoint: `python -c "from app.services.session_generator import run; run()"`"""
    db = SessionLocal()
    try:
        return generate_sessions_for_term(db)
    finally:
        db.close()


if __name__ == "__main__":
    run()
