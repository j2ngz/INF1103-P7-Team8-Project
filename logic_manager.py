import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from models import Outcome, ResumeRecord

logger = logging.getLogger("LogicManager")

REQUIREMENTS_FILE = "requirements.txt"

class JobRequirements:

    DEFAULT_RULE = "multi_condition"

    def __init__(self, required_skills=None, min_experience=0.0, outcome_rule=DEFAULT_RULE):
        self._required_skills = [s.strip() for s in (required_skills or []) if s.strip()]
        self._min_experience = float(min_experience)
        self._outcome_rule = outcome_rule

    @property
    def required_skills(self):
        return list(self._required_skills)

    @property
    def min_experience(self):
        return self._min_experience

    @property
    def outcome_rule(self):
        return self._outcome_rule

    @classmethod
    def from_file(cls, path=REQUIREMENTS_FILE):
        if not os.path.exists(path):
            logger.warning(f"{path} not found. Using default (empty) requirements.")
            return cls()

        skills, min_experience, rule = [], 0.0, cls.DEFAULT_RULE
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or ":" not in line:
                        continue
                    key, value = line.split(":", 1)
                    key, value = key.strip().lower(), value.strip()
                    if key == "required_skills":
                        skills = [s.strip() for s in value.split(",") if s.strip()]
                    elif key == "min_experience":
                        try:
                            min_experience = float(value)
                        except ValueError:
                            logger.warning(f"Could not parse min_experience value: {value}")
                    elif key == "outcome_rule" and value:
                        rule = value.lower()
        except Exception as e:
            logger.error(f"Error reading {path}: {e}. Using defaults.")
            return cls()
        return cls(skills, min_experience, rule)

@dataclass(frozen=True)
class ScoringPolicy:

    target_field: str = "IT"
    skills_for_full_score: int = 4
    experience_for_full_score: float = 5
    certs_for_full_score: int = 3
    skills_weight: float = 0.4
    experience_weight: float = 0.4
    certs_weight: float = 0.2
    accept_threshold: float = 7.5 
    reject_threshold: float = 4.0   


@dataclass(frozen=True)
class ScoreBreakdown:

    score: float
    it_experience_years: float
    certificates: dict = field(default_factory=dict)
    it_certs: list = field(default_factory=list)
    missing_skills: list = field(default_factory=list)



from typing import Any


TARGET_FIELD = "IT"

SKILLS_FOR_FULL_SCORE = 4

MAX_EXPERIENCE_FOR_FULL_SCORE = 5

MAX_CERTS_FOR_FULL_SCORE = 3

ACCEPT_SCORE_THRESHOLD = 7.5
REJECT_SCORE_THRESHOLD = 4.0



def lowercase_certificates_by_industry(certs_by_industry: dict[str, list[str]] | None) -> dict[str, list[str]]:
    normalized = {}
    for industry, certs in (certs_by_industry or {}).items():
        normalized[industry.strip().lower()] = [c.strip().lower() for c in certs]
    return normalized


def does_candidate_have_skill(required_skill: str, candidate_skills: list[str]) -> bool:
    return any(required_skill in candidate_skill for candidate_skill in candidate_skills)


def calculate_resume_score(
    record: dict[str, Any], requirements: dict[str, Any]
) -> tuple[float, list[str], list[str], float, dict[str, list[str]], list[str]]:
    required_skills = [s.lower() for s in requirements.get("required_skills", [])]
    candidate_skills = [s.lower() for s in record.get("skills", [])]

    if required_skills:
        matched_count = sum(1 for s in required_skills if does_candidate_have_skill(s, candidate_skills))
        skill_fraction = min(matched_count / SKILLS_FOR_FULL_SCORE, 1.0)
    else:
        skill_fraction = 1.0 

    field_experience = record.get("experience_by_field", {}).get(TARGET_FIELD, 0)
    experience_fraction = min(field_experience / MAX_EXPERIENCE_FOR_FULL_SCORE, 1.0)

    normalized_certs = lowercase_certificates_by_industry(record.get("certificates_by_industry"))
    target_field_certs = normalized_certs.get(TARGET_FIELD.lower(), [])
    certs_fraction = min(len(target_field_certs) / MAX_CERTS_FOR_FULL_SCORE, 1.0)

    score = (skill_fraction * 0.4 + experience_fraction * 0.4 + certs_fraction * 0.2) * 10
    return (
        round(score, 1), required_skills, candidate_skills,
        field_experience, normalized_certs, target_field_certs,
    )


def evaluate_resume(record: dict[str, Any], requirements: dict[str, Any]) -> dict[str, Any]:
    (score, required_skills, candidate_skills,
     field_experience, normalized_certs, target_field_certs) = calculate_resume_score(record, requirements)

    missing_skills = [s for s in required_skills if not does_candidate_have_skill(s, candidate_skills)]

    if score > ACCEPT_SCORE_THRESHOLD:
        outcome = "Accepted"
    elif score <= REJECT_SCORE_THRESHOLD:
        outcome = "Rejected"
    else:
        outcome = "Flagged"

    return {
        "name": record.get("name", "Unknown"),
        "skills": [s.lower() for s in record.get("skills", [])],
        "it_experience_years": field_experience,
        "certificates": normalized_certs,
        "it_certs": target_field_certs,
        "missing_skills_count": len(missing_skills),
        "score": score,
        "outcome": outcome,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# def evaluate_batch(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
#     requirements = load_requirements()
#     return [evaluate_resume(r, requirements) for r in records]
