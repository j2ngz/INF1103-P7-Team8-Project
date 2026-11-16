from abc import ABC, abstractmethod

from LogicManager.scoring_policy import ScoringPolicy
from Models.outcome import Outcome


class OutcomeRule(ABC):
    """
    Resume Rejected and Flagged handling are shared here, subclasses only need to implement logic when a resume is accepted.
    """

    def __init__(self, policy=None):
        self._policy = policy or ScoringPolicy()

    @property
    @abstractmethod
    def name(self):
        """Short name used in requirements.txt (outcome_rule: <name>)."""
        pass

    @abstractmethod
    def _qualifies_for_accept(self, breakdown, requirements):
        """True when the resume meets this rule's conditions for Accepted."""
        pass

    def decide(self, breakdown, requirements):
        if breakdown.score <= self._policy.reject_threshold:
            return Outcome.REJECTED
        if self._qualifies_for_accept(breakdown, requirements):
            return Outcome.ACCEPTED
        return Outcome.FLAGGED
