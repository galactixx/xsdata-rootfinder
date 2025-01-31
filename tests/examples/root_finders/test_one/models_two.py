from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from xsdata.models.datatype import XmlDate, XmlDuration

from .models_one import Item, ProductIdentificationType

__NAMESPACE__ = "http://example.com/models_part2"


class StatusType(Enum):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    CLOSED = "CLOSED"


@dataclass
class ShippingInfoType:
    class Meta:
        name = "ShippingInfoType"

    address: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    expected_delivery_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    shipping_duration: Optional[XmlDuration] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class OrderLineItem:
    class Meta:
        name = "OrderLineItem"

    product: ProductIdentificationType = field(
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
class OrderType:
    class Meta:
        name = "OrderType"

    order_id: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    status: StatusType = field(
        default=StatusType.PENDING,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    line_items: List[OrderLineItem] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )
    associated_items: List[Item] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )
    shipping_info: Optional[ShippingInfoType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class CustomerType:
    class Meta:
        name = "CustomerType"

    customer_id: str = field(
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
    registration_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
