from LogicManager.score_breakdown import ScoreBreakdown
from LogicManager.scoring_policy import ScoringPolicy


class ScoreCalculator:
    """"
    Scores resume against job requirements
    """

    def __init__(self, policy=None):
        self._policy = policy or ScoringPolicy()

    @property
    def policy(self):
        return self._policy

    @staticmethod
    def lowercase_certificates(certs_by_industry):
        """
        Converts certificate names to lowercase for consistency
        """
        return {
            industry.strip().lower(): [c.strip().lower() for c in certs]
            for industry, certs in (certs_by_industry or {}).items()
        }

    @staticmethod
    def has_skill(required_skill, candidate_skills):
        """
        Ensures that string is detected even if not in exact format
        """
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
