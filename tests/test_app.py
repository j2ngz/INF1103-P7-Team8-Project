"""
End-to-end tests for app.py: the whole pipeline with a FAKE AI client and temp folders.
These prove the four managers work together without any live API.
"""

import json
import os
import shutil
import tempfile
import unittest

from AIManager import AIConfigurationError, AIManager
from app import ScreeningApp
from DataManager import DataManager, ReviewService, SqliteRecordRepository
from IOManager import IOManager, ResumeFolder
from LogicManager import JobRequirements, LogicManager
from Models import Outcome
from tests.helpers import (FakeAIClient, REQUIREMENTS, SAMPLE_BORDERLINE, SAMPLE_NON_IT,
                           SAMPLE_STRONG, make_record)
from tests.test_io_manager import ScriptedIO


class AppTestCase(unittest.TestCase):
    def build(self, answers, ai_replies=None, requirements=REQUIREMENTS, repo_factory=None, pdfs=()):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        resumes = os.path.join(self.root, "resumes")
        os.mkdir(resumes)
        for name in pdfs:
            with open(os.path.join(resumes, name), "wb") as f:
                f.write(b"%PDF-1.4 fake")
        self.script = ScriptedIO(answers)
        self.client = FakeAIClient(ai_replies or [])
        db_path = os.path.join(self.root, "data", "records.db")
        self.repo_factory = repo_factory or (lambda: SqliteRecordRepository(db_path))
        self.repo = self.repo_factory()
        self.addCleanup(lambda: self.repo.close())
        self.data = DataManager(self.repo)   # used to seed records BEFORE the app runs
        self.resumes_dir = resumes
        self.scanned_dir = os.path.join(self.root, "scanned")
        return ScreeningApp(
            io=self.script.manager(),
            ai=AIManager(self.client, sleep=lambda s: None),
            logic=LogicManager(requirements=requirements),
            data=self.data,
            review=ReviewService(self.data),
            folder=ResumeFolder(resumes, self.scanned_dir),
        )

    def after(self):
        #A fresh DataManager on the same storage> the app closes its own connection when it exits
        manager = DataManager(self.repo_factory())
        self.addCleanup(manager.close)
        return manager

    @staticmethod
    def reply(*samples):
        return json.dumps(list(samples))

    PDFS = ("arthur_goatson.pdf", "priya_sharma.pdf", "nurse.pdf")


class ScanTests(AppTestCase):
    def test_scan_grades_saves_archives_and_prints_the_table(self):
        app = self.build(["1", "6"], [self.reply(SAMPLE_STRONG, SAMPLE_BORDERLINE, SAMPLE_NON_IT)], pdfs=self.PDFS)
        app.run()
        text = self.script.text
        self.assertIn("Scanning 3 resume(s)", text)
        self.assertIn("Processed 3 resume(s)", text)
        self.assertIn("Arthur Goatson", text)
        self.assertIn("10.0/10", text)
        self.assertIn("7.5/10", text)
        self.assertIn("Goodbye!", text)
        self.assertEqual(sorted(os.listdir(self.scanned_dir)), sorted(self.PDFS))
        self.assertEqual(os.listdir(self.resumes_dir), [])
        records = self.after().load_records()
        self.assertEqual([r.outcome for r in records], [Outcome.ACCEPTED, Outcome.FLAGGED, Outcome.REJECTED])
        self.assertEqual([r.id for r in records], [1, 2, 3])

    def test_the_prompt_sent_to_the_ai_never_contains_the_job_requirements(self):
        app = self.build(["1", "6"], [self.reply(SAMPLE_STRONG)], pdfs=self.PDFS[:1])
        app.run()
        prompt, paths = self.client.calls[0]
        self.assertNotIn("kubernetes", prompt)
        self.assertEqual([os.path.basename(p) for p in paths], ["arthur_goatson.pdf"])

    def test_records_from_a_second_scan_continue_the_ids(self):
        app = self.build(["1", "6"], [self.reply(SAMPLE_STRONG)], pdfs=self.PDFS[:1])
        self.data.save_records([make_record("Earlier run")])
        app.run()
        self.assertEqual([r.id for r in self.after().load_records()], [1, 2])

    def test_missing_resume_folder(self):
        app = self.build(["1", "6"])
        shutil.rmtree(self.resumes_dir)
        app.run()
        self.assertIn("does not exist", self.script.text)
        self.assertEqual(self.client.calls, [])

    def test_no_resumes_to_scan(self):
        self.build(["1", "6"]).run()
        self.assertIn("No resumes found", self.script.text)
        self.assertEqual(self.client.calls, [])

    def test_ai_failure_saves_nothing_and_leaves_the_resumes(self):
        app = self.build(["1", "6"], [ConnectionError("down")] * 5, pdfs=self.PDFS[:1])
        app.run()
        self.assertIn("AI Manager returned no usable records", self.script.text)
        self.assertEqual(self.after().load_records(), [])
        self.assertEqual(os.listdir(self.resumes_dir), ["arthur_goatson.pdf"])

    def test_missing_api_key_is_reported_and_the_app_keeps_running(self):
        app = self.build(["1", "2", "6"], [AIConfigurationError("GEMINI_API_KEY is not set.")], pdfs=self.PDFS[:1])
        app.run()
        self.assertIn("GEMINI_API_KEY is not set.", self.script.text)
        self.assertIn("No records to display", self.script.text)   # View Summary still works
        self.assertIn("Goodbye!", self.script.text)

    def test_invalid_ai_records_are_dropped_and_their_resumes_stay(self):
        bad = {"filename": "priya_sharma.pdf", "name": "Priya"}   # missing fields
        app = self.build(["1", "6"], [self.reply(SAMPLE_STRONG, bad)], pdfs=self.PDFS[:2])
        app.run()
        self.assertEqual([r.name for r in self.after().load_records()], ["Arthur Goatson"])
        self.assertEqual(os.listdir(self.resumes_dir), ["priya_sharma.pdf"])

    def test_results_are_not_archived_when_saving_fails(self):
        app = self.build(["1", "6"], [self.reply(SAMPLE_STRONG)], pdfs=self.PDFS[:1])
        self.repo.close()   # every save now fails
        app.run()
        self.assertIn("could not be saved", self.script.text)
        self.assertEqual(os.listdir(self.resumes_dir), ["arthur_goatson.pdf"])

    def test_the_outcome_rule_is_chosen_by_requirements(self):
        strict = JobRequirements(REQUIREMENTS.required_skills, min_experience=6)   # nobody has 6 years
        app = self.build(["1", "6"], [self.reply(SAMPLE_STRONG)], requirements=strict, pdfs=self.PDFS[:1])
        app.run()
        self.assertIs(self.after().load_records()[0].outcome, Outcome.FLAGGED)   # 10.0 but only 5 years


