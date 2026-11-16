import unittest
from datetime import datetime

from DataManager import DataManager, ReviewError, ReviewService, SqliteRecordRepository
from Models import Outcome
from tests.helpers import make_record


class ReviewServiceTests(unittest.TestCase):
    def setUp(self):
        repo = SqliteRecordRepository(":memory:")
        self.addCleanup(repo.close)
        self.data = DataManager(repo)
        self.data.save_records([
            make_record("Accepted One", 9.0, "Accepted"),     # id 1
            make_record("Flagged One", 6.0, "Flagged"),       # id 2
            make_record("Rejected One", 2.0, "Rejected"),     # id 3
            make_record("Flagged Two", 5.5, "Flagged"),       # id 4
        ])
        self.service = ReviewService(self.data, clock=lambda: datetime(2026, 5, 6, 7, 8, 9))

    def test_pending_reviews_lists_only_unreviewed_flagged_records(self):
        self.assertEqual([r.name for r in self.service.pending_reviews()], ["Flagged One", "Flagged Two"])

    def test_submit_review_saves_decision_note_and_time(self):
        record = self.service.submit_review(2, "Accepted", "  great portfolio ")
        self.assertIs(record.final_outcome, Outcome.ACCEPTED)
        stored = self.data.get_record(2)
        self.assertIs(stored.review_decision, Outcome.ACCEPTED)
        self.assertEqual(stored.review_note, "great portfolio")
        self.assertEqual(stored.reviewed_at, "2026-05-06 07:08:09")

    def test_original_outcome_is_kept_for_the_audit_trail(self):
        self.service.submit_review(2, "Rejected", "missing core skills")
        stored = self.data.get_record(2)
        self.assertIs(stored.outcome, Outcome.FLAGGED)
        self.assertIs(stored.final_outcome, Outcome.REJECTED)

    def test_reviewed_records_leave_the_pending_list(self):
        self.service.submit_review(2, "Accepted")
        self.assertEqual([r.name for r in self.service.pending_reviews()], ["Flagged Two"])

    def test_decision_is_case_insensitive(self):
        self.assertIs(self.service.submit_review(4, "rejected").review_decision, Outcome.REJECTED)

    def test_unknown_record_is_an_error(self):
        with self.assertRaises(ReviewError):
            self.service.submit_review(99, "Accepted")

    def test_only_flagged_records_can_be_reviewed(self):
        for record_id in (1, 3):
            with self.assertRaises(ReviewError):
                self.service.submit_review(record_id, "Accepted")

    def test_a_record_cannot_be_reviewed_twice(self):
        self.service.submit_review(2, "Accepted")
        with self.assertRaises(ReviewError):
            self.service.submit_review(2, "Rejected")

    def test_invalid_decision_is_an_error_and_changes_nothing(self):
        for bad in ("Flagged", "maybe", "", None):
            with self.assertRaises(ReviewError):
                self.service.submit_review(2, bad)
        self.assertFalse(self.data.get_record(2).is_reviewed)

    def test_summary_counts(self):
        self.service.submit_review(2, "Accepted")
        self.service.submit_review(4, "Rejected")
        self.assertEqual(self.service.summary(), {
            "total": 4, "flagged": 2, "pending": 0, "reviewed_accepted": 1, "reviewed_rejected": 1})


if __name__ == "__main__":
    unittest.main()
