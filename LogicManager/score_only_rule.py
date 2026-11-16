from LogicManager.outcome_rule import OutcomeRule


class ScoreOnlyRule(OutcomeRule):
    """
    Accepted candidate when resume score is above threshold
    """

    @property
    def name(self):
        return "score_only"

    def _qualifies_for_accept(self, breakdown, requirements):
        return breakdown.score > self._policy.accept_threshold
