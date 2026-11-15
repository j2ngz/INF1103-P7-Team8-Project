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