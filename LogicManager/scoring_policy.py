from dataclasses import dataclass


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
