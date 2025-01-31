from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from xsdata.models.datatype import XmlDateTime


class PriorityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class AccessLevel(Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


@dataclass
class Task:
    task_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    description: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    priority: Optional[PriorityLevel] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    created_at: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class User:
    user_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    username: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    access_level: Optional[AccessLevel] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class Project:
    project_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    project_name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    tasks: List[Task] = field(
        default_factory=list,
        metadata={
            "type": "Element",
        },
    )
    users: List[User] = field(
        default_factory=list,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class AuditLog:
    log_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    action: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    timestamp: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class SystemAdministrator:
    admin_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    level: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class AuditManager:
    logs: List[AuditLog] = field(
        default_factory=list,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class Notification:
    notification_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    message: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    project: Optional[Project] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class NotificationService:
    service_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    notifications: List[Notification] = field(
        default_factory=list,
        metadata={
            "type": "Element",
        },
    )
