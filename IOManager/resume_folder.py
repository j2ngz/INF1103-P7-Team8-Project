import os
import shutil


# The folder of resume PDFs waiting to be scanned, and the archive folder for scanned ones
class ResumeFolder:
    # Only PDF files are picked up
    SUPPORTED_EXTENSIONS = (".pdf",)

    # By default: resumes/ to scan, scannedResume/ for the archive
    def __init__(self, resume_dir="./resumes", scanned_dir="./scannedResume"):
        self._resume_dir = resume_dir
        self._scanned_dir = scanned_dir

    # Read-only access to the resume folder path
    @property
    def resume_dir(self):
        return self._resume_dir

    # True if the resume folder exists
    def exists(self):
        return os.path.isdir(self._resume_dir)

    def pdf_paths(self):
        # Paths of every PDF in the folder, sorted by name and empty if the folder is missing
        if not self.exists():
            return []
        return [
            os.path.join(self._resume_dir, name)
            for name in sorted(os.listdir(self._resume_dir))
            if name.lower().endswith(self.SUPPORTED_EXTENSIONS)
        ]

    def archive(self, filenames):
        # Moves each file into the scanned folder (created if needed)
        # A file that cannot be moved is skipped and returns (filename, error message) for each one that failed
        failures = []
        os.makedirs(self._scanned_dir, exist_ok=True)
        for name in filenames:
            name = os.path.basename(name)   # filename comes from the AI's reply, keep only the file name so it can't point outside resumes/
            try:
                shutil.move(os.path.join(self._resume_dir, name), os.path.join(self._scanned_dir, name))
            except Exception as e:   # e.g. the file is open in another program
                failures.append((name, str(e)))
        return failures
