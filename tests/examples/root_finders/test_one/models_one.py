from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from xsdata.models.datatype import XmlDateTime

__NAMESPACE__ = "http://example.com/models_part1"


class ColorType(Enum):
    RED = "RED"
    BLUE = "BLUE"
    GREEN = "GREEN"
    YELLOW = "YELLOW"


@dataclass
class DimensionsType:
    class Meta:
        name = "DimensionsType"

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
class ProductIdentificationType:
    class Meta:
        name = "ProductIdentificationType"

    product_id: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    product_name: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    color: ColorType = field(
        default=ColorType.RED,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    release_date: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class Item:
    class Meta:
        name = "Item"

    identification: ProductIdentificationType = field(
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        }
    )
    dimensions: DimensionsType = field(
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        }
    )
    tags: List[str] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )


@dataclass
class MyRoot:
    class Meta:
        name = "MyRoot"
        namespace = __NAMESPACE__

    items: List[Item] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )
    metadata_id: str = field(
        default="",
        metadata={
            "type": "Attribute",
        },
    )
    version: str = field(
        default="1.0",
        metadata={
            "type": "Attribute",
        },
    )
