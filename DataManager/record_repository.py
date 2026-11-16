from abc import ABC, abstractmethod

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
