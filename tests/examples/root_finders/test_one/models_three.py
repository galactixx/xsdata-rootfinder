from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from xsdata.models.datatype import XmlTime

from .models_one import Item
from .models_two import CustomerType, OrderType

__NAMESPACE__ = "http://example.com/models_part3"


class PaymentMethodType(Enum):
    CREDIT_CARD = "CREDIT_CARD"
    PAYPAL = "PAYPAL"
    WIRE_TRANSFER = "WIRE_TRANSFER"


@dataclass
class PaymentDetailsType:
    class Meta:
        name = "PaymentDetailsType"

    method: PaymentMethodType = field(
        default=PaymentMethodType.CREDIT_CARD,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    amount: float = field(
        default=0.0,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    payment_time: Optional[XmlTime] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class ExtendedOrderType(OrderType):
    class Meta:
        name = "ExtendedOrderType"

    payment_details: Optional[PaymentDetailsType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class AnotherRoot:
    class Meta:
        name = "AnotherRoot"
        namespace = __NAMESPACE__

    customer_info: Optional[CustomerType] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    orders: List[ExtendedOrderType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )
    extra_items: List[Item] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )
    reference_id: str = field(
        default="",
        metadata={
            "type": "Attribute",
        },
    )
