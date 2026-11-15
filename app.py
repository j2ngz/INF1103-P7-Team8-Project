"""
Screening application (composition root)
----------------------------------------
Connects the four managers. Run it with:  python app.py

ScreeningApp OWNS its managers (composition): it creates them in build() and they live
and die with the app. The managers do not know about each other; the pipeline

    IOManager -> AIManager -> LogicManager -> DataManager

is wired here, which keeps each manager focused on one job (SRP) and easy to replace.

Optional environment variables
  GEMINI_API_KEY    the Gemini key (or put it in the .env file)
  STORAGE_PATH      where the SQLite database lives (default: data/resume_records.db)
"""

import logging
import os

from ai_manager import AIConfigurationError, AIManager, GeminiClient, load_env_file
from data_manager import DEFAULT_SQLITE_PATH, DataManager, RepositoryError, SqliteRecordRepository
from io_manager import IOManager, ResumeFolder
from logic_manager import LogicManager
from review_service import ReviewError, ReviewService

logging.basicConfig(level=logging.INFO)



class ScreeningApp:
    def __init__(self, io, ai, logic, data, review, folder):
        self._io = io
        self._ai = ai
        self._logic = logic
        self._data = data
        self._review = review
        self._folder = folder

    @classmethod
    def build(cls, environ=None, env_file=".env"):
        #Creates every manager and connects them
        load_env_file(env_file)
        environ = os.environ if environ is None else environ
        repository = SqliteRecordRepository(environ.get("STORAGE_PATH") or DEFAULT_SQLITE_PATH)
        data = DataManager(repository)
        return cls(
            io=IOManager(),
            ai=AIManager(GeminiClient()),
            logic=LogicManager(),
            data=data,
            review=ReviewService(data),
            folder=ResumeFolder(),
        )

# main loop
    def run(self):
        handlers = {
            "1": self.scan_resumes,
            "2": self.view_summary,
            "3": self.filter_records,
            "4": self.review_flagged,
            "5": self.delete_record,
        }
        try:
            while True:
                choice = self._io.prompt_menu_choice()
                if choice == "6":
                    self._io.show("Goodbye!")
                    break
                handlers[choice]()
        finally:
            self._data.close()

# menu actions
    def scan_resumes(self):
        if not self._folder.exists():
            self._io.warn(f"Resume folder '{self._folder.resume_dir}' does not exist.")
            return
        paths = self._folder.pdf_paths()
        if not paths:
            self._io.warn(f"No resumes found in '{self._folder.resume_dir}'.")
            return

        self._io.show(f"Scanning {len(paths)} resume(s)...")
        try:
            batch = self._ai.process_resume_batch(paths)
        except AIConfigurationError as e:
            self._io.warn(str(e))
            return
        if batch.is_empty():
            self._io.warn("AI Manager returned no usable records. Nothing saved.")
            return

        graded = self._logic.evaluate_batch(batch)
        saved = self._data.save_records(graded)
        if not saved:
            self._io.warn("The results could not be saved, so the resumes were left in place.")
            return

        for filename, error in self._folder.archive(batch.filenames):
            self._io.warn(f"Could not move '{filename}' to the scanned folder: {error}")

        self._io.show(f"Processed {len(saved)} resume(s).")
        self._io.show_records(self._data.load_records())