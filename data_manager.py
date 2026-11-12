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


class SqliteRecordRepository(RecordRepository):

    SCHEMA = """
        CREATE TABLE IF NOT EXISTS records (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            name                 TEXT    NOT NULL,
            skills               TEXT    NOT NULL,
            it_experience_years  REAL    NOT NULL,
            certificates         TEXT    NOT NULL,
            it_certs             TEXT    NOT NULL,
            missing_skills_count INTEGER NOT NULL,
            score                REAL    NOT NULL,
            outcome              TEXT    NOT NULL,
            timestamp            TEXT    NOT NULL,
            review_decision      TEXT,
            review_note          TEXT    NOT NULL DEFAULT '',
            reviewed_at          TEXT
        )"""

    def __init__(self, path=DEFAULT_SQLITE_PATH):
        self._path = path
        self.__connection = self.open()

    # connection handling
    def open(self):
        if self._path != ":memory:":
            folder = os.path.dirname(self._path)
            try:
                if folder:
                    os.makedirs(folder, exist_ok=True)
            except OSError as e:
                raise RepositoryError(f"Could not create folder {folder}: {e}") from e
            
        try:
            return self.connect_and_prepare()
        
        except sqlite3.DatabaseError as e:

            if self._path == ":memory:":
                raise RepositoryError(f"Database error: {e}") from e
            
            moved = f"{self._path}.corrupt-{datetime.now():%Y%m%d%H%M%S}"
            logger.error(f"{self._path} is not a usable database ({e}). Moving it to {moved} and starting fresh.")
            
            try:
                os.replace(self._path, moved)
                return self.connect_and_prepare()
            except (OSError, sqlite3.Error) as e2:
                raise RepositoryError(f"Could not recover database {self._path}: {e2}") from e2

    def connect_and_prepare(self):
        
        connection = sqlite3.connect(self._path)
        
        try:
            connection.row_factory = sqlite3.Row
            connection.execute(self.SCHEMA)
            connection.commit()
        except sqlite3.Error:
            connection.close()
            raise
        return connection

    def close(self):
        if self.__connection is not None:
            self.__connection.close()
            self.__connection = None

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def _conn(self):
        
        if self.__connection is None:
            raise RepositoryError("The database connection is closed")
        return self.__connection

    @staticmethod
    def values(record):
        return (
            record.name, json.dumps(record.skills), record.it_experience_years,
            json.dumps(record.certificates), json.dumps(record.it_certs),
            record.missing_skills_count, record.score, record.outcome.value, record.timestamp,
            record.review_decision.value if record.review_decision else None,
            record.review_note, record.reviewed_at,
        )

    @staticmethod
    def to_record(row):
        return ResumeRecord(
            record_id=row["id"], name=row["name"], skills=json.loads(row["skills"]),
            it_experience_years=row["it_experience_years"],
            certificates=json.loads(row["certificates"]), it_certs=json.loads(row["it_certs"]),
            missing_skills_count=row["missing_skills_count"], score=row["score"],
            outcome=row["outcome"], timestamp=row["timestamp"],
            review_decision=row["review_decision"], review_note=row["review_note"] or "",
            reviewed_at=row["reviewed_at"],
        )

    def rows_to_records(self, rows):
        records = []
        for row in rows:
            try:
                records.append(self.to_record(row))
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"Skipping corrupt database row id={row['id']}: {e}")
        return records

    def run(self, action):
        # runs a database action and turns sqlite errors into RepositoryError
        try:
            return action(self._conn())
        except sqlite3.Error as e:
            raise RepositoryError(f"Database error: {e}") from e

    # RecordRepository

    _INSERT = ("INSERT INTO records (name, skills, it_experience_years, certificates, it_certs, "
               "missing_skills_count, score, outcome, timestamp, review_decision, review_note, reviewed_at) "
               "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)")

    def add(self, record):
        return self.add_many([record])[0]

    def add_many(self, records):
        def action(conn):
            ids = []
            with conn:  
                for record in records:
                    cursor = conn.execute(self._INSERT, self.values(record))
                    ids.append(cursor.lastrowid)
            return ids
        ids = self.run(action)
        for record, new_id in zip(records, ids):
            record.assign_id(new_id)
        return ids

    def get(self, record_id):
        rows = self.run(lambda c: c.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchall())
        records = self.rows_to_records(rows)
        return records[0] if records else None

    def list_all(self):
        return self.rows_to_records(self.run(lambda c: c.execute("SELECT * FROM records ORDER BY id").fetchall()))

    def update(self, record):
        def action(conn):
            with conn:
                cursor = conn.execute(
                    "UPDATE records SET name=?, skills=?, it_experience_years=?, certificates=?, it_certs=?, "
                    "missing_skills_count=?, score=?, outcome=?, timestamp=?, review_decision=?, "
                    "review_note=?, reviewed_at=? WHERE id=?",
                    self.values(record) + (record.id,))
            return cursor.rowcount > 0
        return self.run(action)

    def delete(self, record_id):
        def action(conn):
            with conn:
                cursor = conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
            return cursor.rowcount > 0
        return self.run(action)

    def query(self, outcome=None, min_score=None, max_score=None):
        sql, params = "SELECT * FROM records WHERE 1=1", []
        if outcome is not None:
            wanted = Outcome.parse(outcome)
            if wanted is None:
                return []
            sql += " AND outcome = ?"
            params.append(wanted.value)
        if min_score is not None:
            sql += " AND score >= ?"
            params.append(min_score)
        if max_score is not None:
            sql += " AND score <= ?"
            params.append(max_score)
        sql += " ORDER BY id"
        return self.rows_to_records(self.run(lambda c: c.execute(sql, params).fetchall()))

class InMemoryRecordRepository(RecordRepository):
    # keeps records in a Python dict (used for tests)

    def __init__(self):
        self._records = {}     
        self._next_id = 1

    def add(self, record):
        return self.add_many([record])[0]

    def add_many(self, records):
        ids = []
        for record in records:
            record.assign_id(self._next_id)
            self._records[self._next_id] = copy.deepcopy(record)   # store a copy, like a database would
            ids.append(self._next_id)
            self._next_id += 1
        return ids

    def get(self, record_id):
        record = self._records.get(record_id)
        return copy.deepcopy(record) if record else None

    def list_all(self):
        return [copy.deepcopy(r) for _, r in sorted(self._records.items())]

    def update(self, record):
        if record.id not in self._records:
            return False
        self._records[record.id] = copy.deepcopy(record)
        return True

    def delete(self, record_id):
        return self._records.pop(record_id, None) is not None