import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LogicManager")

REQUIREMENTS_FILE = "requirements.txt"

ACCEPT_SCORE_THRESHOLD = 8.0
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
                if not line or ":" not in line:
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


def _compute_score(record, requirements):
    required_skills = [s.lower() for s in requirements.get("required_skills", [])]
    candidate_skills = [s.lower() for s in record.get("skills", [])]

    if required_skills:
        matched_count = sum(1 for s in required_skills if s in candidate_skills)
        skill_fraction = matched_count / len(required_skills)
    else:
        skill_fraction = 1.0

    min_experience = requirements.get("min_experience", 0)
    experience_years = record.get("experience_years", 0)
    experience_fraction = min(experience_years / min_experience, 1.0) if min_experience > 0 else 1.0

    score = (skill_fraction * 0.7 + experience_fraction * 0.3) * 10
    return round(score, 1), required_skills, candidate_skills


def evaluate_resume(record, requirements):
    """
    Takes one AI-enriched record (filename, skills, experience_years, certificates)
    and returns a fully graded record ready for the Data Manager:
        {filename, skills, experience_years, certificates,
         missing_skills, score, outcome, timestamp}
    """
    score, required_skills, candidate_skills = _compute_score(record, requirements)

    missing_skills = [s for s in required_skills if s not in candidate_skills]
    all_required_present = len(missing_skills) == 0

    min_experience = requirements.get("min_experience", 0)
    meets_experience = record.get("experience_years", 0) >= min_experience

    if score > ACCEPT_SCORE_THRESHOLD and all_required_present and meets_experience:
        outcome = "Accepted"
    elif score <= REJECT_SCORE_THRESHOLD or not all_required_present:
        outcome = "Rejected"
    else:
        outcome = "Flagged"

    return {
        "filename": record.get("filename", "unknown"),
        "skills": record.get("skills", []),
        "experience_years": record.get("experience_years", 0),
        "certificates": record.get("certificates", []),
        "missing_skills": missing_skills,
        "score": score,
        "outcome": outcome,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def evaluate_batch(records):
    requirements = load_requirements()
    return [evaluate_resume(r, requirements) for r in records]