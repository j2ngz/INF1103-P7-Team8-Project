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



class ScoreCalculator:

    def __init__(self, policy=None):
        self._policy = policy or ScoringPolicy()

    @property
    def policy(self):
        return self._policy

    @staticmethod
    def lowercase_certificates(certs_by_industry):
        return {
            industry.strip().lower(): [c.strip().lower() for c in certs]
            for industry, certs in (certs_by_industry or {}).items()
        }

    @staticmethod
    def has_skill(required_skill, candidate_skills):
        return any(required_skill in skill for skill in candidate_skills)

    def calculate(self, resume, requirements):
        p = self._policy
        required = [s.lower() for s in requirements.required_skills]
        candidate = [s.lower() for s in resume.skills]

        missing = [s for s in required if not self.has_skill(s, candidate)]
        if required:
            matched = len(required) - len(missing)
            skill_fraction = min(matched / p.skills_for_full_score, 1.0)
        else:
            skill_fraction = 1.0

        years = resume.experience_by_field.get(p.target_field, 0)
        experience_fraction = min(years / p.experience_for_full_score, 1.0)

        certificates = self.lowercase_certificates(resume.certificates_by_industry)
        it_certs = certificates.get(p.target_field.lower(), [])
        certs_fraction = min(len(it_certs) / p.certs_for_full_score, 1.0)

        score = (skill_fraction * p.skills_weight
                 + experience_fraction * p.experience_weight
                 + certs_fraction * p.certs_weight) * 10
        return ScoreBreakdown(round(score, 1), years, certificates, it_certs, missing)


class OutcomeRule(ABC):

    def __init__(self, policy=None):
        self._policy = policy or ScoringPolicy()

    @property
    @abstractmethod
    def name(self):
        """Short name used in requirements.txt"""

    @abstractmethod
    def _qualifies_for_accept(self, breakdown, requirements):
        """True when the resume meets conditions for accepted."""

    def decide(self, breakdown, requirements):
        if breakdown.score <= self._policy.reject_threshold:
            return Outcome.REJECTED
        if self._qualifies_for_accept(breakdown, requirements):
            return Outcome.ACCEPTED
        return Outcome.FLAGGED


class ScoreOnlyRule(OutcomeRule):
    @property
    def name(self):
        return "score_only"

    def _qualifies_for_accept(self, breakdown, requirements):
        return breakdown.score > self._policy.accept_threshold


class EligibilityRule(ScoreOnlyRule):
    @property
    def name(self):
        return "multi_condition"

    def _qualifies_for_accept(self, breakdown, requirements):
        return (super()._qualifies_for_accept(breakdown, requirements)
                and breakdown.it_experience_years >= requirements.min_experience)

class OutcomeRuleFactory:

    _rules = {
        ScoreOnlyRule(ScoringPolicy()).name: ScoreOnlyRule,
        EligibilityRule(ScoringPolicy()).name: EligibilityRule,
    }

    @classmethod
    def register(cls, name, rule_class):
        cls._rules[name] = rule_class

    @classmethod
    def available(cls):
        return sorted(cls._rules)

    @classmethod
    def create(cls, name, policy=None):
        rule_class = cls._rules.get(name)
        if rule_class is None:
            logger.warning(f"Unknown outcome_rule '{name}'. Using '{JobRequirements.DEFAULT_RULE}'.")
            rule_class = cls._rules[JobRequirements.DEFAULT_RULE]
        return rule_class(policy)


class LogicManager:

    def __init__(self, requirements_path=REQUIREMENTS_FILE, requirements=None,
                 calculator=None, rule=None, clock=datetime.now):
        self._requirements_path = requirements_path
        self._fixed_requirements = requirements
        self._requirements = requirements or JobRequirements.from_file(requirements_path)
        self._calculator = calculator or ScoreCalculator()
        self._fixed_rule = rule
        self._clock = clock

    @property
    def requirements(self):
        return self._requirements

    def current_rule(self):
        if self._fixed_rule is not None:
            return self._fixed_rule
        return OutcomeRuleFactory.create(self._requirements.outcome_rule, self._calculator.policy)

    def evaluate_resume(self, resume):
        breakdown = self._calculator.calculate(resume, self._requirements)
        outcome = self.current_rule().decide(breakdown, self._requirements)
        return ResumeRecord(
            name=resume.name or "Unknown",
            skills=[s.lower() for s in resume.skills],
            it_experience_years=breakdown.it_experience_years,
            certificates=breakdown.certificates,
            it_certs=breakdown.it_certs,
            missing_skills_count=len(breakdown.missing_skills),
            score=breakdown.score,
            outcome=outcome,
            timestamp=self._clock().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def evaluate_batch(self, batch):
        if self._fixed_requirements is None:
            self._requirements = JobRequirements.from_file(self._requirements_path)
        return [self.evaluate_resume(resume) for resume in batch]
