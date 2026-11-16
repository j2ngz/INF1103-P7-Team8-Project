#sample data and fakes for testing purposes

import logging
import os
import tempfile

from AIManager import AIClient
from LogicManager import JobRequirements
from Models import ResumeData, ResumeRecord

logging.disable(logging.CRITICAL)   # keep the managers' log lines out of the test output

REQUIREMENTS = JobRequirements(
    ["python", "sql", "tableau", "power bi", "aws", "docker", "kubernetes", "git", "linux"],
    min_experience=1)
NO_SKILLS_REQUIRED = JobRequirements([], min_experience=0)

# 6 matched skills (some with parentheses), 5 yrs IT, 4 IT certs -> 10.0
SAMPLE_STRONG = {
    "filename": "arthur_goatson.pdf",
    "name": "Arthur Goatson",
    "skills": ["Python", "SQL (PostgreSQL, MySQL)", "AWS (EC2, S3)", "Docker", "Git", "Linux", "Photoshop"],
    "experience_by_field": {"IT": 5, "Finance": 2},
    "certificates_by_industry": {
        "IT": ["AWS Certified Solutions Architect", "CompTIA Security+", "CKA", "Azure Fundamentals"],
        "FnB": ["ServSafe"],
    },
}

# 3 matched skills, 4 yrs IT, 2 IT certs -> 7.5 exactly (not above 7.5, so Flagged)
SAMPLE_BORDERLINE = {
    "filename": "priya_sharma.pdf",
    "name": "Priya Sharma",
    "skills": ["Python", "SQL", "Tableau"],
    "experience_by_field": {"IT": 4},
    "certificates_by_industry": {"IT": ["Tableau Desktop Specialist", "AWS Cloud Practitioner"]},
}

# 1 matched skill, 1 yr IT, no certs -> 1.8
SAMPLE_WEAK = {
    "filename": "weak.pdf",
    "name": "Sam Lee",
    "skills": ["Python", "Excel"],
    "experience_by_field": {"IT": 1},
    "certificates_by_industry": {},
}

# Strong in a different field only -> 0.0
SAMPLE_NON_IT = {
    "filename": "nurse.pdf",
    "name": "Dr. Eleanor Vance",
    "skills": ["Patient care", "Triage"],
    "experience_by_field": {"Healthcare": 12},
    "certificates_by_industry": {"Healthcare": ["BLS", "ACLS"]},
}


def resume(sample):
    """ResumeData from a sample dictionary."""
    return ResumeData.from_dict(sample)


def make_resume(it_years=0, it_certs=0, skills=None, name="Test Person", filename="x.pdf"):
    """A ResumeData with a given IT experience / IT certificate count."""
    return ResumeData(filename, name, skills or [], {"IT": it_years},
                      {"IT": [f"cert {i}" for i in range(it_certs)]})


def make_record(name="Test Person", score=6.0, outcome="Flagged", timestamp="2026-01-01 10:00:00",
                it_certs=None, missing=2, years=3.0, **extra):
    """A graded ResumeRecord (no id yet)."""
    it_certs = it_certs if it_certs is not None else ["cert a"]
    return ResumeRecord(name=name, skills=["python"], it_experience_years=years,
                        certificates={"it": it_certs}, it_certs=it_certs,
                        missing_skills_count=missing, score=score, outcome=outcome,
                        timestamp=timestamp, **extra)


#We use this as a standin for the real API, so we dont need any API key
#It returns the replies it is given, or raises them if they are errors
class FakeAIClient(AIClient):

    def __init__(self, replies):
        self._replies = list(replies)
        self.calls = []

    def generate_json(self, prompt, resume_paths):
        self.calls.append((prompt, list(resume_paths)))
        if not self._replies:
            raise RuntimeError("FakeAIClient has no more replies...")
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def write_temp_file(text, suffix=".txt"):
    #Writes text to a temp file and returns its path (the caller deletes it)
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    return path
