import os
import shutil
from collections import namedtuple

from models import Outcome

FilterCriteria = namedtuple("FilterCriteria", ["outcome", "min_score", "max_score"])


class IOManager:
    MENU_OPTIONS = (
        ("1", "Scan Resume"),
        ("2", "View Summary"),
        ("3", "Filter Records"),
        ("4", "Review Flagged Candidates"),
        ("5", "Delete Record"),
        ("6", "Exit"),
    )
    TABLE_HEADERS = ["ID", "Name", "Score", "Outcome", "Final", "Notes"]
    MAX_NAME_WIDTH = 28
    MAX_NOTE_WIDTH = 44

    def __init__(self, input_fn=input, print_fn=print):
        self._input = input_fn
        self._print = print_fn

    # messages 
    def show(self, message):
        self._print(message)

    def warn(self, message):
        self._print(f"[!] {message}")

    def prompt_menu_choice(self):
        #Prints the menu and reprompts until the user picks a valid option
        valid = {key for key, _ in self.MENU_OPTIONS}
        last = self.MENU_OPTIONS[-1][0]
        while True:
            self._print("\n=== Resume Screening System ===")
            for key, label in self.MENU_OPTIONS:
                self._print(f"{key}. {label}")
            choice = self._input(f"Select an option (1-{last}): ").strip()
            if choice in valid:
                return choice
            self.warn(f"Invalid choice. Please enter a number from 1 to {last}.")

    # prompts 
    def prompt_filter_criteria(self):
        #Asks for an outcome and a score range. Each can be left blank to skip
        self._print("\n--- Filter Records ---")
        outcome = None
        while True:
            text = self._input("Filter by outcome (Accepted/Flagged/Rejected) [Leave blank to skip]: ").strip()
            if not text:
                break
            outcome = Outcome.parse(text)
            if outcome is not None:
                break
            self.warn("Invalid outcome. Please enter Accepted, Flagged, or Rejected (or leave blank).")

        min_score = self.prompt_score("Enter minimum score (0-10) [Leave blank to skip]: ")
        max_score = None
        while True:
            max_score = self.prompt_score("Enter maximum score (0-10) [Leave blank to skip]: ")
            if max_score is not None and min_score is not None and max_score < min_score:
                self.warn(f"Maximum score cannot be less than minimum score ({min_score}).")
                continue
            break
        return FilterCriteria(outcome, min_score, max_score)

    def prompt_score(self, question):
        while True:
            text = self._input(question).strip()
            if not text:
                return None
            try:
                value = float(text)
            except ValueError:
                self.warn("Invalid number. Please enter a valid numeric score (e.g., 7.5).")
                continue
            if 0 <= value <= 10:
                return value
            self.warn("Score must be between 0 and 10.")

    def prompt_record_id(self, question="Enter the record ID (blank to cancel): "):
        #Returns an int id, or None when the user cancels
        while True:
            text = self._input(question).strip()
            if not text:
                return None
            if text.isdigit():
                return int(text)
            self.warn("Please enter the numeric ID shown in the table.")

    def prompt_review_decision(self, record):
        #Shows one Flagged record and asks for a decision. Returns (Outcome, Note) or none
        self._print(f"\nReviewing {record.display_id} - {record.name}: score {record.score}/10, "
                    f"{record.missing_skills_count} skill(s) missing, {len(record.it_certs)} IT cert(s), "
                    f"{record.it_experience_years} yr IT experience")
        while True:
            text = self._input("Decision (Accepted/Rejected) [blank to cancel]: ").strip()
            if not text:
                return None
            decision = Outcome.parse(text)
            if decision in (Outcome.ACCEPTED, Outcome.REJECTED):
                note = self._input("Note for the record (optional): ").strip()
                return decision, note
            self.warn("Please enter Accepted or Rejected.")

    def confirm(self, question):
        return self._input(f"{question} (y/n): ").strip().lower() in ("y", "yes")

    @staticmethod
    def truncate(text, max_len):
        return text if len(text) <= max_len else text[: max_len - 1] + "…"

    def note_for(self, record):
        if record.is_reviewed:
            note = record.review_note or "(no note)"
            return self.truncate(f"Reviewed: {note}", self.MAX_NOTE_WIDTH)
        if record.outcome is Outcome.FLAGGED:
            return f"{record.missing_skills_count} skill(s) missing, {len(record.it_certs)} IT cert(s)"
        return ""

    def show_records(self, records, title="Resume Screening Summary"):
        #Prints a boxed table: ID, Name, Score, Outcome, Final, Notes
        if not records:
            self._print("\nNo records to display.\n")
            return

        headers = self.TABLE_HEADERS
        rows = [[
            r.display_id,
            self.truncate(r.name, self.MAX_NAME_WIDTH),
            f"{r.score}/10",
            r.outcome.value,
            r.final_outcome.value,
            self.note_for(r),
        ] for r in records]

        widths = [max(len(headers[i]), max(len(row[i]) for row in rows)) for i in range(len(headers))]

        def format_row(cols):
            return "| " + " | ".join(f"{c:<{widths[i]}}" for i, c in enumerate(cols)) + " |"

        separator = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
        total_width = len(separator)
        self._print()
        self._print("=" * total_width)
        self._print(f" {title} — Total Records: {len(records)}")
        self._print("=" * total_width)
        self._print(format_row(headers))
        self._print(separator)
        for row in rows:
            self._print(format_row(row))
        self._print("=" * total_width)
        self._print()


class ResumeFolder:
#Folder of resume PDFs waiting to be scanned and archive for scanned ones

    SUPPORTED_EXTENSIONS = (".pdf",)

    def __init__(self, resume_dir="./resumes", scanned_dir="./scannedResume"):
        self._resume_dir = resume_dir
        self._scanned_dir = scanned_dir

    @property
    def resume_dir(self):
        return self._resume_dir

    def exists(self):
        return os.path.isdir(self._resume_dir)

    def pdf_paths(self):
        #Paths of every supported resume file sorted by name and empty if folder is missing
        if not self.exists():
            return []
        return [
            os.path.join(self._resume_dir, name)
            for name in sorted(os.listdir(self._resume_dir))
            if name.lower().endswith(self.SUPPORTED_EXTENSIONS)
        ]

    def archive(self, filenames):
        # Moves each file into the scanned folder 
        # File that cannot be moved is skipped and returns a list of filename, error message for the failures

        failures = []
        os.makedirs(self._scanned_dir, exist_ok=True)
        for name in filenames:
            name = os.path.basename(name)
            try:
                shutil.move(os.path.join(self._resume_dir, name), os.path.join(self._scanned_dir, name))
            except Exception as e:
                failures.append((name, str(e)))
        return failures