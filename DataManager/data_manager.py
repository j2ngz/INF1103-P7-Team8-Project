import logging

from DataManager.repository_error import RepositoryError

logger = logging.getLogger("DataManager")

# Define the contract
class DataManager:

    def __init__(self, repository):
        self._repository = repository

    @property
    def repository(self):
        return self._repository

    def close(self):
        self._repository.close()

    def save_records(self, records):
        records = list(records)
        if not records:
            return []
        try:
            self._repository.add_many(records)
        except RepositoryError as e:
            logger.error(f"Failed to save records: {e}")
            return []
        return records

    def load_records(self):
        try:
            return self._repository.list_all()
        except RepositoryError as e:
            logger.error(f"Failed to load records: {e}")
            return []

    def filter_records(self, outcome=None, min_score=None, max_score=None):
        try:
            return self._repository.query(outcome, min_score, max_score)
        except RepositoryError as e:
            logger.error(f"Failed to query records: {e}")
            return []

    def get_record(self, record_id):
        try:
            return self._repository.get(record_id)
        except RepositoryError as e:
            logger.error(f"Failed to read record {record_id}: {e}")
            return None

    def update_record(self, record):
        try:
            return self._repository.update(record)
        except RepositoryError as e:
            logger.error(f"Failed to update record {record.id}: {e}")
            return False

    def delete_record(self, record_id):
        try:
            return self._repository.delete(record_id)
        except RepositoryError as e:
            logger.error(f"Failed to delete record {record_id}: {e}")
            return False
