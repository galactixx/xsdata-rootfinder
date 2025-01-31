from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from root_finders.test_two.models_three import ExtendedPurchaseOrder

from .models_one import *
from .models_two import *

__NAMESPACE__ = "http://example.com/models_part_d"


class PriorityLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


@dataclass
class DispatchInfo:
    class Meta:
        name = "DispatchInfo"

    dispatch_id: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    priority: PriorityLevel = field(
        default=PriorityLevel.LOW,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class GammaRoot:
    class Meta:
        name = "GammaRoot"
        namespace = __NAMESPACE__

    tracking_code: str = field(
        default="",
        metadata={
            "type": "Attribute",
        },
    )
    dispatch_details: Optional[DispatchInfo] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    # Example references to classes from the other modules
    items: List[MyThing] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )
    client_info: Optional[ClientProfile] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    extended_orders: List[ExtendedPurchaseOrder] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )
