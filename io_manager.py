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


def handle_filter_records():
    """Prompts user for filtering options, filters saved records, and prints the result table."""
    records = data_manager.load_records()
    if not records:
        print("\n[!] No records found in storage to filter.")
        return

    print("\n--- Filter Records ---")
    
    outcome = None
    valid_outcomes = {"accepted", "flagged", "rejected"}
    while True:
        outcome_input = input("Filter by outcome (Accepted/Flagged/Rejected) [Leave blank to skip]: ").strip().lower()
        if not outcome_input:
            break
        if outcome_input in valid_outcomes:
            # Capitalize nicely for display/matching
            outcome = outcome_input.capitalize()
            break
        print("[!] Invalid outcome. Please enter Accepted, Flagged, or Rejected (or leave blank).")

    min_score = None
    while True:
        min_score_input = input("Enter minimum score (0-10) [Leave blank to skip]: ").strip()
        if not min_score_input:
            break
        try:
            min_score = float(min_score_input)
            if 0 <= min_score <= 10:
                break
            print("[!] Score must be between 0 and 10.")
        except ValueError:
            print("[!] Invalid number. Please enter a valid numeric score (e.g., 7.5).")

    max_score = None
    while True:
        max_score_input = input("Enter maximum score (0-10) [Leave blank to skip]: ").strip()
        if not max_score_input:
            break
        try:
            max_score = float(max_score_input)
            if 0 <= max_score <= 10:
                if min_score is not None and max_score < min_score:
                    print(f"[!] Maximum score cannot be less than minimum score ({min_score}).")
                    continue
                break
            print("[!] Score must be between 0 and 10.")
        except ValueError:
            print("[!] Invalid number. Please enter a valid numeric score (e.g., 9.0).")

    filtered = data_manager.filter_records(
        records, 
        outcome=outcome, 
        min_score=min_score, 
        max_score=max_score
    )
    
    _print_table(filtered)


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
