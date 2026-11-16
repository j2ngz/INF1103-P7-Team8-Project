import os
import shutil
import tempfile
import unittest

from IOManager import FilterCriteria, IOManager, ResumeFolder
from Models import Outcome
from tests.helpers import make_record


class ScriptedIO:
    #Feeds scripted answers to IOManager and records everything it prints

    def __init__(self, answers):
        self._answers = list(answers)
        self.prompts = []
        self.lines = []

    def input(self, prompt=""):
        self.prompts.append(prompt)
        return self._answers.pop(0)

    def print(self, text=""):
        self.lines.append(str(text))

    @property
    def text(self):
        return "\n".join(self.lines)

    def manager(self):
        return IOManager(input_fn=self.input, print_fn=self.print)


class MenuTests(unittest.TestCase):
    def test_valid_choice_is_returned(self):
        script = ScriptedIO(["3"])
        self.assertEqual(script.manager().prompt_menu_choice(), "3")
        self.assertIn("3. Filter Records", script.text)
        self.assertIn("6. Exit", script.text)

    def test_invalid_choices_reprompt(self):
        script = ScriptedIO(["", "0", "8", "abc", " 2 "])
        self.assertEqual(script.manager().prompt_menu_choice(), "2")
        self.assertEqual(script.text.count("Invalid choice"), 4)


class FilterPromptTests(unittest.TestCase):
    def test_all_blank_skips_every_filter(self):
        crit = ScriptedIO(["", "", ""]).manager().prompt_filter_criteria()
        self.assertEqual(crit, FilterCriteria(None, None, None))

    def test_full_criteria(self):
        crit = ScriptedIO(["flagged", "4", "8.5"]).manager().prompt_filter_criteria()
        self.assertEqual(crit, FilterCriteria(Outcome.FLAGGED, 4.0, 8.5))

    def test_invalid_values_reprompt(self):
        script = ScriptedIO(["maybe", "Accepted", "abc", "11", "-1", "5", "3", "9"])
        crit = script.manager().prompt_filter_criteria()
        self.assertEqual(crit, FilterCriteria(Outcome.ACCEPTED, 5.0, 9.0))
        self.assertIn("Invalid outcome", script.text)
        self.assertIn("Invalid number", script.text)
        self.assertIn("between 0 and 10", script.text)
        self.assertIn("cannot be less than minimum", script.text)


class OtherPromptTests(unittest.TestCase):
    def test_record_id_prompt(self):
        script = ScriptedIO(["x", "-3", "12"])
        self.assertEqual(script.manager().prompt_record_id(), 12)
        self.assertEqual(script.text.count("numeric ID"), 2)

    def test_record_id_blank_cancels(self):
        self.assertIsNone(ScriptedIO([""]).manager().prompt_record_id())

    def test_review_decision(self):
        script = ScriptedIO(["flagged", "accepted", "solid referees"])
        record = make_record("Pat")
        record.assign_id(2)
        self.assertEqual(script.manager().prompt_review_decision(record), (Outcome.ACCEPTED, "solid referees"))
        self.assertIn("Reviewing 02 - Pat", script.text)

    def test_review_decision_can_be_cancelled(self):
        self.assertIsNone(ScriptedIO([""]).manager().prompt_review_decision(make_record()))

    def test_confirm(self):
        self.assertTrue(ScriptedIO(["Y"]).manager().confirm("Sure?"))
        self.assertTrue(ScriptedIO(["yes"]).manager().confirm("Sure?"))
        self.assertFalse(ScriptedIO(["n"]).manager().confirm("Sure?"))
        self.assertFalse(ScriptedIO([""]).manager().confirm("Sure?"))


class TableTests(unittest.TestCase):
    def render(self, records):
        script = ScriptedIO([])
        script.manager().show_records(records)
        return script.text

    def test_empty_table(self):
        self.assertIn("No records to display", self.render([]))

    def test_columns_and_rows(self):
        accepted = make_record("Arthur Goatson", 10.0, "Accepted")
        accepted.assign_id(3)
        text = self.render([accepted])
        self.assertIn("| ID | Name", text)
        for header in ("Score", "Outcome", "Final", "Notes"):
            self.assertIn(header, text)
        self.assertIn("| 03 | Arthur Goatson | 10.0/10 | Accepted | Accepted |", text)
        self.assertIn("Total Records: 1", text)

    def test_notes_only_for_flagged_rows(self):
        flagged = make_record("Samantha", 6.3, "Flagged", it_certs=["a", "b"], missing=8)
        flagged.assign_id(5)
        rejected = make_record("Low", 1.0, "Rejected")
        rejected.assign_id(6)
        text = self.render([flagged, rejected])
        self.assertIn("8 skill(s) missing, 2 IT cert(s)", text)
        self.assertEqual(text.count("skill(s) missing"), 1)

    def test_reviewed_rows_show_the_final_decision_and_note(self):
        record = make_record("Pat", 6.0, "Flagged")
        record.assign_id(1)
        record.apply_review("Accepted", "strong referees", "t")
        text = self.render([record])
        self.assertIn("| Flagged | Accepted | Reviewed: strong referees", text)

    def test_long_names_are_truncated(self):
        record = make_record("N" * 60)
        record.assign_id(1)
        self.assertIn("…", self.render([record]))

    def test_rows_have_equal_width(self):
        records = [make_record("Short", 1.0, "Rejected"), make_record("A much longer name here", 6.0, "Flagged")]
        for i, r in enumerate(records, 1):
            r.assign_id(i)
        rows = [l for l in self.render(records).splitlines() if l.startswith("|")]
        self.assertEqual(len({len(r) for r in rows}), 1)


class ResumeFolderTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.resumes = os.path.join(self.root, "resumes")
        self.scanned = os.path.join(self.root, "scanned")
        os.mkdir(self.resumes)
        for name in ("b.pdf", "A.PDF", "notes.txt", "c.docx"):
            with open(os.path.join(self.resumes, name), "wb") as f:
                f.write(b"%PDF-")
        self.folder = ResumeFolder(self.resumes, self.scanned)

    def test_lists_only_pdfs_sorted(self):
        names = [os.path.basename(p) for p in self.folder.pdf_paths()]
        self.assertEqual(names, ["A.PDF", "b.pdf"])

    def test_missing_folder(self):
        folder = ResumeFolder(os.path.join(self.root, "nope"), self.scanned)
        self.assertFalse(folder.exists())
        self.assertEqual(folder.pdf_paths(), [])

    def test_archive_moves_files_and_creates_the_folder(self):
        self.assertEqual(self.folder.archive(["b.pdf"]), [])
        self.assertTrue(os.path.exists(os.path.join(self.scanned, "b.pdf")))
        self.assertFalse(os.path.exists(os.path.join(self.resumes, "b.pdf")))

    def test_archive_reports_failures_and_continues(self):
        failures = self.folder.archive(["ghost.pdf", "b.pdf"])
        self.assertEqual([name for name, _ in failures], ["ghost.pdf"])
        self.assertTrue(os.path.exists(os.path.join(self.scanned, "b.pdf")))

    def test_archive_ignores_path_tricks_in_ai_supplied_names(self):
        outside = os.path.join(self.root, "outside.pdf")
        with open(outside, "wb") as f:
            f.write(b"x")
        failures = self.folder.archive(["../outside.pdf"])
        self.assertEqual(len(failures), 1)
        self.assertTrue(os.path.exists(outside))   # the file outside the folder was not touched


if __name__ == "__main__":
    unittest.main()
