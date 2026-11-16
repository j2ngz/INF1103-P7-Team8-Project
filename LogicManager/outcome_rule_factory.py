import logging

from LogicManager.eligibility_rule import EligibilityRule
from LogicManager.job_requirements import JobRequirements
from LogicManager.score_only_rule import ScoreOnlyRule
from LogicManager.scoring_policy import ScoringPolicy

logger = logging.getLogger("LogicManager")


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
