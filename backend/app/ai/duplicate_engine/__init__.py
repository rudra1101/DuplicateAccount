from app.ai.duplicate_engine.engine import (
    DuplicateDetectionEngine,
    duplicate_detection_engine,
)
from app.ai.duplicate_engine.normalizer import (
    normalize_account,
)
from app.ai.duplicate_engine.types import (
    ComparisonFeatures,
    DuplicatePrediction,
    MatchReason,
    NormalizedAccount,
)

__all__ = [
    "ComparisonFeatures",
    "DuplicateDetectionEngine",
    "DuplicatePrediction",
    "MatchReason",
    "NormalizedAccount",
    "duplicate_detection_engine",
    "normalize_account",
]