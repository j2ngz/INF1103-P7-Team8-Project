import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LogicManager")

REQUIREMENTS_FILE = "requirements.txt"

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
    score, required_skills, candidate_skills = _compute_score(record, requirements)

    missing_skills = [s for s in required_skills if s not in candidate_skills]
    matched_count = len(required_skills) - len(missing_skills)

    has_most_skills = (
        True if not required_skills else (matched_count / len(required_skills)) >= 0.5
    )
    no_related_skills = bool(required_skills) and matched_count == 0

    min_experience = requirements.get("min_experience", 0)
    meets_experience = record.get("experience_years", 0) >= min_experience

    if score > ACCEPT_SCORE_THRESHOLD and has_most_skills and meets_experience:
        outcome = "Accepted"
        review_notes = ""
    elif no_related_skills or score <= REJECT_SCORE_THRESHOLD:
        outcome = "Rejected"
        review_notes = (
            "no overlap with required skills" if no_related_skills else ""
        )
    else:
        outcome = "Flagged"
        reasons = []
        if missing_skills:
            reasons.append(f"missing skill(s): {', '.join(missing_skills)}")
        if not meets_experience:
            reasons.append(
                f"experience below minimum ({record.get('experience_years', 0)} / "
                f"{min_experience} years)"
            )
        if not reasons:
            reasons.append("borderline score - recommend manual check")
        review_notes = "; ".join(reasons)

    return {
        "filename": record.get("filename", "unknown"),
        "skills": record.get("skills", []),
        "experience_years": record.get("experience_years", 0),
        "certificates": record.get("certificates", []),
        "missing_skills": missing_skills,
        "score": score,
        "outcome": outcome,
        "review_notes": review_notes,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def evaluate_batch(records):
    """Evaluates a list of AI-enriched records. Called by I/O Manager after AI Manager returns."""
    requirements = load_requirements()
    return [evaluate_resume(r, requirements) for r in records]
