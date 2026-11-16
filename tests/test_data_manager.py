import os
import shutil
import tempfile
import unittest

from DataManager import (DataManager, InMemoryRecordRepository, RecordRepository,
                          RepositoryError, SqliteRecordRepository)
from Models import Outcome
from tests.helpers import make_record


class RepositoryContract:

    def test_add_assigns_sequential_ids(self):
        a, b = make_record("A"), make_record("B")
        self.assertEqual(self.repo.add(a), 1)
        self.assertEqual(self.repo.add(b), 2)
        self.assertEqual((a.id, b.id), (1, 2))

    def test_add_many_keeps_order_and_continues_ids(self):
        self.repo.add(make_record("first"))
        records = [make_record("B"), make_record("C")]
        self.assertEqual(self.repo.add_many(records), [2, 3])
        self.assertEqual([r.name for r in self.repo.list_all()], ["first", "B", "C"])

    def test_get_returns_the_stored_record(self):
        record = make_record("Arthur", score=9.5, outcome="Accepted", it_certs=["aws ccp", "cka"])
        self.repo.add(record)
        loaded = self.repo.get(record.id)
        self.assertEqual(loaded.name, "Arthur")
        self.assertEqual(loaded.score, 9.5)
        self.assertIs(loaded.outcome, Outcome.ACCEPTED)
        self.assertEqual(loaded.it_certs, ["aws ccp", "cka"])
        self.assertEqual(loaded.certificates, {"it": ["aws ccp", "cka"]})
        self.assertEqual(loaded.timestamp, "2026-01-01 10:00:00")

    def test_get_unknown_id_is_none(self):
        self.assertIsNone(self.repo.get(99))

    def test_list_all_on_an_empty_store(self):
        self.assertEqual(self.repo.list_all(), [])

    def test_update_changes_the_stored_record(self):
        record = make_record("A", outcome="Flagged")
        self.repo.add(record)
        stored = self.repo.get(record.id)
        stored.apply_review("Accepted", "strong referee", "2026-02-02 08:00:00")
        self.assertTrue(self.repo.update(stored))
        again = self.repo.get(record.id)
        self.assertIs(again.final_outcome, Outcome.ACCEPTED)
        self.assertEqual(again.review_note, "strong referee")
        self.assertIs(again.outcome, Outcome.FLAGGED) 

    def test_update_unknown_record_returns_false(self):
        ghost = make_record()
        ghost.assign_id(42)
        self.assertFalse(self.repo.update(ghost))

    def test_delete(self):
        a, b = make_record("A"), make_record("B")
        self.repo.add_many([a, b])
        self.assertTrue(self.repo.delete(a.id))
        self.assertEqual([r.name for r in self.repo.list_all()], ["B"])
        self.assertFalse(self.repo.delete(a.id))

    def test_ids_are_not_reused_while_later_records_exist(self):
        a, b = make_record("A"), make_record("B")
        self.repo.add_many([a, b])
        self.repo.delete(a.id)
        c = make_record("C")
        self.repo.add(c)
        self.assertEqual(c.id, 3)

    def test_query_by_outcome_is_case_insensitive(self):
        self.repo.add_many([make_record("A", 9, "Accepted"), make_record("B", 6, "Flagged"),
                            make_record("C", 2, "Rejected")])
        self.assertEqual([r.name for r in self.repo.query(outcome="flagged")], ["B"])
        self.assertEqual([r.name for r in self.repo.query(outcome=Outcome.REJECTED)], ["C"])
        self.assertEqual(self.repo.query(outcome="nonsense"), [])

    def test_query_by_score_range_is_inclusive(self):
        self.repo.add_many([make_record(n, s, "Flagged") for n, s in (("A", 4.5), ("B", 6.0), ("C", 7.5))])
        self.assertEqual([r.name for r in self.repo.query(min_score=6.0)], ["B", "C"])
        self.assertEqual([r.name for r in self.repo.query(max_score=6.0)], ["A", "B"])
        self.assertEqual([r.name for r in self.repo.query(min_score=6.0, max_score=6.0)], ["B"])

    def test_query_combines_filters_with_and(self):
        self.repo.add_many([make_record("A", 9, "Accepted"), make_record("B", 8, "Flagged"),
                            make_record("C", 5, "Flagged")])
        self.assertEqual([r.name for r in self.repo.query("Flagged", min_score=6)], ["B"])

    def test_query_without_filters_returns_everything(self):
        self.repo.add_many([make_record("A"), make_record("B")])
        self.assertEqual(len(self.repo.query()), 2)

    def test_text_with_separators_survives_a_round_trip(self):
        record = make_record("O'Brien, Pat || Jr", outcome="Flagged")
        self.repo.add(record)
        stored = self.repo.get(record.id)
        stored.apply_review("Rejected", "line one\nline two || three", "t")
        self.repo.update(stored)
        again = self.repo.get(record.id)
        self.assertIn("O'Brien", again.name)
        self.assertEqual(again.review_decision, Outcome.REJECTED)
        for word in ("line one", "line two", "three"):
            self.assertIn(word, again.review_note)



