from IOManager.filter_criteria import FilterCriteria
from Models.outcome import Outcome

# Handles everything the user sees and types so it will show the menu, prompts and the records table
class IOManager:
    MENU_OPTIONS = (
        ("1", "Scan Resume"),
        ("2", "View Summary"),
        ("3", "Filter Records"),
        ("4", "Review Flagged Candidates"),
        ("5", "Delete Record"),
        ("6", "Exit"),
    )

    # Table columns, and the longest a name or note can be before it is cut short
    TABLE_HEADERS = ["ID", "Name", "Score", "Outcome", "Final", "Notes"]
    MAX_NAME_WIDTH = 28
    MAX_NOTE_WIDTH = 44

    # input_fn and print_fn can be swapped for fakes in the tests
    def __init__(self, input_fn=input, print_fn=print):
        self._input = input_fn
        self._print = print_fn

    # Messages 
    def show(self, message):
        self._print(message)

    # Prints a warning with ! in front
    def warn(self, message):
        self._print(f"[!] {message}")

    # menu 
    def prompt_menu_choice(self):
        # Prints the menu and reprompts until the user picks a valid option
        valid = {key for key, _ in self.MENU_OPTIONS}           # The valid keys, 1 to 6
        last = self.MENU_OPTIONS[-1][0]                         # The last option number, used in the messages
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
        # Asks for an outcome and a score range. Each can be left blank to skip
        self._print("\n--- Filter Records ---")
        outcome = None
        # Outcome does ask again until it is Accepted, Flagged or Rejected or blank to skip

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
        # Maximum score does ask again if it is lower than the minimum

        while True:
            max_score = self.prompt_score("Enter maximum score (0-10) [Leave blank to skip]: ")
            if max_score is not None and min_score is not None and max_score < min_score:
                self.warn(f"Maximum score cannot be less than minimum score ({min_score}).")
                continue
            break
        return FilterCriteria(outcome, min_score, max_score)

    def prompt_score(self, question):
        # Asks for a score from 0 to 10, returns it as a float or nothing if user leaves blanks
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
        # Returns an int id, or none when the user cancels
        while True:
            text = self._input(question).strip()
            if not text:
                return None
            if text.isdigit():      # whole numbers only
                return int(text)
            self.warn("Please enter the numeric ID shown in the table.")

    def prompt_review_decision(self, record):
        # Shows one Flagged record and asks for a decision. Returns Outcome, note or none
        self._print(f"\nReviewing {record.display_id} - {record.name}: score {record.score}/10, "
                    f"{record.missing_skills_count} skill(s) missing, {len(record.it_certs)} IT cert(s), "
                    f"{record.it_experience_years} yr IT experience")
        while True:
            text = self._input("Decision (Accepted/Rejected) [blank to cancel]: ").strip()
            if not text:
                return None
            decision = Outcome.parse(text)
            if decision in (Outcome.ACCEPTED, Outcome.REJECTED):         # Flagged is not a valid 
                note = self._input("Note for the record (optional): ").strip()
                return decision, note
            self.warn("Please enter Accepted or Rejected.")

    # Returns True only when the user types y or yes
    def confirm(self, question):
        return self._input(f"{question} (y/n): ").strip().lower() in ("y", "yes")

    # Cuts long text and ends it with "…" so the table stays lined up
    @staticmethod
    def truncate(text, max_len):
        return text if len(text) <= max_len else text[: max_len - 1] + "…"

   # Text for the Notes column: the review note if reviewed, missing skills and IT certs if Flagged
    def note_for(self, record):
        if record.is_reviewed:
            note = record.review_note or "(no note)"
            return self.truncate(f"Reviewed: {note}", self.MAX_NOTE_WIDTH)
        if record.outcome is Outcome.FLAGGED:
            return f"{record.missing_skills_count} skill(s) missing, {len(record.it_certs)} IT cert(s)"
        return ""

    def show_records(self, records, title="Resume Screening Summary"):
        """
        Prints a boxed table: ID, Name, Score, Outcome, Final, Notes
        Outcome is the screener's result
        Final is the reviewer's decision when there is one
        Notes is filled for Flagged (missing skills / IT certs) and reviewed rows
        """
        if not records:
            self._print("\nNo records to display.\n")
            return

        headers = self.TABLE_HEADERS
         # One row of text per record
        rows = [[
            r.display_id,
            self.truncate(r.name, self.MAX_NAME_WIDTH),
            f"{r.score}/10",
            r.outcome.value,
            r.final_outcome.value,
            self.note_for(r),
        ] for r in records]

        # Each column is as wide as its longest value or its header
        widths = [max(len(headers[i]), max(len(row[i]) for row in rows)) for i in range(len(headers))]

        # Pads each value to its column width and joins them with |
        def format_row(cols):
            return "| " + " | ".join(f"{c:<{widths[i]}}" for i, c in enumerate(cols)) + " |"

        separator = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
        total_width = len(separator)
        # Title, header row, then one line per record
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
