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

class ResumeData:
    #What the AI Read from a resume. Immutable after creation.

    def __init__(self, filename, name, skills, experience_by_field, certificates_by_industry):
        self._filename = filename
        self._name = name
        self._skills = list(skills)
        self._experience_by_field = dict(experience_by_field)
        self._certificates_by_industry = {k: list(v) for k, v in certificates_by_industry.items()}

    @classmethod
    def from_dict(cls, data):
        """Builds a ResumeData from an (already validated) AI response dictionary."""
        return cls(
            filename=data["filename"],
            name=data["name"],
            skills=data["skills"],
            experience_by_field=data["experience_by_field"],
            certificates_by_industry=data["certificates_by_industry"],
        )

    @property
    def filename(self):
        return self._filename

    @property
    def name(self):
        return self._name

    @property
    def skills(self):
        return list(self._skills)

    @property
    def experience_by_field(self):
        return dict(self._experience_by_field)

    @property
    def certificates_by_industry(self):
        return {k: list(v) for k, v in self._certificates_by_industry.items()}

    def __repr__(self):
        return f"ResumeData(filename={self._filename!r}, name={self._name!r})"

class ResumeBatch:

    def __init__(self, items=None):
        self._items = list(items) if items else []

    def add(self, item):
        self._items.append(item)

    @property
    def filenames(self):
        return [item.filename for item in self._items if item.filename]

    def is_empty(self):
        return not self._items

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

