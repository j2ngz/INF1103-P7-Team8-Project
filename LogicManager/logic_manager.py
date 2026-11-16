from datetime import datetime

from LogicManager.job_requirements import JobRequirements, REQUIREMENTS_FILE
from LogicManager.outcome_rule_factory import OutcomeRuleFactory
from LogicManager.score_calculator import ScoreCalculator
from Models.resume_record import ResumeRecord


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
        """"
        Scores ResumeData and returns ResumeRecord (no id saved yet)
        """
        #Scores one ResumeData and returns an unsaved ResumeRecord (no id yet)
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
        """"
        Evalutes every resume in the ResumeBatch
        """
        if self._fixed_requirements is None:
            self._requirements = JobRequirements.from_file(self._requirements_path)
        return [self.evaluate_resume(resume) for resume in batch]
