from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from xsdata.models.datatype import XmlDate, XmlDateTime, XmlDuration

__NAMESPACE__ = "http://example.com/models_x"


class ConditionType(Enum):
    NEW = "NEW"
    USED = "USED"
    REFURBISHED = "REFURBISHED"
    DAMAGED = "DAMAGED"


class StatusCode(Enum):
    OK = "OK"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"


class PriorityCode(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class HiddenBase:
    note: str = field(
        default="Hidden base note",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class VisibleDerived(HiddenBase):
    derived_value: int = field(
        default=0,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class ManufacturerInfo:
    class Meta:
        name = "ManufacturerInfo"

    name: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    country: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    established: Optional[XmlDate] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class ProductAttributes:
    class Meta:
        name = "ProductAttributes"

    weight: float = field(
        default=0.0,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    length: float = field(
        default=0.0,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    width: float = field(
        default=0.0,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    height: float = field(
        default=0.0,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class WarrantyInfo:
    class Meta:
        name = "WarrantyInfo"

    duration: XmlDuration = field(
        default=XmlDuration("P1Y"),
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    coverage_details: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class ProductRecord:
    class Meta:
        name = "ProductRecord"

    product_id: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    attributes: Optional[ProductAttributes] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    manufacturer: Optional[ManufacturerInfo] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    warranty: Optional[WarrantyInfo] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    condition: ConditionType = field(
        default=ConditionType.NEW,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class ShipmentDetails:
    class Meta:
        name = "ShipmentDetails"

    shipment_id: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    scheduled_date: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    priority: PriorityCode = field(
        default=PriorityCode.LOW,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    status_code: StatusCode = field(
        default=StatusCode.UNKNOWN,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    comments: List[str] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )


@dataclass
class LogisticsRecord:
    class Meta:
        name = "LogisticsRecord"

    record_id: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    details: Optional[ShipmentDetails] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    overseer: Optional[VisibleDerived] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
