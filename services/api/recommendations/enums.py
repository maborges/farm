from __future__ import annotations

from enum import Enum


class RecommendationDomain(str, Enum):
    AGRICULTURE = "AGRICULTURE"
    LIVESTOCK = "LIVESTOCK"
    FINANCE = "FINANCE"
    OPERATIONS = "OPERATIONS"
    FIELD = "FIELD"
    INTEGRATIONS = "INTEGRATIONS"
    SYSTEM = "SYSTEM"


class RecommendationStatus(str, Enum):
    CREATED = "CREATED"
    VIEWED = "VIEWED"
    ACCEPTED = "ACCEPTED"
    DISMISSED = "DISMISSED"
    POSTPONED = "POSTPONED"
    EXECUTED = "EXECUTED"
    EXPIRED = "EXPIRED"
    AUTO_EXPIRED = "AUTO_EXPIRED"
    SUPERSEDED = "SUPERSEDED"
    REOPENED = "REOPENED"


class RecommendationPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class RecommendationSourceType(str, Enum):
    SIGNAL = "SIGNAL"
    EVENT = "EVENT"
    INDICATOR = "INDICATOR"
    ANALYTICS = "ANALYTICS"
    MANUAL = "MANUAL"
    SYSTEM = "SYSTEM"


class RecommendationActionType(str, Enum):
    NONE = "NONE"
    OPEN_ROUTE = "OPEN_ROUTE"
    OPEN_URL = "OPEN_URL"
    REVIEW = "REVIEW"
    EXECUTE_ASSISTED = "EXECUTE_ASSISTED"


class RecommendationLifecycleActionType(str, Enum):
    CREATE = "CREATE"
    VIEW = "VIEW"
    ACCEPT = "ACCEPT"
    DISMISS = "DISMISS"
    POSTPONE = "POSTPONE"
    EXECUTE = "EXECUTE"
    EXPIRE = "EXPIRE"
    AUTO_EXPIRE = "AUTO_EXPIRE"
    SUPERSEDE = "SUPERSEDE"
    REOPEN = "REOPEN"


ACTIVE_RECOMMENDATION_STATUSES = (
    RecommendationStatus.CREATED.value,
    RecommendationStatus.VIEWED.value,
    RecommendationStatus.ACCEPTED.value,
    RecommendationStatus.POSTPONED.value,
    RecommendationStatus.REOPENED.value,
)
