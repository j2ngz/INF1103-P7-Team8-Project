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

"""Jun Kang's part"""
def _prompt_menu_choice():
    """Prints the menu and validates the user's choice. Re-prompts on invalid input."""
    while True:
        print("\n=== Resume Screening System ===")
        print("1. Scan Resume")
        print("2. View Summary")
        print("3. Exit")
        choice = input("Select an option (1-3): ").strip()

        if choice in ("1", "2", "3"):
            return choice
        print("[!] Invalid choice. Please enter 1, 2, or 3.")

def handle_scan_resume():
    """Placeholder - the full pipeline is wired in during integration."""
    resume_paths = _get_resume_paths()
    if not resume_paths:
        return

    print(f"Scanning {len(resume_paths)} resume(s)...")
    print("[DEBUG-TEMP] AI step not wired up yet")

def handle_view_summary():
    """Placeholder - will load saved records during integration."""
    print("[DEBUG-TEMP] view summary not wired up yet")

def run():
    """Main menu loop."""
    while True:
        choice = _prompt_menu_choice()

        if choice == "1":
            handle_scan_resume()
        elif choice == "2":
            handle_view_summary()
        elif choice == "3":
            print("Goodbye!")
            break

def _truncate(text, max_len):
    """Truncates text with an ellipsis if it's longer than max_len."""
    return text if len(text) <= max_len else text[: max_len - 1] + "…"

# [DEBUG-TEMP] test the move using a throw-away folder - remove later
if __name__ == "__main__":
    print("[DEBUG-TEMP]", _truncate("Alexandria Montgomery-Featherstonehaugh", 20))  # [DEBUG-TEMP]
    run()