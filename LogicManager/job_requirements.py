import logging
import os

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
        """
        Reads key:value lines.
        Blank lines and comments are ignored.
        Missing/Unreadable file defaults to no required skills.
        """
        if not os.path.exists(path):
            logger.warning(f"{path} not found. Using default requirements.")
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
