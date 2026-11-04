from enum import Enum


class Outcome(str, Enum):

    ACCEPTED = "Accepted"
    FLAGGED = "Flagged"
    REJECTED = "Rejected"

    @classmethod
    def parse(cls, text):
        if not isinstance(text, str):
            return None
        wanted = text.strip().lower()
        for member in cls:
            if member.value.lower() == wanted:
                return member
        return None