import logging
from datetime import datetime

from models import Outcome

logger = logging.getLogger("ReviewService")


class ReviewError(Exception):
    """A review could not be recorded (unknown record, wrong state, bad decision)."""


class ReviewService:
    def __init__(self, data_manager, clock=datetime.now):
        self._data_manager = data_manager
        self._clock = clock

    def pending_reviews(self):
        #Flagged records that nobody has reviewed yet
        return [r for r in self._data_manager.filter_records(outcome=Outcome.FLAGGED) if r.needs_review]

    def submit_review(self, record_id, decision, note=""):
        #Records a decision (Accepted or Rejected) for a Flagged record and saves it
        #Returns the updated record. Raises ReviewError when it cannot be done
        
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