class SqliteRepositoryTests(RepositoryContract, unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "nested", "records.db")
        self.repo = SqliteRecordRepository(self.path)
        self.addCleanup(self.repo.close)

    def test_creates_missing_folders_and_the_database(self):
        self.assertTrue(os.path.exists(self.path))

    def test_records_persist_across_separate_runs(self):
        self.repo.add(make_record("Persistent"))
        self.repo.close()
        reopened = SqliteRecordRepository(self.path)
        self.addCleanup(reopened.close)
        self.assertEqual([r.name for r in reopened.list_all()], ["Persistent"])

    def test_corrupt_database_is_moved_aside_and_replaced(self):
        self.repo.close()
        with open(self.path, "wb") as f:
            f.write(b"this is definitely not a sqlite database" * 20)
        fresh = SqliteRecordRepository(self.path)
        self.addCleanup(fresh.close)
        self.assertEqual(fresh.list_all(), [])
        quarantined = [n for n in os.listdir(os.path.dirname(self.path)) if ".corrupt-" in n]
        self.assertEqual(len(quarantined), 1)
        fresh.add(make_record("After recovery"))
        self.assertEqual(len(fresh.list_all()), 1)

    def test_closed_connection_raises_repository_error(self):
        self.repo.close()
        with self.assertRaises(RepositoryError):
            self.repo.list_all()

    def test_context_manager_closes_the_connection(self):
        with SqliteRecordRepository(":memory:") as repo:
            repo.add(make_record())
        with self.assertRaises(RepositoryError):
            repo.list_all()

    def test_add_many_is_all_or_nothing(self):
        good, bad = make_record("Good"), make_record("Bad")
        bad._score = None   # makes the NOT NULL column fail on insert
        with self.assertRaises(RepositoryError):
            self.repo.add_many([good, bad])
        self.assertEqual(self.repo.list_all(), [])
        self.assertIsNone(good.id)

    def test_a_corrupt_row_is_skipped(self):
        self.repo.add(make_record("Good"))
        conn = self.repo._SqliteRecordRepository__connection
        conn.execute("INSERT INTO records (name, skills, it_experience_years, certificates, it_certs, "
                     "missing_skills_count, score, outcome, timestamp) VALUES "
                     "('Bad','not json',1,'{}','[]',0,1.0,'Maybe','t')")
        conn.commit()
        self.assertEqual([r.name for r in self.repo.list_all()], ["Good"])



class InMemoryRepositoryTests(RepositoryContract, unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryRecordRepository()


class RecordRepositoryInterfaceTests(unittest.TestCase):
    def test_sqlite_is_a_record_repository(self):
        self.assertTrue(issubclass(SqliteRecordRepository, RecordRepository))

    def test_the_interface_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            RecordRepository()


class DataManagerTests(unittest.TestCase):
    def setUp(self):
        self.repo = SqliteRecordRepository(":memory:")
        self.addCleanup(self.repo.close)
        self.data = DataManager(self.repo)

    def test_save_returns_the_saved_records_with_ids(self):
        saved = self.data.save_records([make_record("A"), make_record("B")])
        self.assertEqual([r.id for r in saved], [1, 2])
        self.assertEqual(len(self.data.load_records()), 2)

    def test_save_nothing(self):
        self.assertEqual(self.data.save_records([]), [])

    def test_save_failure_is_reported_not_raised(self):
        self.repo.close()
        self.assertEqual(self.data.save_records([make_record()]), [])
        self.assertEqual(self.data.load_records(), [])
        self.assertEqual(self.data.filter_records(outcome="Flagged"), [])
        self.assertIsNone(self.data.get_record(1))
        self.assertFalse(self.data.delete_record(1))

    def test_filter_get_update_delete(self):
        self.data.save_records([make_record("A", 9, "Accepted"), make_record("B", 6, "Flagged")])
        self.assertEqual([r.name for r in self.data.filter_records(outcome="Flagged")], ["B"])
        record = self.data.get_record(2)
        record.apply_review("Rejected", "", "t")
        self.assertTrue(self.data.update_record(record))
        self.assertTrue(self.data.delete_record(1))
        self.assertEqual([r.name for r in self.data.load_records()], ["B"])


class DataManagerSubstitutionTests(unittest.TestCase):
    def test_data_manager_works_the_same_on_sqlite_and_in_memory(self):
        with tempfile.TemporaryDirectory() as d:
            repositories = [SqliteRecordRepository(os.path.join(d, "a.db")), InMemoryRecordRepository()]
            results = []
            for repository in repositories:
                data = DataManager(repository)
                data.save_records([make_record("A", 9, "Accepted"), make_record("B", 6, "Flagged")])
                results.append(([r.name for r in data.load_records()],
                                [r.name for r in data.filter_records(outcome="Flagged")]))
                data.close()
            self.assertEqual(results[0], results[1])
            self.assertEqual(results[0], (["A", "B"], ["B"]))


if __name__ == "__main__":
    unittest.main()
