import logging
from datetime import datetime

from Models.outcome import Outcome
from DataManager.review_error import ReviewError

logger = logging.getLogger("ReviewService")


class ReviewService:
    def __init__(self, data_manager, clock=datetime.now):
        self._data_manager = data_manager
        self._clock = clock

    def pending_reviews(self):
        return [r for r in self._data_manager.filter_records(outcome=Outcome.FLAGGED) if r.needs_review]

    def submit_review(self, record_id, decision, note=""):
        record = self._data_manager.get_record(record_id)
        if record is None:
            raise ReviewError(f"No record with id {record_id}.")
        try:
            record.apply_review(decision, note, self._clock().strftime("%Y-%m-%d %H:%M:%S"))
        except ValueError as e:
            raise ReviewError(str(e)) from e
        if not self._data_manager.update_record(record):
            raise ReviewError("The review could not be saved.")
        logger.info(f"Record {record.display_id} reviewed: {record.review_decision.value}")
        return record

    def summary(self):
        records = self._data_manager.load_records()
        return {
            "total": len(records),
            "flagged": sum(1 for r in records if r.outcome is Outcome.FLAGGED),
            "pending": sum(1 for r in records if r.needs_review),
            "reviewed_accepted": sum(1 for r in records if r.is_reviewed and r.review_decision is Outcome.ACCEPTED),
            "reviewed_rejected": sum(1 for r in records if r.is_reviewed and r.review_decision is Outcome.REJECTED),
        }
