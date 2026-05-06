from enum import Enum


class LikelySourceZone(str, Enum):
    ACTIVE_FACE = "active_face"
    GAS_SYSTEM = "gas_system"
    PERIMETER_OR_UNKNOWN = "perimeter_or_unknown"


class PriorityTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SeverityTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReviewStatus(str, Enum):
    PROPOSED = "proposed"
    PUBLISHED = "published"
    DISMISSED = "dismissed"
    NEEDS_REVIEW = "needs_review"


class FeedbackStatus(str, Enum):
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    NEEDS_REVIEW = "needs_review"
    UNRESOLVED = "unresolved"


class DataSplit(str, Enum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"
    DEMO = "demo"