class MenuActionTests(AppTestCase):
    def seed(self):
        self.data.save_records([
            make_record("Alice", 9.0, "Accepted"),
            make_record("Bob", 6.0, "Flagged"),
            make_record("Cara", 2.0, "Rejected"),
        ])

    def test_view_summary_shows_saved_records_from_earlier_runs(self):
        app = self.build(["2", "6"])
        self.seed()
        app.run()
        for name in ("Alice", "Bob", "Cara"):
            self.assertIn(name, self.script.text)
        self.assertIn("Total Records: 3", self.script.text)

    def test_filter_records(self):
        app = self.build(["3", "flagged", "", "", "6"])
        self.seed()
        app.run()
        self.assertIn("Filtered Records — Total Records: 1", self.script.text)
        self.assertIn("Bob", self.script.text)

    def test_filter_with_no_records(self):
        self.build(["3", "6"]).run()
        self.assertIn("No records found in storage to filter", self.script.text)

    def test_review_flagged_candidate_end_to_end(self):
        app = self.build(["4", "2", "accepted", "good interview", "2", "6"])
        self.seed()
        app.run()
        stored = self.after().get_record(2)
        self.assertIs(stored.final_outcome, Outcome.ACCEPTED)
        self.assertIs(stored.outcome, Outcome.FLAGGED)
        self.assertIn("Record 02 marked Accepted", self.script.text)
        self.assertIn("Reviewed: good interview", self.script.text)

    def test_review_with_nothing_flagged(self):
        app = self.build(["4", "6"])
        self.data.save_records([make_record("Alice", 9.0, "Accepted")])
        app.run()
        self.assertIn("No Flagged records are waiting for review", self.script.text)

    def test_review_rejects_an_id_that_is_not_pending(self):
        app = self.build(["4", "1", "", "6"])   # 1 is Accepted: asked again, then blank cancels
        self.seed()
        app.run()
        self.assertIn("Record 1 is not waiting for review", self.script.text)
        self.assertFalse(self.after().get_record(2).is_reviewed)

    def test_review_reprompts_until_a_pending_id_is_entered(self):
        app = self.build(["4", "1", "3124", "2", "accepted", "", "6"])
        self.seed()
        app.run()
        self.assertIn("Record 1 is not waiting for review", self.script.text)
        self.assertIn("Record 3124 is not waiting for review", self.script.text)
        self.assertIs(self.after().get_record(2).final_outcome, Outcome.ACCEPTED)

    def test_review_can_be_cancelled(self):
        app = self.build(["4", "", "6"])
        self.seed()
        app.run()
        self.assertFalse(self.after().get_record(2).is_reviewed)

    def test_delete_record_with_confirmation(self):
        app = self.build(["5", "3", "y", "6"])
        self.seed()
        app.run()
        self.assertIn("Record 03 deleted", self.script.text)
        self.assertEqual([r.name for r in self.after().load_records()], ["Alice", "Bob"])

    def test_delete_can_be_declined(self):
        app = self.build(["5", "3", "n", "6"])
        self.seed()
        app.run()
        self.assertEqual(len(self.after().load_records()), 3)

    def test_delete_unknown_id(self):
        app = self.build(["5", "42", "", "6"])   # 42 does not exist: asked again, then blank cancels
        self.seed()
        app.run()
        self.assertIn("No record with id 42", self.script.text)
        self.assertEqual(len(self.after().load_records()), 3)

    def test_delete_reprompts_until_an_existing_id_is_entered(self):
        app = self.build(["5", "42", "223123", "3", "y", "6"])
        self.seed()
        app.run()
        self.assertIn("No record with id 42", self.script.text)
        self.assertIn("No record with id 223123", self.script.text)
        self.assertEqual([r.name for r in self.after().load_records()], ["Alice", "Bob"])

    def test_invalid_menu_input_is_re_asked(self):
        self.build(["x", "9", "6"]).run()
        self.assertEqual(self.script.text.count("Invalid choice"), 2)



class BuildTests(unittest.TestCase):
    def test_build_creates_all_four_managers_without_a_key_or_the_sdk(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        env = {"STORAGE_PATH": os.path.join(root, "x.db")}
        app = ScreeningApp.build(environ=env, env_file=os.path.join(root, "no.env"))
        self.assertIsInstance(app._io, IOManager)
        self.assertIsInstance(app._ai, AIManager)
        self.assertIsInstance(app._logic, LogicManager)
        self.assertIsInstance(app._data, DataManager)
        app._data.close()


if __name__ == "__main__":
    unittest.main()
