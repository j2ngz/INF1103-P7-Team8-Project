"""
I/O Manager
-----------
All boundaries between system and user.

Responsibilities:
  - Collect structured input from the user via the terminal
  - Collect / print summary views
  - Validate user input - reject and re-prompt on bad data
  - All print() calls in the system live here and nowhere else
  - Format individual records and lists
"""
import os
import shutil

import ai_manager
import logic_manager
import data_manager

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



def _prompt_menu_choice():
    """Prints the menu and validates the user's choice. Re-prompts on invalid input."""
    while True:
        print("\n=== Resume Screening System ===")
        print("1. Scan Resume")
        print("2. View Summary")
        print("3. Filter Records")
        print("4. Exit")
        choice = input("Select an option (1-4): ").strip()

        if choice in ("1", "2", "3", "4"):
            return choice
        print("[!] Invalid choice. Please enter 1, 2, 3, or 4.")


def handle_scan_resume():
    """Full pipeline: I/O Manager -> AI Manager -> Logic Manager -> Data Manager."""
    resume_paths = _get_resume_paths()
    if not resume_paths:
        return

    print(f"Scanning {len(resume_paths)} resume(s)...")
    ai_records = ai_manager.process_resume_batch(resume_paths)

    if not ai_records:
        print("[!] AI Manager returned no usable records. Nothing saved.")
        return

    scanned_filenames = [r["filename"] for r in ai_records if r.get("filename")]
    _move_scanned_resumes(RESUME_FOLDER, scanned_filenames)

    graded_records = logic_manager.evaluate_batch(ai_records)
    data_manager.save_records(graded_records)

    print(f"Processed {len(graded_records)} resume(s).")
    _print_table(data_manager.load_records())


def handle_view_summary():
    """Loads all saved records (across all runs) and prints them."""
    records = data_manager.load_records()
    _print_table(records)

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

def run():
    """Main menu loop."""
    while True:
        choice = _prompt_menu_choice()

        if choice == "1":
            handle_scan_resume()
        elif choice == "2":
            handle_view_summary()
        elif choice == "3":
            handle_filter_records()
        elif choice == "4":
            print("Goodbye!")
            break


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


if __name__ == "__main__":
    run()