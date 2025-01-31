from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from xsdata.models.datatype import XmlDateTime


class EmploymentType(Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"


class LevelType(Enum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"


@dataclass
class BasePerson:
    person_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    full_name: Optional[str] = field(
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
class Staff(BasePerson):
    role: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    employment_type: Optional[EmploymentType] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    level: Optional[LevelType] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class Customer(BasePerson):
    email: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    loyalty_points: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class OfficeLocation:
    location_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    address: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    country: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    established_at: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class OfficeDirectory:
    directory_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    offices: List[OfficeLocation] = field(
        default_factory=list,
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
    title: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    team: List[Staff] = field(
        default_factory=list,
        metadata={
            "type": "Element",
        },
    )
    deadline: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class CustomerOrder:
    order_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    customer: Optional[Customer] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    order_date: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    amount: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class OrderHistory:
    history_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    orders: List[CustomerOrder] = field(
        default_factory=list,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class CustomerServiceManager:
    csm_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    customers: List[Customer] = field(
        default_factory=list,
        metadata={
            "type": "Element",
        },
    )
    order_history: Optional[OrderHistory] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class ProjectManager:
    project_mgr_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    projects: List[Project] = field(
        default_factory=list,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class PayrollEntry:
    payroll_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    staff_member: Optional[Staff] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    pay_date: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    amount: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class PayrollManager:
    manager_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    payroll_records: List[PayrollEntry] = field(
        default_factory=list,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class OfficeAssignment:
    office: Optional[OfficeLocation] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    staff_member: Optional[Staff] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    assigned_at: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class OfficeManager:
    manager_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    directory: Optional[OfficeDirectory] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    assignments: List[OfficeAssignment] = field(
        default_factory=list,
        metadata={
            "type": "Element",
        },
    )
