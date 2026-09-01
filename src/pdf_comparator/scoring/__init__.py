"""Scoring, severity, confidence, and classification synthesis module."""

from pdf_comparator.scoring.classifier import ResultClassifier
from pdf_comparator.scoring.confidence import ConfidenceEvaluator
from pdf_comparator.scoring.severity import SeverityEvaluator

__all__ = [
    "SeverityEvaluator",
    "ConfidenceEvaluator",
    "ResultClassifier",
]
