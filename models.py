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

class ResumeRecord:

    REVIEWABLE_DECISIONS = (Outcome.ACCEPTED, Outcome.REJECTED)

    def __init__(self, name, skills, it_experience_years, certificates, it_certs,
                 missing_skills_count, score, outcome, timestamp, record_id=None,
                 review_decision=None, review_note="", reviewed_at=None):
        self._id = record_id
        self._name = name
        self._skills = list(skills)
        self._it_experience_years = it_experience_years
        self._certificates = {k: list(v) for k, v in certificates.items()}
        self._it_certs = list(it_certs)
        self._missing_skills_count = int(missing_skills_count)
        self._score = float(score)
        self._outcome = Outcome.parse(outcome) if not isinstance(outcome, Outcome) else outcome
        if self._outcome is None:
            raise ValueError(f"Unknown outcome: {outcome!r}")
        self._timestamp = timestamp
        self._review_decision = None
        self._review_note = ""
        self._reviewed_at = None
        if review_decision:
            decision = review_decision if isinstance(review_decision, Outcome) else Outcome.parse(review_decision)
            if decision not in self.REVIEWABLE_DECISIONS:
                raise ValueError(f"Invalid review decision: {review_decision!r}")
            self._review_decision = decision
            self._review_note = review_note or ""
            self._reviewed_at = reviewed_at

    @property
    def id(self):
        return self._id

    def assign_id(self, record_id):
        """Gives the record its id. Id can only be assigned once."""
        if self._id is not None:
            raise ValueError("Record already has an id")
        self._id = int(record_id)

    @property
    def display_id(self):
        return "" if self._id is None else f"{self._id:02d}"

    @property
    def name(self):
        return self._name

    @property
    def skills(self):
        return list(self._skills)

    @property
    def it_experience_years(self):
        return self._it_experience_years

    @property
    def certificates(self):
        return {k: list(v) for k, v in self._certificates.items()}

    @property
    def it_certs(self):
        return list(self._it_certs)

    @property
    def missing_skills_count(self):
        return self._missing_skills_count

    @property
    def score(self):
        return self._score

    @property
    def outcome(self):
        return self._outcome

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def review_decision(self):
        return self._review_decision

    @property
    def review_note(self):
        return self._review_note

    @property
    def reviewed_at(self):
        return self._reviewed_at

    @property
    def is_reviewed(self):
        return self._review_decision is not None

    @property
    def needs_review(self):
        """True for a Flagged record that nobody has reviewed yet."""
        return self._outcome is Outcome.FLAGGED and not self.is_reviewed

    @property
    def final_outcome(self):
        """The reviewer's decision when there is one, otherwise the original outcome."""
        return self._review_decision if self.is_reviewed else self._outcome

    def apply_review(self, decision, note, reviewed_at):
        """
        Records a human decision on a Flagged record.
        Raises error when the record is not Flagged, was already reviewed, or the decision is not Accepted/Rejected.
        """
        if self._outcome is not Outcome.FLAGGED:
            raise ValueError("Only Flagged records can be reviewed")
        if self.is_reviewed:
            raise ValueError("This record has already been reviewed")
        decision = decision if isinstance(decision, Outcome) else Outcome.parse(decision)
        if decision not in self.REVIEWABLE_DECISIONS:
            raise ValueError("Review decision must be Accepted or Rejected")
        self._review_decision = decision
        self._review_note = (note or "").strip()
        self._reviewed_at = reviewed_at

    def without_id(self):
        """A copy of this record with no id, ready to be added to another repository."""
        return ResumeRecord(
            name=self._name, skills=self._skills, it_experience_years=self._it_experience_years,
            certificates=self._certificates, it_certs=self._it_certs,
            missing_skills_count=self._missing_skills_count, score=self._score,
            outcome=self._outcome, timestamp=self._timestamp,
            review_decision=self._review_decision, review_note=self._review_note,
            reviewed_at=self._reviewed_at)

    def __repr__(self):
        return f"ResumeRecord(id={self._id}, name={self._name!r}, score={self._score}, outcome={self._outcome.value})"
