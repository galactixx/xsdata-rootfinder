from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from test_three.models_one import (
    ConditionType,
    LogisticsRecord,
    ProductRecord,
    StatusCode,
    VisibleDerived,
)
from xsdata.models.datatype import XmlDate, XmlDateTime

__NAMESPACE__ = "http://example.com/models_y"


class RegionCode(Enum):
    NA = "North America"
    EU = "Europe"
    AS = "Asia"
    SA = "South America"
    AF = "Africa"
    OC = "Oceania"
    AN = "Antarctica"


class DispatchMethod(Enum):
    AIR = "AIR"
    SEA = "SEA"
    LAND = "LAND"
    DIGITAL = "DIGITAL"


@dataclass
class DispatchDetails:
    class Meta:
        name = "DispatchDetails"

    dispatch_method: DispatchMethod = field(
        default=DispatchMethod.LAND,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    origin_region: RegionCode = field(
        default=RegionCode.NA,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    dispatch_note: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    estimated_travel_days: int = field(
        default=5,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class CustomerAccount:
    class Meta:
        name = "CustomerAccount"

    customer_id: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    account_name: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    creation_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class LogisticsSummary:
    class Meta:
        name = "LogisticsSummary"

    summary_id: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    record: Optional[LogisticsRecord] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    remarks: List[str] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )


@dataclass
class MaintenanceReport:
    class Meta:
        name = "MaintenanceReport"

    report_id: str = field(
        default="",
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    last_check: Optional[XmlDateTime] = field(
        default=None,
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
    condition: ConditionType = field(
        default=ConditionType.REFURBISHED,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )


@dataclass
class OmegaRoot:
    class Meta:
        name = "OmegaRoot"
        namespace = __NAMESPACE__

    root_id: str = field(
        default="",
        metadata={
            "type": "Attribute",
        },
    )
    created_on: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    main_dispatch: Optional[DispatchDetails] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    account: Optional[CustomerAccount] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
        },
    )
    primary_product: Optional[ProductRecord] = field(
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
    logs_summaries: List[LogisticsSummary] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )
    maintenance: List[MaintenanceReport] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": __NAMESPACE__,
            "min_occurs": 0,
        },
    )
