from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from xsdata.models.datatype import XmlDate

from .models_one import *

__NAMESPACE__ = "http://example.com/models_part_b"


class StatusFlag(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"
    CLOSED = "CLOSED"


@dataclass
class CarrierInfo:
    class Meta:
        name = "CarrierInfo"

    carrier_name: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    expected_delivery: Optional[XmlDate] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    notes: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class OrderLine:
    class Meta:
        name = "OrderLine"

    product: ProductInfo = field(
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        }
    )
    quantity: int = field(
        default=1,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class PurchaseOrder:
    class Meta:
        name = "PurchaseOrder"

    order_id: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    status: StatusFlag = field(
        default=StatusFlag.PENDING,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    order_lines: List[OrderLine] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )
    associated_things: List[MyThing] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )
    carrier: Optional[CarrierInfo] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class ClientProfile:
    class Meta:
        name = "ClientProfile"

    client_id: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    name: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    signup_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
