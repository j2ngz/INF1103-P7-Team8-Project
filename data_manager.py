import copy
import json
import logging
import os
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime

from models import Outcome, ResumeRecord

logger = logging.getLogger("DataManager")

DEFAULT_SQLITE_PATH = os.path.join("data", "resume_records.db")


class RepositoryError(Exception):
    pass

# Defining the contract
class RecordRepository(ABC):

    @abstractmethod
    def add(self, record):
        pass

    @abstractmethod
    def add_many(self, records):
        pass

    @abstractmethod
    def get(self, record_id):
        pass

    @abstractmethod
    def list_all(self):
        pass

    @abstractmethod
    def update(self, record):
        pass

    @abstractmethod
    def delete(self, record_id):
        pass

    @abstractmethod
    def query(self, outcome=None, min_score=None, max_score=None):
        pass

    def close(self):
        pass