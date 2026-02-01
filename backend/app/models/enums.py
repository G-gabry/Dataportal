import enum


class SourceType(str, enum.Enum):
    UNIVERSITY = "UNIVERSITY"
    SCHOLARSHIP_ORG = "SCHOLARSHIP_ORG"
    CONFERENCE_ORG = "CONFERENCE_ORG"
    EXCHANGE_ORG = "EXCHANGE_ORG"
    OTHER = "OTHER"


class ItemType(str, enum.Enum):
    PROGRAM = "PROGRAM"
    SCHOLARSHIP = "SCHOLARSHIP"
    CONFERENCE = "CONFERENCE"
    EXCHANGE = "EXCHANGE"


class URLStatus(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    CLASSIFIED = "CLASSIFIED"
    SCRAPED = "SCRAPED"
    EXTRACTED = "EXTRACTED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class RelevanceStatus(str, enum.Enum):
    PENDING = "PENDING"
    RELEVANT = "RELEVANT"
    NOT_RELEVANT = "NOT_RELEVANT"


class PriorityLevel(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ItemStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    VERIFIED = "VERIFIED"
    PUBLISHED = "PUBLISHED"
    OUTDATED = "OUTDATED"
    ARCHIVED = "ARCHIVED"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"
