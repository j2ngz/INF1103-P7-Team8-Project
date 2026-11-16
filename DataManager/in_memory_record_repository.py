import copy

from DataManager.record_repository import RecordRepository
from Models.outcome import Outcome


class InMemoryRecordRepository(RecordRepository):

    def __init__(self):
        self._records = {}     
        self._next_id = 1

    def add(self, record):
        return self.add_many([record])[0]

    def add_many(self, records):
        ids = []
        for record in records:
            record.assign_id(self._next_id)
            self._records[self._next_id] = copy.deepcopy(record) 
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

    def query(self, outcome=None, min_score=None, max_score=None):
        wanted = None
        if outcome is not None:
            wanted = Outcome.parse(outcome)
            if wanted is None:
                return []
        return [r for r in self.list_all()
                if (wanted is None or r.outcome is wanted)
                and (min_score is None or r.score >= min_score)
                and (max_score is None or r.score <= max_score)]
