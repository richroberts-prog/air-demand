"""Scoring package for role evaluation.

Provides scoring functions for engineer, headhunter, and excitement metrics.
"""

from .engine import calculate_scores
from .engineer import calculate_engineer_score
from .excitement import score_excitement_deterministic
from .headhunter import calculate_headhunter_score

__all__ = [
    "calculate_engineer_score",
    "calculate_headhunter_score",
    "calculate_scores",
    "score_excitement_deterministic",
]
