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