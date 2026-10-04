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

# [DEBUG-TEMP] test the move using a throw-away folder - remove later
if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        src_dir = os.path.join(tmp, "resumes")
        dst_dir = os.path.join(tmp, "scanned")
        os.makedirs(src_dir)
        open(os.path.join(src_dir, "test.pdf"), "w").close()
        print("[DEBUG-TEMP] before:", os.listdir(src_dir))
        _move_scanned_resumes(src_dir, ["test.pdf"], dst_dir)
        print("[DEBUG-TEMP] after: resumes =", os.listdir(src_dir), "scanned =", os.listdir(dst_dir))