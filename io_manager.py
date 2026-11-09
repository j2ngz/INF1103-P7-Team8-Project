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

    def confirm(self, question):
        return self._input(f"{question} (y/n): ").strip().lower() in ("y", "yes")


RESUME_FOLDER = "./resumes"
SCANNED_FOLDER = "./scannedResume"
SUPPORTED_EXTENSIONS = (".pdf",)


def _get_resume_paths(folder=RESUME_FOLDER):
    """Finds all supported resume files in the hardcoded folder."""
    if not os.path.isdir(folder):
        print(f"[!] Resume folder '{folder}' does not exist.")
        return []

    paths = [
        os.path.join(folder, f)
        for f in sorted(os.listdir(folder))
        if f.lower().endswith(SUPPORTED_EXTENSIONS)
    ]
    if not paths:
        print(f"[!] No resumes found in '{folder}'.")
    return paths


def _move_scanned_resumes(resume_folder, scanned_filenames, scanned_folder=SCANNED_FOLDER):
    """
    Moves each successfully processed resume (by filename) out of the resume
    folder and into scanned_folder, creating scanned_folder if it doesn't exist.
    Resumes that failed AI validation are left in place.
    """
    os.makedirs(scanned_folder, exist_ok=True)
    for filename in scanned_filenames:
        src = os.path.join(resume_folder, filename)
        dst = os.path.join(scanned_folder, filename)
        try:
            shutil.move(src, dst)
        except Exception as e:
            print(f"[!] Could not move '{filename}' to '{scanned_folder}': {e}")





def _truncate(text, max_len):
    """Truncates text with an ellipsis if it's longer than max_len."""
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _print_table(records):
    """
    Formats and prints a clean, boxed summary table: ID, Name, Score, Outcome,
    Notes - all in one row per candidate. Notes is only populated for Flagged
    resumes (missing skill count + IT cert count); blank for Accepted/Rejected.
    """
    if not records:
        print("\nNo records to display.\n")
        return

    headers = ["ID", "Name", "Score", "Outcome", "Notes"]
    max_name_w = 28

    rows = []
    for r in records:
        rid = str(r.get("id", ""))
        name = _truncate(str(r.get("name", "")), max_name_w)
        score = f"{r.get('score', 0)}/10"
        outcome = str(r.get("outcome", ""))
        if outcome == "Flagged":
            missing_count = r.get("missing_skills_count", 0)
            certs_count = len(r.get("it_certs", []))
            notes = f"{missing_count} skill(s) missing, {certs_count} IT cert(s)"
        else:
            notes = ""
        rows.append([rid, name, score, outcome, notes])

    # Column widths: fit the header and the widest value in that column.
    widths = [
        max(len(headers[i]), max((len(row[i]) for row in rows), default=0))
        for i in range(len(headers))
    ]

    def format_row(cols):
        return "| " + " | ".join(f"{c:<{widths[i]}}" for i, c in enumerate(cols)) + " |"

    separator = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    total_w = len(separator)

    print()
    print("=" * total_w)
    print(f" Resume Screening Summary — Total Records: {len(records)}")
    print("=" * total_w)
    print(format_row(headers))
    print(separator)
    for row in rows:
        print(format_row(row))

    print("=" * total_w)
    print()
