from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .models_two import *

__NAMESPACE__ = "http://example.com/models_part_c"


class CountryCode(Enum):
    US = "US"
    CA = "CA"
    GB = "GB"
    FR = "FR"
    DE = "DE"


@dataclass
class AddressInfo:
    class Meta:
        name = "AddressInfo"

    street: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    city: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    country: CountryCode = field(
        default=CountryCode.US,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class ExtendedPurchaseOrder(PurchaseOrder):
    class Meta:
        name = "ExtendedPurchaseOrder"

    delivery_address: Optional[AddressInfo] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class BetaRoot:
    class Meta:
        name = "BetaRoot"
        namespace = __NAMESPACE__

    client_profile: Optional[ClientProfile] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    orders: List[ExtendedPurchaseOrder] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )
    description: str = field(
        default="",
        metadata={
            "type": "Attribute",
        },
    )
