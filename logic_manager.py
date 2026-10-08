import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LogicManager")

REQUIREMENTS_FILE = "requirements.txt"

TARGET_FIELD = "IT"

SKILLS_FOR_FULL_SCORE = 4

MAX_EXPERIENCE_FOR_FULL_SCORE = 5

MAX_CERTS_FOR_FULL_SCORE = 3

ACCEPT_SCORE_THRESHOLD = 7.5
REJECT_SCORE_THRESHOLD = 4.0


def load_requirements(path=REQUIREMENTS_FILE):
    defaults = {"required_skills": [], "min_experience": 0}

    if not os.path.exists(path):
        logger.warning(f"{path} not found. Using default (empty) requirements.")
        return defaults

    requirements = dict(defaults)
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()

                if key == "required_skills":
                    requirements["required_skills"] = [
                        s.strip() for s in value.split(",") if s.strip()
                    ]
                elif key == "min_experience":
                    try:
                        requirements["min_experience"] = float(value)
                    except ValueError:
                        logger.warning(f"Could not parse min_experience value: {value}")
    except Exception as e:
        logger.error(f"Error reading {path}: {e}. Using defaults.")
        return defaults

    return requirements


def _normalize_certs_by_industry(certs_by_industry):
    normalized = {}
    for industry, certs in (certs_by_industry or {}).items():
        normalized[industry.strip().lower()] = [c.strip().lower() for c in certs]
    return normalized


def _skill_is_matched(required_skill, candidate_skills):
    return any(required_skill in candidate_skill for candidate_skill in candidate_skills)


def _compute_score(record, requirements):
    required_skills = [s.lower() for s in requirements.get("required_skills", [])]
    candidate_skills = [s.lower() for s in record.get("skills", [])]

    if required_skills:
        matched_count = sum(1 for s in required_skills if _skill_is_matched(s, candidate_skills))
        skill_fraction = min(matched_count / SKILLS_FOR_FULL_SCORE, 1.0)
    else:
        skill_fraction = 1.0

    field_experience = record.get("experience_by_field", {}).get(TARGET_FIELD, 0)
    experience_fraction = min(field_experience / MAX_EXPERIENCE_FOR_FULL_SCORE, 1.0)

    normalized_certs = _normalize_certs_by_industry(record.get("certificates_by_industry"))
    target_field_certs = normalized_certs.get(TARGET_FIELD.lower(), [])
    certs_fraction = min(len(target_field_certs) / MAX_CERTS_FOR_FULL_SCORE, 1.0)

    score = (skill_fraction * 0.4 + experience_fraction * 0.4 + certs_fraction * 0.2) * 10
    return (
        round(score, 1), required_skills, candidate_skills,
        field_experience, normalized_certs, target_field_certs,
    )


def evaluate_resume(record, requirements):
    (score, required_skills, candidate_skills,
     field_experience, normalized_certs, target_field_certs) = _compute_score(record, requirements)

    missing_skills = [s for s in required_skills if not _skill_is_matched(s, candidate_skills)]

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


def evaluate_batch(records):
    requirements = load_requirements()
    return [evaluate_resume(r, requirements) for r in records]