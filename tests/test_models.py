import unittest

from Models import Outcome, ResumeBatch, ResumeData, ResumeRecord
from tests.helpers import SAMPLE_STRONG, make_record, resume


class OutcomeTests(unittest.TestCase):
    def test_parse_is_case_insensitive(self):
        self.assertIs(Outcome.parse("accepted"), Outcome.ACCEPTED)
        self.assertIs(Outcome.parse("  FLAGGED "), Outcome.FLAGGED)

    def test_parse_unknown_or_non_text_is_none(self):
        self.assertIsNone(Outcome.parse("maybe"))
        self.assertIsNone(Outcome.parse(None))


class ResumeDataTests(unittest.TestCase):
    def test_properties_return_copies_so_the_object_cannot_be_changed(self):
        data = resume(SAMPLE_STRONG)
        data.skills.append("hacked")
        data.experience_by_field["IT"] = 99
        data.certificates_by_industry["IT"].append("hacked")
        self.assertNotIn("hacked", data.skills)
        self.assertEqual(data.experience_by_field["IT"], 5)
        self.assertNotIn("hacked", data.certificates_by_industry["IT"])

    def test_from_dict_reads_all_fields(self):
        data = resume(SAMPLE_STRONG)
        self.assertEqual(data.filename, "arthur_goatson.pdf")
        self.assertEqual(data.name, "Arthur Goatson")


class ResumeBatchTests(unittest.TestCase):
    def test_empty_batch(self):
        batch = ResumeBatch()
        self.assertTrue(batch.is_empty())
        self.assertEqual(len(batch), 0)
        self.assertEqual(list(batch), [])

    def test_batch_groups_items_that_exist_independently(self):
        a = ResumeData("a.pdf", "A", [], {}, {})
        batch = ResumeBatch([a])
        batch.add(ResumeData("b.pdf", "B", [], {}, {}))
        self.assertEqual(batch.filenames, ["a.pdf", "b.pdf"])
        del batch
        self.assertEqual(a.name, "A")   # the part outlives the whole


class ResumeRecordTests(unittest.TestCase):
    def test_id_can_be_assigned_once_only(self):
        record = make_record()
        self.assertIsNone(record.id)
        record.assign_id(3)
        self.assertEqual(record.display_id, "03")
        with self.assertRaises(ValueError):
            record.assign_id(4)

    def test_unknown_outcome_is_rejected(self):
        with self.assertRaises(ValueError):
            make_record(outcome="Maybe")

    def test_final_outcome_is_original_until_reviewed(self):
        record = make_record(outcome="Flagged")
        self.assertTrue(record.needs_review)
        self.assertIs(record.final_outcome, Outcome.FLAGGED)

    def test_review_sets_final_outcome_and_keeps_original(self):
        record = make_record(outcome="Flagged")
        record.apply_review("Accepted", " good fit ", "2026-02-01 09:00:00")
        self.assertIs(record.outcome, Outcome.FLAGGED)
        self.assertIs(record.final_outcome, Outcome.ACCEPTED)
        self.assertEqual(record.review_note, "good fit")
        self.assertFalse(record.needs_review)

    def test_only_flagged_records_can_be_reviewed(self):
        with self.assertRaises(ValueError):
            make_record(outcome="Accepted", score=9).apply_review("Rejected", "", "t")

    def test_a_record_cannot_be_reviewed_twice(self):
        record = make_record()
        record.apply_review("Rejected", "", "t")
        with self.assertRaises(ValueError):
            record.apply_review("Accepted", "", "t")

    def test_review_decision_must_be_accepted_or_rejected(self):
        with self.assertRaises(ValueError):
            make_record().apply_review("Flagged", "", "t")

    def test_without_id_copies_everything_but_the_id(self):
        record = make_record(review_decision="Rejected", review_note="no", reviewed_at="t")
        record.assign_id(5)
        copy = record.without_id()
        self.assertIsNone(copy.id)
        self.assertEqual(copy.review_decision, Outcome.REJECTED)
        self.assertEqual(copy.name, record.name)

    def test_lists_are_copied_out(self):
        record = make_record(it_certs=["a"])
        record.it_certs.append("b")
        self.assertEqual(record.it_certs, ["a"])


if __name__ == "__main__":
    unittest.main()
