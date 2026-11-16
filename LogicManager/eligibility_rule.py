from LogicManager.score_only_rule import ScoreOnlyRule


class EligibilityRule(ScoreOnlyRule):
    """
    This rule accepts candidates with a score above the threshold and relevant job experience fulfills the job's minimum experience required.
    A candidate with a high score but insufficient experience is flagged for the reviewer to assess.
    """
    
    @property
    def name(self):
        return "multi_condition"

    def _qualifies_for_accept(self, breakdown, requirements):
        return (super()._qualifies_for_accept(breakdown, requirements)
                and breakdown.it_experience_years >= requirements.min_experience)
