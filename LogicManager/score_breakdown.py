from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScoreBreakdown:
    """"
    Calculated resume data
    """

    score: float
    it_experience_years: float
    certificates: dict = field(default_factory=dict)
    it_certs: list = field(default_factory=list)
    missing_skills: list = field(default_factory=list)
