from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from xsdata.models.datatype import XmlDateTime


class ColorEnum(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class SizeEnum(Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


@dataclass
class Dimensions:
    height: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    width: Optional[float] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    measured_at: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class Manufacturer:
    name: Optional[str] = field(
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


@dataclass
class Product:
    product_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    color: Optional[ColorEnum] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    size: Optional[SizeEnum] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    dimensions: Optional[Dimensions] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    manufacturer: Optional[Manufacturer] = field(
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
class Catalog:
    catalog_name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    products: List[Product] = field(
        default_factory=list,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class Shipment:
    shipment_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    items: List[Product] = field(
        default_factory=list,
        metadata={
            "type": "Element",
        },
    )
    shipped_at: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class Warehouse:
    location_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    shipments: List[Shipment] = field(
        default_factory=list,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class Order:
    order_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    product: Optional[Product] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    order_time: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


@dataclass
class Customer:
    customer_id: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )
    orders: List[Order] = field(
        default_factory=list,
        metadata={
            "type": "Element",
        },
    )
