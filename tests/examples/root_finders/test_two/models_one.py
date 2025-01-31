from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from xsdata.models.datatype import XmlDateTime

__NAMESPACE__ = "http://example.com/models_part_a"


class ColorOption(Enum):
    RED = "RED"
    BLUE = "BLUE"
    GREEN = "GREEN"
    ORANGE = "ORANGE"


@dataclass
class DimensionSpec:
    class Meta:
        name = "DimensionSpec"

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
class ProductInfo:
    class Meta:
        name = "ProductInfo"

    product_id: str = field(
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
    color: ColorOption = field(
        default=ColorOption.RED,
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
class MyThing:
    class Meta:
        name = "MyThing"

    info: ProductInfo = field(
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        }
    )
    dimensions: DimensionSpec = field(
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
class AlphaRoot:
    class Meta:
        name = "AlphaRoot"
        namespace = __NAMESPACE__

    collection_id: str = field(
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
    my_things: List[MyThing] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )
